from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T


def kb_main_menu(*, channel_url: str | None = None, next_label: str | None = None,
                 next_callback: str | None = None) -> InlineKeyboardMarkup:
    """Главное меню только с доступными пользовательскими разделами."""
    b = InlineKeyboardBuilder()

    if next_label and next_callback:
        b.button(text=next_label, callback_data=next_callback, style="success")
    b.button(text=T.btn_menu_daily, callback_data="day:open")
    b.button(text=T.btn_menu_earn, callback_data="sec:earn")

    # Подарки получают с текущего аккаунта Telegram после явного подтверждения.
    b.button(text=T.btn_menu_gifts, callback_data="gift:open")

    # Рефералы и личный кабинет.
    b.button(text=T.btn_menu_referrals, callback_data="ref:open")
    b.button(text=T.btn_menu_profile, callback_data="prof:open")

    # Ряд 3: помощь + официальный канал
    b.button(text=T.btn_menu_help, callback_data="sec:help")

    # Ряд 4: канал (URL если настроен)
    if channel_url:
        b.button(text=T.btn_menu_channel, url=channel_url)

    b.adjust(*([1] if next_label and next_callback else []), 2, 1, 2, 2)
    return b.as_markup()
