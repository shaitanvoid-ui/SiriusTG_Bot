"""Настройки уведомлений в профиле (Этап 11): тумблеры категорий DM."""

from __future__ import annotations

from utils.telegram import ignore_unchanged


from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.notifications import kb_notifications
from db.models import User
from locales.ru import T
from services.notifications import CATEGORIES, NotificationService

router = Router(name="notifications")


def _render_card(prefs: dict[str, bool]) -> str:
    rows = []
    for code, (emoji, name, hint) in CATEGORIES.items():
        template = T.notifications_row_on if prefs.get(code, True) else T.notifications_row_off
        rows.append(template.format(emoji=emoji, name=name, hint=hint))
    return T.notifications_card.format(rows="\n".join(rows))


@router.callback_query(F.data == "ntf:open")
async def cb_open(callback: CallbackQuery, db_user: User) -> None:
    if callback.message is None:
        await callback.answer()
        return
    prefs = NotificationService.prefs_of(db_user)
    with ignore_unchanged():
        await callback.message.edit_text(
            _render_card(prefs), reply_markup=kb_notifications(prefs)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ntf:t:"))
async def cb_toggle(
    callback: CallbackQuery, session: AsyncSession, db_user: User
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    category = (callback.data or "").rsplit(":", 1)[-1]
    prefs = NotificationService.toggle(db_user, category)
    await session.flush()
    with ignore_unchanged():
        await callback.message.edit_text(
            _render_card(prefs), reply_markup=kb_notifications(prefs)
        )
    enabled = prefs.get(category, True)
    await callback.answer(
        T.notifications_toggled_on_alert if enabled else T.notifications_toggled_off_alert
    )
