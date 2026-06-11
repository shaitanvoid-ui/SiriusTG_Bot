from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models import Promo
from locales.ru import T


def _row_text(p: Promo) -> str:
    status = "✅" if p.is_active else "⏸"
    badge = "🪤" if p.is_honeypot else "🎟"
    used = f"{p.used_count}"
    if p.max_activations > 0:
        used = f"{p.used_count}/{p.max_activations}"
    return f"{status}{badge}  {p.code}  ·  {used}"


def kb_promos_list(promos: list[Promo], *, limit: int = 25) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    shown = promos[:limit]
    for p in shown:
        b.button(text=_row_text(p), callback_data=f"adm:promo:open:{p.id}")
    b.button(text=T.btn_admin_promo_add, callback_data="adm:promo:add")
    b.button(text=T.btn_admin_back, callback_data="adm:root")
    b.adjust(*([1] * len(shown)), 2)
    return b.as_markup()


def kb_promo_card(p: Promo) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle = T.btn_admin_promo_pause if p.is_active else T.btn_admin_promo_resume
    b.button(text=toggle, callback_data=f"adm:promo:toggle:{p.id}")
    b.button(text=T.btn_admin_promo_delete, callback_data=f"adm:promo:del_ask:{p.id}")
    b.button(text=T.btn_admin_promo_back_list, callback_data="adm:promo:list")
    b.adjust(2, 1)
    return b.as_markup()


def kb_promo_delete_confirm(promo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=T.btn_admin_promo_delete_confirm,
                callback_data=f"adm:promo:del_yes:{promo_id}",
            ),
            InlineKeyboardButton(
                text=T.btn_admin_promo_delete_cancel,
                callback_data=f"adm:promo:open:{promo_id}",
            ),
        ]]
    )


def kb_promo_add_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=T.btn_admin_promo_add_cancel, callback_data="adm:promo:add_cancel"),
        ]]
    )


def kb_promo_add_honeypot() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=T.btn_admin_promo_honeypot_no, callback_data="adm:promo:hp:no"),
                InlineKeyboardButton(text=T.btn_admin_promo_honeypot_yes, callback_data="adm:promo:hp:yes"),
            ],
            [InlineKeyboardButton(text=T.btn_admin_promo_add_cancel, callback_data="adm:promo:add_cancel")],
        ]
    )
