from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T
from utils.ui import stars


def kb_wheel(*, free_available: bool, can_pay: bool, cost: float) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if free_available:
        b.button(text=T.btn_wheel_free, callback_data="whl:spin:free")
    if can_pay:
        b.button(
            text=T.btn_wheel_paid.format(cost=stars(cost)),
            callback_data="whl:confirm",
        )
    else:
        b.button(text=T.btn_wheel_locked, callback_data="whl:noop")
    b.button(text=T.btn_wheel_refresh, callback_data="whl:open")
    b.footer(text=T.btn_back_earn, callback_data="sec:earn")
    if free_available:
        b.adjust(1, 1, 2)
    else:
        b.adjust(1, 2)
    return b.as_markup()


def kb_paid_confirmation(*, token: str, cost: float) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn_wheel_confirm.format(cost=stars(cost)), callback_data=f"whl:paid:{token}", style="primary")
    builder.button(text=T.btn_cancel, callback_data="whl:open")
    builder.adjust(1, 1)
    return builder.as_markup()
