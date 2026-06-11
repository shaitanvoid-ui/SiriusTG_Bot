"""Клавиатуры для инструкции."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales.ru import T


router = Router(name="instructions_kb")


def kb_instruction_page(page_idx: int = 0, total: int = 1) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if total > 1:
        b.button(text="◀", callback_data="ins:page:-1")
        b.button(text=f"{page_idx + 1}/{total}", callback_data="ins:noop")
        b.button(text="▶", callback_data="ins:page:1")
    b.button(text="◀ В меню", callback_data="nav:menu")
    if total > 1:
        b.adjust(3, 1)
    else:
        b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == "ins:noop")
async def cb_ins_noop(callback: CallbackQuery) -> None:
    await callback.answer()
