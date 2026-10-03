"""Personal daily route; availability comes from existing economy rules."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.daily import kb_daily
from db.models import User
from locales.ru import T
from services.dashboard import DashboardService
from services.settings import SettingsService
from utils.ui import html_text
from utils.telegram import ignore_unchanged


router = Router(name="daily")


@router.callback_query(F.data == "day:open")
async def cb_open(callback: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext) -> None:
    await state.clear()
    if callback.message is None:
        await callback.answer()
        return
    await callback.answer()
    view = await DashboardService(session, SettingsService(session)).get_view(db_user)
    rows = "\n\n".join(T.daily_action_row.format(
        marker="✓" if action.complete else "○",
        label=html_text(action.label), detail=html_text(action.detail),
    ) for action in view.actions)
    with ignore_unchanged():
        await callback.message.edit_text(T.daily_caption.format(
            rows=rows, reset=view.next_reset.strftime("%H:%M"), reset_unix=int(view.next_reset.timestamp()),
        ), reply_markup=kb_daily(view.actions))
