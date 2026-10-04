"""Native gift navigation; callbacks contain identifiers, never recipient data."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from aiogram.types import DisabledButton, InlineKeyboardMarkup

from locales.ru import T
from utils.keyboards import SiriusKeyboardBuilder
from utils.ui import button_text
from utils.gift_labels import gift_label


def kb_catalogue(gifts: Sequence[Any], *, page: int = 0, pages: int = 1) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    for gift in gifts:
        title = button_text(gift_label(gift.title), limit=28)
        b.button(text=f"{title} · {gift.stars} ед.", callback_data=f"gift:view:{gift.id}")
    pagination = 0
    if page > 0:
        b.button(text=T.btn_gift_page_back, callback_data=f"gift:page:{page - 1}")
        pagination += 1
    if page + 1 < pages:
        b.button(text=T.btn_gift_page_next, callback_data=f"gift:page:{page + 1}")
        pagination += 1
    b.button(text=T.btn_gift_history, callback_data="gift:history")
    b.button(text=T.btn_gift_refresh, callback_data="gift:open")
    b.footer(text=T.btn_back_menu, callback_data="nav:menu")
    b.adjust(*([1] * len(gifts)), *([pagination] if pagination else []), 2, 1)
    return b.as_markup()


def kb_gift(gift_id: int, *, available: bool) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    if available:
        b.button(text=T.btn_gift_quote, callback_data=f"gift:quote:{gift_id}", style="primary")
    else:
        b.button(text=T.gift_unavailable, disabled=DisabledButton())
    b.button(text=T.btn_gift_history, callback_data="gift:history")
    b.footer(text=T.btn_gift_catalogue, callback_data="gift:open")
    b.adjust(1, 1, 2)
    return b.as_markup()


def kb_confirmation(token: str, *, cost: str) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_gift_confirm.format(cost=cost), callback_data=f"gift:confirm:{token}", style="primary")
    b.button(text=T.btn_cancel, callback_data="gift:open")
    b.adjust(1, 1)
    return b.as_markup()


def kb_gift_history(requests: Sequence[Any]) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    for request in requests:
        title = button_text(gift_label(request.title), limit=28)
        b.button(text=f"{title} · #{request.id}", callback_data=f"gift:request:{request.id}")
    b.button(text=T.btn_gift_refresh, callback_data="gift:history")
    b.footer(text=T.btn_gift_catalogue, callback_data="gift:open")
    b.adjust(*([1] * len(requests)), 1, 2)
    return b.as_markup()


def kb_request(request: Any) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_gift_refresh, callback_data=f"gift:request:{request.id}")
    if request.status in {"pending", "waiting_funds"} and request.reserve_state == "held":
        b.button(text=T.btn_gift_cancel, callback_data=f"gift:cancel:{request.id}")
    b.button(text=T.btn_gift_catalogue, callback_data="gift:open")
    b.footer(text=T.btn_gift_history, callback_data="gift:history")
    b.adjust(*([1] * (2 if request.status in {"pending", "waiting_funds"} and request.reserve_state == "held" else 1)), 1, 2)
    return b.as_markup()


def kb_cancel_confirmation(request_id: int) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_gift_cancel_confirm, callback_data=f"gift:cancel_yes:{request_id}", style="danger")
    b.button(text=T.btn_back, callback_data=f"gift:request:{request_id}")
    b.adjust(1, 1)
    return b.as_markup()


def kb_gift_error() -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_gift_refresh, callback_data="gift:open")
    b.button(text=T.btn_gift_history, callback_data="gift:history")
    b.button(text=T.btn_menu_help, callback_data="sup:open")
    b.footer(text=T.btn_back_menu, callback_data="nav:menu")
    b.adjust(2, 1, 1)
    return b.as_markup()


def kb_gift_notification(request_id: int) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_gift_open_request, callback_data=f"gift:request:{request_id}", style="primary")
    return b.as_markup()


def kb_admin_gifts() -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_admin_gift_queue, callback_data="adm:gift:list:queue")
    b.button(text=T.btn_admin_gift_waiting, callback_data="adm:gift:list:waiting_funds")
    b.button(text=T.btn_admin_gift_reconciliation, callback_data="adm:gift:list:reconciliation_required")
    b.button(text=T.btn_admin_gift_history, callback_data="adm:gift:list:history")
    b.button(text=T.btn_admin_gift_account, callback_data="adm:gift:account")
    b.footer(text=T.btn_back_admin, callback_data="adm:root")
    b.adjust(2, 2, 1, 1)
    return b.as_markup()


def kb_admin_list(requests: Sequence[Any], *, section: str) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    for request in requests:
        b.button(text=f"#{request.id} · {request.title}", callback_data=f"adm:gift:request:{request.id}")
    b.button(text=T.btn_gift_refresh, callback_data=f"adm:gift:list:{section}")
    b.footer(text=T.btn_admin_gift_back, callback_data="adm:gift:open")
    b.adjust(*([1] * len(requests)), 1, 2)
    return b.as_markup()


def kb_admin_request(request: Any) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_gift_refresh, callback_data=f"adm:gift:request:{request.id}")
    if request.status == "waiting_funds" and request.reserve_state == "held":
        b.button(text=T.btn_admin_gift_retry, callback_data=f"adm:gift:action:{request.id}:retry")
    if request.status == "reconciliation_required" and request.reserve_state == "held":
        b.button(text=T.btn_admin_gift_success, callback_data=f"adm:gift:action:{request.id}:manual_success")
        b.button(text=T.btn_admin_gift_failure, callback_data=f"adm:gift:action:{request.id}:proven_failure")
    b.footer(text=T.btn_admin_gift_back, callback_data="adm:gift:open")
    b.adjust(1)
    return b.as_markup()


def kb_admin_cancel(request_id: int) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_cancel, callback_data=f"adm:gift:request:{request_id}")
    b.adjust(1)
    return b.as_markup()


def kb_admin_decision(request_id: int, token: str) -> InlineKeyboardMarkup:
    b = SiriusKeyboardBuilder()
    b.button(text=T.btn_admin_gift_decide, callback_data=f"adm:gift:decide:{token}", style="danger")
    b.button(text=T.btn_cancel, callback_data=f"adm:gift:request:{request_id}")
    b.adjust(1, 1)
    return b.as_markup()
