from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T


def kb_achievements() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_ach_refresh, callback_data="ach:open")
    b.footer(text=T.btn_ach_back, callback_data="prof:open")
    b.adjust(1, 2)
    return b.as_markup()
