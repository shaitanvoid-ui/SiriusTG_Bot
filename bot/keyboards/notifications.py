"""Клавиатура настроек уведомлений (Этап 11)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T
from services.notifications import CATEGORIES


def kb_notifications(prefs: dict[str, bool]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for code, (emoji, name, _hint) in CATEGORIES.items():
        template = T.btn_notifications_on if prefs.get(code, True) else T.btn_notifications_off
        b.button(
            text=template.format(emoji=emoji, name=name),
            callback_data=f"ntf:t:{code}",
        )
    b.footer(text=T.btn_back_profile, callback_data="prof:open")
    b.adjust(*([1] * len(CATEGORIES)), 2)
    return b.as_markup()
