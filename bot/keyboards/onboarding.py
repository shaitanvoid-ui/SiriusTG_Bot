from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from db.models import Sponsor
from locales.ru import T
from services.sponsor import SponsorService
from utils.ui import button_text


def kb_terms_page(page: int, total: int) -> InlineKeyboardMarkup:
    """Кнопки навигации страниц соглашения. На последней — Принимаю / Не принимаю."""
    b = InlineKeyboardBuilder()
    navigation = 0
    if page > 1:
        b.button(text=T.terms_prev_btn, callback_data=f"terms:p:{page - 1}")
        navigation += 1
    if page < total:
        b.button(text=T.terms_next_btn, callback_data=f"terms:p:{page + 1}")
        navigation += 1

    if page == total:
        b.button(text=T.terms_accept_btn, callback_data="terms:accept")
        b.button(text=T.terms_decline_btn, callback_data="terms:decline")
    b.adjust(*([navigation] if navigation else []), *([1, 1] if page == total else []))
    return b.as_markup()


def kb_captcha(choices: tuple[str, ...], token: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for emoji in choices:
        b.button(text=emoji, callback_data=f"cap:{token}:{emoji}")
    # все 4 варианта на одной строке
    b.adjust(len(choices))
    return b.as_markup()


def kb_subs(sponsors: list[Sponsor]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    shown = 0
    for s in sponsors:
        url = SponsorService.display_link(s)
        if url:
            b.button(
                text=button_text(f"{T.subs_open_btn_prefix} {s.title}"),
                url=url,
            )
            shown += 1
    b.button(text=T.subs_check_btn, callback_data="subs:check")
    b.adjust(*([1] * (shown + 1)))
    return b.as_markup()
