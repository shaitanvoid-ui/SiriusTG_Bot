"""Клавиатура истории операций (Этап 11): пагинация."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T


def kb_history(page: int, total_pages: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    nav_row = 0
    if page > 1:
        b.button(text=T.btn_history_prev, callback_data=f"hist:p:{page - 1}")
        nav_row += 1
    if page < total_pages:
        b.button(text=T.btn_history_next, callback_data=f"hist:p:{page + 1}")
        nav_row += 1
    b.footer(text=T.btn_back_profile, callback_data="prof:open")
    rows = ([nav_row] if nav_row else []) + [2]
    b.adjust(*rows)
    return b.as_markup()
