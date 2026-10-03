"""Owner-only review and explicit risk decisions using native Telegram controls."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from locales.ru import T
from utils.keyboards import SiriusKeyboardBuilder


def kb_antifraud_queue(rows, *, page: int = 0, has_more: bool = False) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    for user, snapshot in rows:
        score = snapshot.score if snapshot else 0
        b.button(text=T.btn_antifraud_user.format(tg_id=user.tg_id, score=score), callback_data=f"adm:af:user:{user.id}")
    pages = 0
    if page:
        b.button(text=T.btn_history_prev, callback_data=f"adm:af:list:{page - 1}")
        pages += 1
    if has_more:
        b.button(text=T.btn_history_next, callback_data=f"adm:af:list:{page + 1}")
        pages += 1
    b.button(text=T.btn_refresh, callback_data=f"adm:af:list:{page}")
    b.button(text=T.btn_antifraud_new_task, callback_data="adm:af:create")
    b.footer(text=T.btn_back_admin, callback_data="adm:root")
    b.adjust(*([1] * len(rows)), *([pages] if pages else []), 2, 1)
    return b.as_markup()


def kb_antifraud_user(user_id: int, *, shadow: bool) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    if shadow:
        b.button(text=T.btn_antifraud_reset, callback_data=f"adm:af:reset:{user_id}", style="primary")
    b.button(text=T.btn_refresh, callback_data=f"adm:af:user:{user_id}")
    b.footer(text=T.btn_antifraud_back, callback_data="adm:af:open")
    b.adjust(*([1] if shadow else []), 1, 2)
    return b.as_markup()


def kb_antifraud_cancel(user_id: int) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_cancel, callback_data=f"adm:af:user:{user_id}")
    return b.as_markup()


def kb_antifraud_confirm(user_id: int, token: str) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_antifraud_reset_confirm, callback_data=f"adm:af:confirm:{token}", style="primary")
    b.button(text=T.btn_cancel, callback_data=f"adm:af:user:{user_id}")
    b.adjust(1, 1)
    return b.as_markup()


def kb_antifraud_create(token: str) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_antifraud_create_confirm, callback_data=f"adm:af:create_yes:{token}", style="primary")
    b.button(text=T.btn_cancel, callback_data="adm:af:open")
    b.adjust(1, 1)
    return b.as_markup()
