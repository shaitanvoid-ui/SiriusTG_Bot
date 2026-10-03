from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T


def kb_bonus(*, can_claim: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if can_claim:
        b.button(text=T.btn_bonus_claim, callback_data="bns:claim")
    else:
        b.button(text=T.btn_bonus_claimed, callback_data="bns:noop")
    b.button(text=T.btn_bonus_refresh, callback_data="bns:open")
    b.button(text=T.btn_back_earn, callback_data="sec:earn")
    b.adjust(1, 2)
    return b.as_markup()
