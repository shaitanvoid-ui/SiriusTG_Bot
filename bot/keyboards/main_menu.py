from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales.ru import T


def kb_main_menu(*, channel_url: str | None = None) -> InlineKeyboardMarkup:
    """Главное меню — 6 крупных хабов с иерархической навигацией."""
    b = InlineKeyboardBuilder()

    # Ряд 1: главное действие — «Заработать», на всю ширину
    b.button(text=T.btn_menu_earn, callback_data="sec:earn")

    # Ряд 2: ключевые механики
    b.button(text=T.btn_menu_referrals, callback_data="ref:open")
    b.button(text=T.btn_menu_withdraw, callback_data="feat:soon:withdraw")

    # Ряд 3: личное + помощь
    b.button(text=T.btn_menu_profile, callback_data="prof:open")
    b.button(text=T.btn_menu_help, callback_data="sec:help")

    # Ряд 4: канал (URL если настроен)
    if channel_url:
        b.button(text=T.btn_menu_channel, url=channel_url)
    else:
        b.button(text=T.btn_menu_channel, callback_data="feat:soon:channel")

    b.adjust(1, 2, 2, 1)
    return b.as_markup()
