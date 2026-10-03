from __future__ import annotations

from aiogram.types import CopyTextButton, InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T


def kb_referral(*, share_url: str, invite_link: str | None = None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if invite_link:
        b.button(text=T.btn_ref_copy_link, copy_text=CopyTextButton(text=invite_link), style="primary")
        b.button(text=T.btn_ref_copy_text, callback_data="ref:txt")
        b.button(text=T.btn_ref_share, url=share_url)
    else:
        b.button(text=T.btn_ref_share, url=share_url, style="primary")
        b.button(text=T.btn_ref_copy_text, callback_data="ref:txt")
    b.footer(text=T.btn_back_menu, callback_data="nav:menu")
    b.adjust(1, *([2] if invite_link else [1]), 1)
    return b.as_markup()


def kb_referral_text_view() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.footer(text=T.btn_ref_back, callback_data="ref:open")
    b.adjust(2)
    return b.as_markup()
