"""Премиум-форматтеры и шаблоны для inline-UI."""

from __future__ import annotations

from typing import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ---------- константы оформления ----------

DIVIDER: str = "━━━━━━━━━━━━━━━━━━━"
DIVIDER_THIN: str = "─────────────────"
SOFT_DIVIDER: str = "·  ·  ·"
BULLET: str = "▸"
DOT: str = "•"

# универсальные ярлыки кнопок
BTN_BACK: str = "◀ Назад"
BTN_BACK_MENU: str = "◀ В меню"
BTN_CLOSE: str = "✕ Закрыть"
BTN_ADD: str = "➕ Добавить"
BTN_CANCEL: str = "✕ Отменить"
BTN_RETRY: str = "🔄 Ещё раз"
BTN_CONFIRM: str = "✅ Подтвердить"


# ---------- форматирование текста ----------

def title(emoji: str, text: str) -> str:
    """Заголовок секции: '✨ <b>Текст</b>'."""
    return f"{emoji} <b>{text}</b>"


def card(*lines: str) -> str:
    """Карточка: заголовок + разделитель + тело."""
    return f"\n{DIVIDER}\n".join(lines)


def kv(label: str, value: str) -> str:
    """'Ключ: <b>значение</b>'."""
    return f"{label}: <b>{value}</b>"


def step(current: int, total: int) -> str:
    return f"<i>Шаг {current} из {total}</i>"


def stars(amount: float) -> str:
    """'15.00⭐' — единый стиль форматирования звёзд."""
    return f"{amount:.2f}⭐"


def section_label(text: str) -> str:
    """Метка-раздел с маркером: '▸ <b>ТЕКСТ</b>'."""
    return f"{BULLET}  <b>{text.upper()}</b>"


def progress_bar(current: int, total: int, *, width: int = 12) -> str:
    """Премиум прогресс-бар на юникод-блоках. '▰▰▰▰▱▱▱▱▱▱'."""
    if total <= 0:
        ratio = 1.0
    else:
        ratio = max(0.0, min(1.0, current / total))
    filled = round(ratio * width)
    filled = max(0, min(width, filled))
    return "▰" * filled + "▱" * (width - filled)


def mini_bar(current: int, total: int, *, width: int = 8) -> str:
    """Компактный прогресс-бар для строк-списков: '▰▰▱▱▱▱▱▱'."""
    return progress_bar(current, total, width=width)


def human_duration(ms: int) -> str:
    """Человеко-читаемая длительность: '4 мин 32 сек', '45 сек', '5 мин'."""
    total = max(0, round(ms / 1000))
    minutes, seconds = divmod(total, 60)
    if minutes and seconds:
        return f"{minutes} мин {seconds} сек"
    if minutes:
        return f"{minutes} мин"
    return f"{seconds} сек"


def clock_mmss(ms: int) -> str:
    """Компактный таймер для кнопки: '4:32', '5:00', '0:05'."""
    total = max(0, round(ms / 1000))
    minutes, seconds = divmod(total, 60)
    return f"{minutes}:{seconds:02d}"


def brand_header(brand_name: str, tagline: str) -> str:
    """Шапка бренда: '✦ <b>SIRIUS</b> ✦  ·  <i>Stars Hub</i>'."""
    return f"✦ <b>{brand_name}</b> ✦  ·  <i>{tagline}</i>"


def kvline(label: str, value: str, *, pad: int = 14) -> str:
    """Выровненная пара 'Ярлык          значение' для табличных карточек."""
    padded = label.ljust(pad)
    return f"   {padded}<b>{value}</b>"


# ---------- клавиатуры ----------

def kb_single(text: str, callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=callback_data)]]
    )


def kb_two(
    left_text: str,
    left_cb: str,
    right_text: str,
    right_cb: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=left_text, callback_data=left_cb),
            InlineKeyboardButton(text=right_text, callback_data=right_cb),
        ]]
    )


def kb_back(callback_data: str = "nav:back") -> InlineKeyboardMarkup:
    return kb_single(BTN_BACK, callback_data)


def kb_back_to_menu() -> InlineKeyboardMarkup:
    return kb_single(BTN_BACK_MENU, "nav:menu")


def kb_close(callback_data: str = "nav:close") -> InlineKeyboardMarkup:
    return kb_single(BTN_CLOSE, callback_data)


def builder() -> InlineKeyboardBuilder:
    return InlineKeyboardBuilder()


def rows(*row_specs: Iterable[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in row_specs])
