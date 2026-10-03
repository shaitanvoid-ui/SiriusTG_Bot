from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

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
    b.footer(text=T.btn_top_back, callback_data="prof:open")
    b.adjust(2, 1, 1, 2)
    return b.as_markup()
