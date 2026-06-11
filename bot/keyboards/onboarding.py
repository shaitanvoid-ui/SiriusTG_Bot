from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models import Sponsor
from locales.ru import T
from services.sponsor import SponsorService


def kb_terms_page(page: int, total: int) -> InlineKeyboardMarkup:
    """Кнопки навигации страниц соглашения. На последней — Принимаю / Не принимаю."""
    rows: list[list[InlineKeyboardButton]] = []

    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text=T.terms_prev_btn, callback_data=f"terms:p:{page - 1}"))
    if page < total:
        nav.append(InlineKeyboardButton(text=T.terms_next_btn, callback_data=f"terms:p:{page + 1}"))
    if nav:
        rows.append(nav)

    if page == total:
        rows.append([InlineKeyboardButton(text=T.terms_accept_btn, callback_data="terms:accept")])
        rows.append([InlineKeyboardButton(text=T.terms_decline_btn, callback_data="terms:decline")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_captcha(choices: tuple[str, ...], token: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for emoji in choices:
        b.button(text=emoji, callback_data=f"cap:{token}:{emoji}")
    # все 4 варианта на одной строке
    b.adjust(len(choices))
    return b.as_markup()


def kb_subs(sponsors: list[Sponsor]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in sponsors:
        url = SponsorService.display_link(s)
        if url:
            b.button(text=f"{T.subs_open_btn_prefix} {s.title}", url=url)
    b.button(text=T.subs_check_btn, callback_data="subs:check")
    b.adjust(*([1] * len(sponsors)), 1)
    return b.as_markup()
