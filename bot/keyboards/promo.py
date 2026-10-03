from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T


def kb_promo_intro() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_promo_enter, callback_data="promo:start")
    b.footer(text=T.btn_promo_back_profile, callback_data="prof:open")
    b.adjust(1, 2)
    return b.as_markup()


def kb_promo_waiting() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_promo_cancel, callback_data="promo:cancel")
    b.adjust(1)
    return b.as_markup()


def kb_promo_result() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_promo_again, callback_data="promo:start")
    b.footer(text=T.btn_promo_back_profile, callback_data="prof:open")
    b.adjust(1, 2)
    return b.as_markup()
