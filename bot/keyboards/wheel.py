from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales.ru import T
from utils.ui import stars


def kb_wheel(*, free_available: bool, can_pay: bool, cost: float) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if free_available:
        b.button(text=T.btn_wheel_free, callback_data="whl:spin:free")
    b.button(text=T.btn_wheel_paid.format(cost=stars(cost)), callback_data="whl:spin:paid")
    b.button(text=T.btn_wheel_refresh, callback_data="whl:open")
    b.button(text="◀ В меню", callback_data="nav:menu")
    if free_available:
        b.adjust(1, 1, 2)
    else:
        b.adjust(1, 2)
    return b.as_markup()
