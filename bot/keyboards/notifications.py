"""Клавиатура настроек уведомлений (Этап 11)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
    b.button(text="◀ В профиль", callback_data="prof:open")
    b.adjust(*([1] * (len(CATEGORIES) + 1)))
    return b.as_markup()
