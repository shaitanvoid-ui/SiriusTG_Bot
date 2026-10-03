from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T
from utils.ui import clock_mmss


def kb_clicker(*, can_click: bool, cooldown_ms_left: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if not can_click:
        # лимит достигнут — оставляем заглушку, чтобы кнопка не пропадала
        b.button(text=T.btn_click_limit_reached, callback_data="clk:noop")
    elif cooldown_ms_left > 0:
        # идёт перезарядка — кнопка показывает таймер, но остаётся «живой»:
        # тап до готовности вернёт алерт со временем и обновит карточку.
        b.button(
            text=T.btn_click_cooldown.format(time=clock_mmss(cooldown_ms_left)),
            callback_data="clk:tap",
        )
    else:
        b.button(text=T.btn_click_tap, callback_data="clk:tap")
    b.button(text=T.btn_click_refresh, callback_data="clk:open")
    b.button(text=T.btn_back_earn, callback_data="sec:earn")
    b.adjust(1, 2)
    return b.as_markup()


def kb_clicker_captcha(token: str, choices: tuple[str, ...]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for emoji in choices:
        b.button(text=emoji, callback_data=f"clk:cap:{token}:{emoji}")
    b.button(text=T.btn_click_cancel, callback_data="sec:earn")
    b.adjust(len(choices), 1)
    return b.as_markup()
