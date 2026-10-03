from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup

from locales.ru import T
from services.dashboard import DailyAction
from utils.keyboards import SiriusKeyboardBuilder


def kb_daily(actions: tuple[DailyAction, ...]) -> InlineKeyboardMarkup:
    builder = SiriusKeyboardBuilder()
    for action in actions:
        if not action.complete:
            builder.button(text=action.label, callback_data=action.callback)
    builder.button(text=T.btn_refresh, callback_data="day:open")
    builder.footer(text=T.btn_back_menu, callback_data="nav:menu")
    builder.adjust(*([1] * sum(not action.complete for action in actions)), 1, 1)
    return builder.as_markup()
