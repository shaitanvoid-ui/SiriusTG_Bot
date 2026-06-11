"""Опциональные задания — список активных опц.спонсоров и кнопка «Проверить»."""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router, html
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.tasks import kb_task_card, kb_tasks_list
from db.models import User
from db.repositories.sponsor import SponsorRepo
from db.repositories.user import UserRepo
from db.repositories.user_task_completion import UserTaskCompletionRepo
from locales.ru import T
from services.settings import SettingsService
from services.sponsor import SponsorService
from services.tasks import ClaimResult, TasksService, TaskStatus
from utils.ui import stars


router = Router(name="tasks")


def _render_list(items_count: int, active_count: int) -> str:
    if items_count == 0:
        return T.tasks_empty
    return T.tasks_list_caption.format(active=active_count)


@router.callback_query(F.data == "tsk:list")
async def cb_list(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return

    svc = TasksService(session, SettingsService(session))
    if not await svc.enabled():
        with suppress(Exception):
            await callback.message.edit_text(T.tasks_disabled, reply_markup=kb_tasks_list([]))
        await callback.answer()
        return

    items = await svc.list_for_user(user)
    active = sum(1 for i in items if not i.is_completed)
    text = _render_list(len(items), active)
    with suppress(Exception):
        await callback.message.edit_text(text, reply_markup=kb_tasks_list(items))
    await callback.answer()


def _format_card(sponsor, *, is_completed: bool) -> str:
    title = html.quote(sponsor.title)
    reward = stars(sponsor.reward)
    if is_completed:
        status_line = T.task_card_completed
    else:
        status_line = T.task_card_pending
    return T.task_card.format(
        title=title,
        reward=reward,
        status_line=status_line,
    )


@router.callback_query(F.data.startswith("tsk:open:"))
async def cb_open(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.data is None or callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    try:
        sponsor_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer()
        return
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return

    sponsor = await SponsorRepo(session).get(sponsor_id)
    if sponsor is None or sponsor.is_required or not sponsor.is_active:
        await callback.answer(T.task_not_found_alert, show_alert=True)
        return

    completion = await UserTaskCompletionRepo(session).get(user.id, sponsor.id)
    is_completed = completion is not None
    url = SponsorService.display_link(sponsor) or None
    text = _format_card(sponsor, is_completed=is_completed)
    with suppress(Exception):
        await callback.message.edit_text(
            text,
            reply_markup=kb_task_card(sponsor.id, url, is_completed=is_completed),
            disable_web_page_preview=True,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("tsk:claim:"))
async def cb_claim(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.data is None or callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    try:
        sponsor_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer()
        return
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return

    svc = TasksService(session, SettingsService(session))
    if callback.bot is None:
        await callback.answer()
        return
    res: ClaimResult = await svc.claim(callback.bot, user=user, sponsor_id=sponsor_id)

    if res.status == TaskStatus.OK:
        await callback.answer(
            T.task_claim_ok_alert.format(reward=stars(res.reward)),
            show_alert=False,
        )
        # перерисуем карточку как «выполнено»
        sponsor = await SponsorRepo(session).get(sponsor_id)
        if sponsor is not None and callback.message is not None:
            url = SponsorService.display_link(sponsor) or None
            text = _format_card(sponsor, is_completed=True)
            with suppress(Exception):
                await callback.message.edit_text(
                    text,
                    reply_markup=kb_task_card(sponsor.id, url, is_completed=True),
                    disable_web_page_preview=True,
                )
        return

    if res.status == TaskStatus.NOT_SUBSCRIBED:
        await callback.answer(T.task_not_subscribed_alert, show_alert=True)
        return
    if res.status == TaskStatus.ALREADY_DONE:
        await callback.answer(T.task_already_done_alert, show_alert=False)
        return
    if res.status == TaskStatus.LIMIT_REACHED:
        await callback.answer(T.task_limit_reached_alert, show_alert=True)
        return
    if res.status == TaskStatus.NOT_FOUND or res.status == TaskStatus.INACTIVE:
        await callback.answer(T.task_not_found_alert, show_alert=True)
        return
    if res.status == TaskStatus.NO_REWARD:
        await callback.answer(T.task_no_reward_alert, show_alert=True)
        return
    if res.status == TaskStatus.DISABLED:
        await callback.answer(T.tasks_disabled_alert, show_alert=True)
        return
    await callback.answer(T.error_generic, show_alert=False)
