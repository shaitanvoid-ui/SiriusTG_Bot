"""Админка: рассылка по всем юзерам (Этап 9).

FSM: текст → предпросмотр → подтверждение → отправка с прогрессом.
Отправка идёт в текущем хендлере (для текущих объёмов это ок);
прогресс — edit-in-place каждые 25 отправок.
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.admin_panel import kb_bc_cancel, kb_bc_confirm, kb_dash
from bot.states.admin import BroadcastStates
from db.repositories.action_log import ActionLogRepo
from db.repositories.user import UserRepo
from locales.ru import T
from services.broadcast import run_broadcast


router = Router(name="admin_broadcast")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "adm:bc")
async def cb_open(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    count = len(await UserRepo(session).list_broadcast_tg_ids())
    await state.set_state(BroadcastStates.waiting_text)
    with suppress(Exception):
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

    tg_ids = await UserRepo(session).list_broadcast_tg_ids()
    await callback.answer()

    progress_msg = callback.message

    async def _progress(done: int, total: int) -> None:
        with suppress(Exception):
            await progress_msg.edit_text(T.admin_bc_progress.format(done=done, total=total))

    with suppress(Exception):
        await progress_msg.edit_text(T.admin_bc_progress.format(done=0, total=len(tg_ids)))

    result = await run_broadcast(bot, tg_ids, text, progress_cb=_progress)

    await ActionLogRepo(session).log(
        user_tg_id=callback.from_user.id if callback.from_user else None,
        action="admin_broadcast",
        payload={"total": result.total, "sent": result.sent, "failed": result.failed},
    )
    with suppress(Exception):
        await progress_msg.edit_text(
            T.admin_bc_done.format(
                total=result.total, sent=result.sent, failed=result.failed
            ),
            reply_markup=kb_dash("adm:bc"),
        )
