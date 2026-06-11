"""Клавиатуры для отзывов."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales.ru import T


def kb_review_intro() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_review_start, callback_data="rev:start")
    b.button(text="◀ В меню", callback_data="nav:menu")
    b.adjust(1, 1)
    return b.as_markup()


def kb_review_rating(current: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    stars = ["○ 1⭐", "○ 2⭐", "○ 3⭐", "○ 4⭐", "○ 5⭐"]
    for i, label in enumerate(stars, 1):
        prefix = "✅ " if i <= current else ""
        b.button(text=prefix + label, callback_data=f"rev:star:{i}")
    b.button(text=T.btn_review_next, callback_data="rev:rating_next")
    b.button(text=T.btn_review_cancel, callback_data="rev:cancel")
    b.adjust(5, 1, 1)
    return b.as_markup()


def kb_review_text_step() -> InlineKeyboardMarkup:
    """Шаг ввода текста: юзер пишет сообщением, кнопка — только отмена."""
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_review_cancel, callback_data="rev:cancel")
    b.adjust(1)
    return b.as_markup()


def kb_review_anonymity() -> InlineKeyboardMarkup:
    """Шаг анонимности: с username / анонимно."""
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_review_public, callback_data="rev:anon_no")
    b.button(text=T.btn_review_anonymous, callback_data="rev:anon_yes")
    b.button(text=T.btn_review_cancel, callback_data="rev:cancel")
    b.adjust(1, 1, 1)
    return b.as_markup()


def kb_review_confirm() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_review_confirm, callback_data="rev:confirm")
    b.button(text=T.btn_review_cancel, callback_data="rev:cancel")
    b.adjust(1, 1)
    return b.as_markup()


def kb_review_success() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀ В меню", callback_data="nav:menu")
    b.adjust(1)
    return b.as_markup()
