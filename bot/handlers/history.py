"""История операций в профиле (Этап 11): пагинированная лента ⭐-движений."""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.history import kb_history
from db.models import User
from locales.ru import T
from services.history import HistoryPage, HistoryService

router = Router(name="history")


def _signed(amount: float) -> str:
    if amount > 0:
        return f"+{amount:.2f}⭐"
    if amount < 0:
        return f"−{abs(amount):.2f}⭐"
    return "0.00⭐"


def render_history(page: HistoryPage) -> str:
    if not page.entries:
        return T.history_empty
    rows = "\n".join(
        T.history_row.format(
            emoji=e.emoji, amount=_signed(e.amount), title=e.title, when=e.when
        )
        for e in page.entries
    )
    return T.history_card.format(rows=rows, page=page.page, total_pages=page.total_pages)


async def _show_page(
    callback: CallbackQuery, session: AsyncSession, db_user: User, page_num: int
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    page = await HistoryService(session).page_for(db_user, page_num)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            render_history(page), reply_markup=kb_history(page.page, page.total_pages)
        )
    await callback.answer()


@router.callback_query(F.data == "hist:open")
async def cb_open(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    await _show_page(callback, session, db_user, 1)


@router.callback_query(F.data.startswith("hist:p:"))
async def cb_page(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    page_num = int((callback.data or "1").rsplit(":", 1)[-1])
    await _show_page(callback, session, db_user, page_num)
