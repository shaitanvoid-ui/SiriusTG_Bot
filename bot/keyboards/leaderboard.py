from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales.ru import T


_PERIOD_LABELS = (
    ("week", T.top_period_week),
    ("month", T.top_period_month),
    ("all", T.top_period_all),
)


def kb_leaderboard(period: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for value, label in _PERIOD_LABELS:
        text = f"• {label} •" if value == period else label
        b.button(text=text, callback_data=f"top:p:{value}")
    b.button(text=T.btn_top_refresh, callback_data=f"top:p:{period}")
    b.button(text=T.btn_top_back, callback_data="prof:open")
    b.adjust(3, 2)
    return b.as_markup()
