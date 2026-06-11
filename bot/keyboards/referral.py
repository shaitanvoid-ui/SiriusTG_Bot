from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales.ru import T


def kb_referral(*, share_url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_ref_copy_text, callback_data="ref:txt")
    b.button(text=T.btn_ref_share, url=share_url)
    b.button(text="◀ В меню", callback_data="nav:menu")
    b.adjust(2, 1)
    return b.as_markup()


def kb_referral_text_view() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_ref_back, callback_data="ref:open")
    b.button(text="◀ В меню", callback_data="nav:menu")
    b.adjust(2)
    return b.as_markup()
