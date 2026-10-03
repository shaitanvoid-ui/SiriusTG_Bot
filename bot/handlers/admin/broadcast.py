"""Админка: рассылка по всем юзерам (Этап 9).

FSM: текст → предпросмотр → подтверждение → отправка с прогрессом.
Отправка идёт в отдельной фоновой задаче с собственной DB-сессией;
прогресс — edit-in-place каждые 25 отправок.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.admin_panel import kb_bc_cancel, kb_bc_confirm, kb_dash
from bot.states.admin import BroadcastStates
from db.repositories.action_log import ActionLogRepo
from db.repositories.user import UserRepo
from db.session import SessionLocal
from core.logger import get_logger
from locales.ru import T
from services.broadcast import BroadcastBusyError, run_broadcast


router = Router(name="admin_broadcast")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())
log = get_logger(__name__)
_launch_lock = asyncio.Lock()
_active_task: asyncio.Task[None] | None = None
_MAX_BROADCAST_TEXT = 3_500


async def _broadcast_job(
    *,
    bot: Bot,
    tg_ids: list[int],
    text: str,
    progress_msg: Message,
    actor_tg_id: int | None,
) -> None:
    global _active_task

    async def _progress(done: int, total: int) -> None:
        with suppress(TelegramAPIError):
            await progress_msg.edit_text(T.admin_bc_progress.format(done=done, total=total))

    try:
        result = await run_broadcast(bot, tg_ids, text, progress_cb=_progress)
        async with SessionLocal() as job_session:
            await ActionLogRepo(job_session).log(
                user_tg_id=actor_tg_id,
                action="admin_broadcast",
                payload={
                    "total": result.total,
                    "sent": result.sent,
                    "failed": result.failed,
                },
            )
            await job_session.commit()
        with suppress(TelegramAPIError):
            await progress_msg.edit_text(
                T.admin_bc_done.format(
                    total=result.total,
                    sent=result.sent,
                    failed=result.failed,
                ),
                reply_markup=kb_dash("adm:bc"),
            )
    except BroadcastBusyError:
        with suppress(TelegramAPIError):
            await progress_msg.edit_text(T.admin_bc_failed, reply_markup=kb_dash("adm:bc"))
    except asyncio.CancelledError:
        log.warning("broadcast_cancelled")
        raise
    except Exception:
        # Граница фоновой asyncio-задачи: исключение иначе останется unobserved.
        log.exception("broadcast_job_failed")
        with suppress(TelegramAPIError):
            await progress_msg.edit_text(T.admin_bc_failed, reply_markup=kb_dash("adm:bc"))
    finally:
        _active_task = None


async def shutdown_active_broadcast(timeout: float = 20.0) -> None:
    """Даёт рассылке завершиться при shutdown, затем аккуратно отменяет."""
    task = _active_task
    if task is None or task.done():
        return
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
    except TimeoutError:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@router.callback_query(F.data == "adm:bc")
async def cb_open(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    count = len(await UserRepo(session).list_broadcast_tg_ids())
    await state.set_state(BroadcastStates.waiting_text)
    with suppress(TelegramAPIError):
        await callback.message.edit_text(
            T.admin_bc_intro.format(count=count), reply_markup=kb_bc_cancel()
        )
    await callback.answer()


@router.message(BroadcastStates.waiting_text, F.text)
async def msg_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = (message.html_text or "").strip()
    if not text:
        await message.answer(T.admin_bc_empty)
        return
    if len(message.text or "") > _MAX_BROADCAST_TEXT:
        await message.answer(
            T.admin_bc_too_long.format(max_len=_MAX_BROADCAST_TEXT),
            reply_markup=kb_bc_cancel(),
        )
        return
    count = len(await UserRepo(session).list_broadcast_tg_ids())
    await state.set_state(BroadcastStates.confirming)
    await state.update_data(bc_text=text)
    await message.answer(
        T.admin_bc_preview.format(text=text, count=count),
        reply_markup=kb_bc_confirm(),
    )


@router.callback_query(BroadcastStates.confirming, F.data == "adm:bc:go")
async def cb_go(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    data = await state.get_data()
    text = data.get("bc_text", "")
    await state.clear()
    if not text:
        await callback.answer(T.admin_bc_empty, show_alert=True)
        return

    global _active_task
    async with _launch_lock:
        if _active_task is not None and not _active_task.done():
            await callback.answer(T.admin_bc_busy_alert, show_alert=True)
            return
        tg_ids = await UserRepo(session).list_broadcast_tg_ids()
        progress_msg = callback.message
        with suppress(TelegramAPIError):
            await progress_msg.edit_text(
                T.admin_bc_progress.format(done=0, total=len(tg_ids))
            )
        _active_task = asyncio.create_task(
            _broadcast_job(
                bot=bot,
                tg_ids=tg_ids,
                text=text,
                progress_msg=progress_msg,
                actor_tg_id=callback.from_user.id if callback.from_user else None,
            ),
            name="admin-broadcast",
        )
    await callback.answer()
