from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales.ru import T


def kb_achievements() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_ach_refresh, callback_data="ach:open")
    b.button(text=T.btn_ach_back, callback_data="prof:open")
    b.adjust(2)
    return b.as_markup()
