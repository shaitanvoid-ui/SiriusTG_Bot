"""Клавиатуры админки отзывов."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales.ru import T


def kb_reviews_list() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_admin_reviews, callback_data="adm:rev:list")
    b.button(text=T.btn_admin_back_from_reviews, callback_data="adm:root")
    b.adjust(1, 1)
    return b.as_markup()


def kb_review_mod_actions(review_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_review_approve, callback_data=f"adm:rev:approve:{review_id}")
    b.button(text=T.btn_review_reject, callback_data=f"adm:rev:reject:{review_id}")
    b.button(text=T.btn_review_convert, callback_data=f"adm:rev:convert:{review_id}")
    b.button(text=T.btn_review_mod_back, callback_data="adm:rev:list")
    b.adjust(1, 2, 1)
    return b.as_markup()
