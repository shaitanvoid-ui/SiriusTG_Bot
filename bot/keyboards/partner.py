"""Клавиатуры партнёрской панели (Этап 10)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models import PartnerLink
from locales.ru import T


def kb_partner_root() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_partner_links, callback_data="pa:links")
    b.button(text=T.btn_partner_sponsors, callback_data="pa:sp")
    b.button(text=T.btn_partner_payout, callback_data="pa:pay")
    b.button(text=T.btn_partner_history, callback_data="pa:hist")
    b.button(text="◀ В профиль", callback_data="prof:open")
    b.adjust(2, 2, 1)
    return b.as_markup()


def kb_partner_links(links: list[PartnerLink]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for link in links:
        b.button(text=f"🔗 {link.title}", callback_data=f"pa:lnk:{link.id}")
    b.button(text=T.btn_partner_link_add, callback_data="pa:lnk:add")
    b.button(text=T.btn_partner_back, callback_data="pa:open")
    b.adjust(*([1] * len(links)), 1, 1)
    return b.as_markup()


def kb_partner_link_card(link_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_partner_link_del, callback_data=f"pa:lnk:del:{link_id}")
    b.button(text="◀ К ссылкам", callback_data="pa:links")
    b.adjust(1, 1)
    return b.as_markup()


def kb_partner_sponsors() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_partner_sponsor_add, callback_data="pa:sp:add")
    b.button(text=T.btn_partner_back, callback_data="pa:open")
    b.adjust(1, 1)
    return b.as_markup()


def kb_partner_payout_method() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_payout_card, callback_data="pa:pay:m:card")
    b.button(text=T.btn_payout_yoomoney, callback_data="pa:pay:m:yoomoney")
    b.button(text=T.btn_partner_back, callback_data="pa:open")
    b.adjust(2, 1)
    return b.as_markup()


def kb_partner_cancel() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✕ Отменить", callback_data="pa:open")
    b.adjust(1)
    return b.as_markup()


def kb_partner_back() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_partner_back, callback_data="pa:open")
    b.adjust(1)
    return b.as_markup()
