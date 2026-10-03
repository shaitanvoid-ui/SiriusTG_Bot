"""Клавиатуры подразделов: Заработать, Помощь, Профиль."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T


def kb_earn() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_earn_clicker, callback_data="clk:open")
    b.button(text=T.btn_earn_bonus, callback_data="bns:open")
    b.button(text=T.btn_earn_wheel, callback_data="whl:open")
    b.button(text=T.btn_earn_tasks, callback_data="tsk:list")
    b.footer(text=T.btn_back_menu, callback_data="nav:menu")
    b.adjust(2, 2, 1)
    return b.as_markup()


def kb_help() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_help_instructions, callback_data="ins:open")
    b.button(text=T.btn_help_support, callback_data="sup:open")
    b.button(text=T.btn_help_review, callback_data="rev:intro")
    b.footer(text=T.btn_back_menu, callback_data="nav:menu")
    b.adjust(2, 1, 1)
    return b.as_markup()


def kb_profile(*, is_partner: bool = False) -> InlineKeyboardMarkup:
    """Под карточкой профиля — быстрые переходы в подсекции."""
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_profile_promo, callback_data="promo:open")
    b.button(text=T.btn_profile_achievements, callback_data="ach:open")
    b.button(text=T.btn_profile_history, callback_data="hist:open")
    b.button(text=T.btn_profile_top, callback_data="top:open")
    b.button(text=T.btn_profile_notifications, callback_data="ntf:open")
    rows = [2, 2]
    if is_partner:
        b.button(text=T.btn_profile_partner, callback_data="pa:open")
        rows.append(2)
    else:
        rows.append(1)
    b.footer(text=T.btn_back_menu, callback_data="nav:menu")
    rows.append(1)
    b.adjust(*rows)
    return b.as_markup()
