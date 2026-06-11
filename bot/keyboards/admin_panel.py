"""Клавиатуры новых админ-разделов Этапа 8/9: дашборд, юзеры, экономика,
рассылка, инструкция, канал, стоп-слова."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models import Instruction, User
from locales.ru import T


def _back_to_root_row(b: InlineKeyboardBuilder) -> None:
    b.button(text=T.btn_admin_back, callback_data="adm:root")


# ---------- дашборд / система ----------

def kb_dash(refresh_cb: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_admin_refresh, callback_data=refresh_cb)
    _back_to_root_row(b)
    b.adjust(2)
    return b.as_markup()


# ---------- юзеры ----------

def kb_user_search() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    _back_to_root_row(b)
    b.adjust(1)
    return b.as_markup()


def kb_user_card(user: User) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if user.is_banned:
        b.button(text=T.btn_admin_user_unban, callback_data=f"adm:usr:unban:{user.id}")
    else:
        b.button(text=T.btn_admin_user_ban, callback_data=f"adm:usr:ban:{user.id}")
    if user.is_shadow_banned:
        b.button(text=T.btn_admin_user_shadow_off, callback_data=f"adm:usr:shoff:{user.id}")
    else:
        b.button(text=T.btn_admin_user_shadow_on, callback_data=f"adm:usr:shon:{user.id}")
    b.button(text=T.btn_admin_user_balance, callback_data=f"adm:usr:bal:{user.id}")
    b.button(text=T.btn_admin_user_search, callback_data="adm:usr")
    _back_to_root_row(b)
    b.adjust(2, 2, 1)
    return b.as_markup()


# ---------- экономика ----------

def kb_eco_groups(groups: list[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for g in groups:
        b.button(text=f"⚙ {g}", callback_data=f"adm:eco:g:{g}")
    _back_to_root_row(b)
    b.adjust(*([2] * (len(groups) // 2)), *([1] * (len(groups) % 2)), 1)
    return b.as_markup()


def kb_eco_keys(group: str, keys: list[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for k in keys:
        b.button(text=k, callback_data=f"adm:eco:k:{k}")
    b.button(text="◀ К группам", callback_data="adm:eco")
    b.adjust(*([1] * len(keys)), 1)
    return b.as_markup()


def kb_eco_cancel(group: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✕ Отменить", callback_data=f"adm:eco:g:{group}")
        ]]
    )


# ---------- рассылка ----------

def kb_bc_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=T.btn_admin_bc_cancel, callback_data="adm:root")
        ]]
    )


def kb_bc_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=T.btn_admin_bc_send, callback_data="adm:bc:go"),
            InlineKeyboardButton(text=T.btn_admin_bc_cancel, callback_data="adm:root"),
        ]]
    )


# ---------- инструкция ----------

def kb_ins_list(pages: list[Instruction]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in pages:
        b.button(text=f"📄 {p.title}", callback_data=f"adm:ins:open:{p.id}")
    b.button(text=T.btn_admin_ins_add, callback_data="adm:ins:add")
    _back_to_root_row(b)
    b.adjust(*([1] * len(pages)), 2)
    return b.as_markup()


def kb_ins_card(page_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_admin_ins_edit_title, callback_data=f"adm:ins:et:{page_id}")
    b.button(text=T.btn_admin_ins_edit_body, callback_data=f"adm:ins:eb:{page_id}")
    b.button(text=T.btn_admin_ins_delete, callback_data=f"adm:ins:del:{page_id}")
    b.button(text="◀ К списку", callback_data="adm:ins:list")
    b.adjust(2, 2)
    return b.as_markup()


def kb_ins_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✕ Отменить", callback_data="adm:ins:list")
        ]]
    )


# ---------- канал ----------

def kb_channel() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    _back_to_root_row(b)
    b.adjust(1)
    return b.as_markup()


# ---------- стоп-слова ----------

def kb_stop_words() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_admin_sw_add, callback_data="adm:sw:add")
    b.button(text=T.btn_admin_sw_remove, callback_data="adm:sw:rm")
    _back_to_root_row(b)
    b.adjust(2, 1)
    return b.as_markup()


def kb_sw_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✕ Отменить", callback_data="adm:sw")
        ]]
    )


# ---------- партнёры (Этап 10) ----------

def kb_pa_root(rows: list[tuple[int, str]], pending: int) -> InlineKeyboardMarkup:
    """rows — (partner_id, готовый лейбл)."""
    b = InlineKeyboardBuilder()
    for partner_id, label in rows:
        b.button(text=label, callback_data=f"adm:pa:open:{partner_id}")
    b.button(text=T.btn_admin_pa_add, callback_data="adm:pa:add")
    b.button(text=T.btn_admin_pa_payouts.format(pending=pending), callback_data="adm:pa:pays")
    _back_to_root_row(b)
    b.adjust(*([1] * len(rows)), 2, 1)
    return b.as_markup()


def kb_pa_card(partner_id: int, is_active: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_active:
        b.button(text=T.btn_admin_pa_pause, callback_data=f"adm:pa:tgl:{partner_id}")
    else:
        b.button(text=T.btn_admin_pa_activate, callback_data=f"adm:pa:tgl:{partner_id}")
    b.button(text=T.btn_admin_pa_cpa, callback_data=f"adm:pa:cpa:{partner_id}")
    b.button(text=T.btn_admin_pa_percent, callback_data=f"adm:pa:pct:{partner_id}")
    b.button(text="◀ К списку", callback_data="adm:pa")
    b.adjust(1, 2, 1)
    return b.as_markup()


def kb_pa_payouts(rows: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """rows — (payout_id, готовый лейбл)."""
    b = InlineKeyboardBuilder()
    for payout_id, label in rows:
        b.button(text=label, callback_data=f"adm:pa:pay:{payout_id}")
    b.button(text="◀ К партнёрам", callback_data="adm:pa")
    b.adjust(*([1] * len(rows)), 1)
    return b.as_markup()


def kb_pa_payout_card(payout_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_admin_pa_paid, callback_data=f"adm:pa:paid:{payout_id}")
    b.button(text=T.btn_admin_pa_reject, callback_data=f"adm:pa:rej:{payout_id}")
    b.button(text="◀ К заявкам", callback_data="adm:pa:pays")
    b.adjust(2, 1)
    return b.as_markup()


def kb_pa_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✕ Отменить", callback_data="adm:pa")
        ]]
    )
