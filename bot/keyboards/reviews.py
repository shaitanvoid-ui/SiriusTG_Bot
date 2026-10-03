"""Клавиатуры для отзывов."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T


def kb_review_intro() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_review_start, callback_data="rev:start")
    b.button(text=T.btn_back_help, callback_data="sec:help")
    b.adjust(1, 1)
    return b.as_markup()


def kb_review_rating(current: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i in range(1, 6):
        marker = "●" if i == current else "○"
        b.button(text=f"{marker} {i} ⭐", callback_data=f"rev:star:{i}")
    b.button(text=T.btn_review_next, callback_data="rev:rating_next")
    b.button(text=T.btn_review_cancel, callback_data="rev:cancel")
    b.adjust(3, 2, 1, 1)
    return b.as_markup()


def kb_review_text_step() -> InlineKeyboardMarkup:
    """Шаг ввода текста: можно вернуться к оценке или отменить сценарий."""
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_review_back, callback_data="rev:back:rating")
    b.button(text=T.btn_review_cancel, callback_data="rev:cancel")
    b.adjust(2)
    return b.as_markup()


def kb_review_anonymity() -> InlineKeyboardMarkup:
    """Шаг анонимности: с username / анонимно."""
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_review_public, callback_data="rev:anon_no")
    b.button(text=T.btn_review_anonymous, callback_data="rev:anon_yes")
    b.button(text=T.btn_review_back, callback_data="rev:back:text")
    b.button(text=T.btn_review_cancel, callback_data="rev:cancel")
    b.adjust(1, 1, 2)
    return b.as_markup()


def kb_review_confirm() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_review_confirm, callback_data="rev:confirm")
    b.button(text=T.btn_review_back, callback_data="rev:back:anon")
    b.button(text=T.btn_review_cancel, callback_data="rev:cancel")
    b.adjust(1, 2)
    return b.as_markup()


def kb_review_success() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_back_help, callback_data="sec:help")
    b.adjust(1)
    return b.as_markup()
