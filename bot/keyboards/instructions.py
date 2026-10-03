"""Клавиатуры для инструкции."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, DisabledButton, InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T


router = Router(name="instructions_kb")


def kb_instruction_page(page_idx: int = 0, total: int = 1) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if total > 1:
        position = f"{page_idx + 1}/{total}"
        if page_idx > 0:
            b.button(text=f"‹ {position}", callback_data="ins:page:-1")
        else:
            b.button(text=f"‹ {position}", disabled=DisabledButton())
        if page_idx + 1 < total:
            b.button(text=f"{position} ›", callback_data="ins:page:1")
        else:
            b.button(text=f"{position} ›", disabled=DisabledButton())
    b.footer(text=T.btn_ins_back, callback_data="sec:help")
    if total > 1:
        b.adjust(2, 2)
    else:
        b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == "ins:noop")
async def cb_ins_noop(callback: CallbackQuery) -> None:
    await callback.answer()
