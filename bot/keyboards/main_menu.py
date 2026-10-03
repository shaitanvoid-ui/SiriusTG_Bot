from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T


def kb_main_menu(*, channel_url: str | None = None, next_label: str | None = None,
                 next_callback: str | None = None) -> InlineKeyboardMarkup:
    """Главное меню только с доступными пользовательскими разделами."""
    b = InlineKeyboardBuilder()

    # Одна главная цель, затем компактная навигация по разделам.
    b.button(text=T.btn_menu_gifts, callback_data="gift:open", style="primary")
    b.button(text=T.btn_menu_daily, callback_data="day:open")
    b.button(text=T.btn_menu_earn, callback_data="sec:earn")
    b.button(text=T.btn_menu_profile, callback_data="prof:open")
    b.button(text=T.btn_menu_referrals, callback_data="ref:open")
    if next_label and next_callback and next_callback not in {"gift:open", "day:open", "sec:earn", "prof:open", "ref:open", "sec:help"}:
        b.button(text=next_label, callback_data=next_callback)
        next_row = [1]
    else:
        next_row = []
    b.button(text=T.btn_menu_help, callback_data="sec:help")
    if channel_url:
        b.button(text=T.btn_menu_channel, url=channel_url)
    b.adjust(1, 2, 2, *next_row, 2 if channel_url else 1)
    return b.as_markup()
