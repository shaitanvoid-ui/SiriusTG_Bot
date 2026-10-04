"""Gift cards, priced confirmation and the current user's durable requests."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.gifts import (
    kb_cancel_confirmation, kb_catalogue, kb_confirmation, kb_gift,
    kb_gift_error, kb_gift_history, kb_request,
)
from db.money import from_units, to_units
from locales.ru import T
from services.gifts import GiftService, GiftServiceError
from userbot.gifts import GiftAdapterError
from utils.telegram import ignore_unchanged
from utils.tz import fmt_dt
from utils.ui import clip, html_text
from utils.gift_labels import gift_label


router = Router(name="gifts")
CATALOGUE_PAGE_SIZE = 6


def internal_cost(units: int) -> str:
    """Show every stored fraction; never silently round a financial obligation."""
    text = f"{from_units(units):.4f}".rstrip("0").rstrip(".")
    return T.gift_internal_units.format(amount=text.replace(".", ","))


def status_text(status: str) -> str:
    return getattr(T, f"gift_status_{status}", T.gift_status_unknown)


def confirmation_text(kind: str | None) -> str:
    if kind in {"telegram", "telegram_confirmed", "payment_result", "telegram_operation"}:
        return T.gift_confirmation_telegram
    if kind in {"manual", "manual_success", "manual_confirmed"}:
        return T.gift_confirmation_manual
    return T.gift_confirmation_unverified


def _service(gift_service: GiftService | None) -> GiftService:
    return gift_service if gift_service is not None else GiftService()


def _id(value: str | None) -> int | None:
    try:
        result = int((value or "").rsplit(":", 1)[-1])
    except ValueError:
        return None
    return result if 0 < result < 2**63 else None


def _expiration(value: datetime | int | float) -> int:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp())
    return int(value)


async def _edit(callback: CallbackQuery, text: str, keyboard: Any) -> None:
    if callback.message is not None:
        with ignore_unchanged():
            await callback.message.edit_text(text, reply_markup=keyboard)


def error_text(code: str) -> str:
    """Only reviewed public explanations can cross the MTProto boundary."""
    known = {
        "restricted": T.gift_error_access,
        "gates": T.gift_error_gates,
        "minimum": T.gift_error_minimum,
        "referrals": T.gift_error_refs,
        "balance": T.gift_error_funds,
        "cannot_cancel": T.gift_error_cancel,
        "unsafe_retry": T.gift_error_retry,
        "owner_only": T.admin_gift_owner_only,
        "accounting_invariant": T.gift_error_accounting,
        "sender_unavailable": T.gift_error_account,
        "not_configured": T.gift_error_account,
        "no_session": T.gift_error_account,
        "not_authorized": T.gift_error_account,
        "account_mismatch": T.gift_error_account,
        "session_in_use": T.gift_error_account,
        "connection_failed": T.gift_error_account,
        "recipient_unresolved": T.gift_error_recipient,
        "recipient_mismatch": T.gift_error_recipient,
        "price_changed": T.gift_error_price,
        "gift_sold_out": T.gift_error_price,
        "gift_unavailable": T.gift_error_price,
        "gift_locked": T.gift_error_price,
        "gift_user_limit": T.gift_error_price,
        "gift_unsupported": T.gift_unsupported,
        "gift_auction_unsupported": T.gift_unsupported,
        "premium_required": T.gift_restricted,
        "insufficient_balance": T.gift_error_funds,
        "not_enough": T.gift_error_funds,
        "debt": T.gift_error_debt,
        "debt_outstanding": T.gift_error_debt,
        "minimum_balance": T.gift_error_minimum,
        "minimum_not_met": T.gift_error_minimum,
        "insufficient_refs": T.gift_error_refs,
        "referrals_required": T.gift_error_refs,
        "daily_limit": T.gift_error_limit,
        "limit_reached": T.gift_error_limit,
        "banned": T.gift_error_access,
        "shadow_banned": T.gift_error_access,
        "not_eligible": T.gift_error_access,
        "gates_required": T.gift_error_gates,
        "terms_required": T.gift_error_gates,
        "captcha_required": T.gift_error_gates,
        "subscription_required": T.gift_error_gates,
        "not_found": T.gift_error_not_found,
        "forbidden": T.gift_error_not_found,
        "cancel_not_allowed": T.gift_error_cancel,
        "invalid_state": T.gift_error_cancel,
        "retry_not_allowed": T.gift_error_retry,
        "evidence_required": T.gift_error_evidence,
        "confirmation_expired": T.gift_error_confirmation,
        "confirmation_invalid": T.gift_error_confirmation,
        "quote_expired": T.gift_error_confirmation,
        "quote_invalid": T.gift_error_confirmation,
        "payment_unknown": T.gift_reconciliation_detail,
    }
    return known.get(code, T.gift_error_unavailable)


async def _error(callback: CallbackQuery, error: GiftServiceError | GiftAdapterError, svc: GiftService) -> None:
    text = error_text(error.code)
    if error.code == "recipient_unresolved":
        try:
            account = await svc.account()
        except (GiftServiceError, GiftAdapterError):
            account = None
        if account is not None and account.available and account.username:
            text = T.gift_error_recipient_sender.format(sender=html_text(f"@{account.username}"))
    await _edit(callback, text, kb_gift_error())
    await callback.answer()


def availability_text(gift: Any) -> str:
    if gift.available and gift.kind == "ordinary":
        return T.gift_available
    if gift.reason == "gift_sold_out":
        return T.gift_sold_out
    if gift.kind != "ordinary" or gift.reason in {"gift_unsupported", "gift_auction_unsupported"}:
        return T.gift_unsupported
    if gift.reason in {"premium_required", "gift_locked", "gift_user_limit"}:
        return T.gift_restricted
    return T.gift_unavailable


def render_gift(gift: Any, *, conditions: dict[str, int] | None = None) -> str:
    rules = [T.gift_conditions]
    if conditions is not None:
        rules = [T.gift_admission_rules.format(
            minimum=internal_cost(conditions["minimum_units"]), refs=conditions["min_refs"],
            limit=conditions["daily_limit"] if conditions["daily_limit"] else T.gift_unlimited,
        )]
    if gift.requires_premium:
        rules.append(T.gift_premium_condition)
    if gift.limited and gift.availability_remains is not None:
        rules.append(T.gift_limited_condition.format(count=gift.availability_remains))
    return T.gift_card.format(
        title=html_text(clip(gift_label(gift.title), 120)), stars=gift.stars,
        cost=internal_cost(to_units(gift.stars)), availability=availability_text(gift),
        conditions="\n".join(rules),
    )


def render_request(request: Any, *, position: int = 0) -> str:
    status = request.status
    if status == "pending":
        detail = T.gift_queue_detail.format(position=position) if position > 0 else T.gift_status_pending
    else:
        detail = {
            "waiting_funds": T.gift_waiting_detail,
            "processing": T.gift_processing_detail,
            "succeeded": T.gift_succeeded_detail,
            "failed": T.gift_failed_detail,
            "cancelled": T.gift_cancelled_detail,
            "reconciliation_required": T.gift_reconciliation_detail,
        }.get(status, T.gift_status_unknown)
    if status == "waiting_funds":
        code = getattr(request, "error_code", None)
        if code == "budget":
            detail = T.gift_budget_detail
        elif code in {"sender_unavailable", "not_configured", "no_session", "not_authorized", "account_mismatch", "session_in_use", "connection_failed"}:
            detail = T.gift_error_account
    return T.gift_request.format(
        id=request.id, title=html_text(clip(gift_label(request.title), 120)), stars=request.stars,
        cost=internal_cost(request.cost_units), status=status_text(status),
        reserve=getattr(T, f"gift_reserve_{request.reserve_state}", T.gift_reserve_unknown),
        created=fmt_dt(request.created_at), detail=detail,
        confirmation=confirmation_text(request.confirmation_kind) if status == "succeeded" else "",
    )


async def _show_request(callback: CallbackQuery, svc: GiftService, request: Any) -> None:
    position = await svc.queue_position(request.id) if request.status == "pending" else 0
    await _edit(callback, render_request(request, position=position), kb_request(request))
    await callback.answer()


async def _catalogue(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                     gift_service: GiftService | None, *, page: int) -> None:
    await state.clear()
    # Upsert/gate middleware may hold SQLite's writer lock. Release it before
    # any service transaction or network call; the gift service uses its own DB.
    await session.commit()
    svc = _service(gift_service)
    try:
        catalogue = await svc.catalogue()
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error, svc)
        return
    pages = max(1, (len(catalogue) + CATALOGUE_PAGE_SIZE - 1) // CATALOGUE_PAGE_SIZE)
    page = min(max(page, 0), pages - 1)
    gifts = catalogue[page * CATALOGUE_PAGE_SIZE:(page + 1) * CATALOGUE_PAGE_SIZE]
    rows = T.gift_catalogue_summary.format(count=len(gifts)) if gifts else T.gift_catalogue_empty
    if pages > 1:
        rows += "\n\n" + T.gift_catalogue_page.format(page=page + 1, pages=pages)
    await _edit(callback, T.gift_catalogue.format(rows=rows), kb_catalogue(gifts, page=page, pages=pages))
    await callback.answer()


@router.callback_query(F.data == "gift:open")
async def cb_open(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                  gift_service: GiftService | None = None) -> None:
    await _catalogue(callback, session, state, gift_service, page=0)


@router.callback_query(F.data.startswith("gift:page:"))
async def cb_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                  gift_service: GiftService | None = None) -> None:
    try:
        page = int((callback.data or "").rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await _catalogue(callback, session, state, gift_service, page=page)


@router.callback_query(F.data.startswith("gift:view:"))
async def cb_view(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                  gift_service: GiftService | None = None) -> None:
    await state.clear()
    gift_id = _id(callback.data)
    if gift_id is None:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await session.commit()
    svc = _service(gift_service)
    try:
        gift = next((gift for gift in await svc.catalogue() if gift.id == gift_id), None)
        conditions = await svc.conditions() if gift is not None else None
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error, svc)
        return
    if gift is None:
        await callback.answer(T.gift_unavailable_alert, show_alert=True)
        return
    await _edit(callback, render_gift(gift, conditions=conditions), kb_gift(gift.id, available=gift.available and gift.kind == "ordinary"))
    await callback.answer()


@router.callback_query(F.data.startswith("gift:quote:"))
async def cb_quote(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                   gift_service: GiftService | None = None) -> None:
    await state.clear()
    gift_id = _id(callback.data)
    if gift_id is None or callback.message is None:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await session.commit()
    svc = _service(gift_service)
    try:
        quote = await svc.quote(callback.from_user.id, gift_id)
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error, svc)
        return
    await state.update_data(gift_quote_token=quote.id, gift_quote_expires_at=_expiration(quote.expires_at))
    await _edit(callback, T.gift_confirmation.format(
        title=html_text(clip(gift_label(quote.title), 120)), stars=quote.stars, cost=internal_cost(quote.cost_units),
    ), kb_confirmation(quote.id, cost=internal_cost(quote.cost_units)))
    await callback.answer()


@router.callback_query(F.data.startswith("gift:confirm:"))
async def cb_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                     gift_service: GiftService | None = None) -> None:
    data = await state.get_data()
    token = (callback.data or "").split(":", 2)[-1]
    expires = data.get("gift_quote_expires_at")
    if not token or token != data.get("gift_quote_token") or not isinstance(expires, (int, float)) or expires <= time.time():
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await state.clear()
    await session.commit()
    svc = _service(gift_service)
    try:
        # A durable quote is bound to this Telegram user in the service; FSM
        # cannot set a recipient, gift price or reservation amount.
        request = await svc.confirm(callback.from_user.id, token)
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error, svc)
        return
    await _show_request(callback, svc, request)


@router.callback_query(F.data == "gift:history")
async def cb_history(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                     gift_service: GiftService | None = None) -> None:
    await state.clear()
    await session.commit()
    svc = _service(gift_service)
    try:
        requests = await svc.history(callback.from_user.id, limit=10)
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error, svc)
        return
    rows = "\n\n".join(T.gift_history_row.format(
        id=request.id, title=html_text(clip(gift_label(request.title), 80)),
        status=status_text(request.status), cost=internal_cost(request.cost_units),
    ) for request in requests) or T.gift_history_empty
    await _edit(callback, T.gift_history.format(rows=rows), kb_gift_history(requests))
    await callback.answer()


@router.callback_query(F.data.startswith("gift:request:"))
async def cb_request(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                     gift_service: GiftService | None = None) -> None:
    await state.clear()
    request_id = _id(callback.data)
    if request_id is None:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await session.commit()
    svc = _service(gift_service)
    try:
        request = await svc.detail(callback.from_user.id, request_id)
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error, svc)
        return
    await _show_request(callback, svc, request)


@router.callback_query(F.data.startswith("gift:cancel:"))
async def cb_cancel(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                    gift_service: GiftService | None = None) -> None:
    await state.clear()
    request_id = _id(callback.data)
    if request_id is None:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await session.commit()
    svc = _service(gift_service)
    try:
        request = await svc.detail(callback.from_user.id, request_id)
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error, svc)
        return
    if request.status not in {"pending", "waiting_funds"} or request.reserve_state != "held":
        await callback.answer(T.gift_error_cancel, show_alert=True)
        return
    await state.update_data(gift_cancel_request_id=request_id)
    await _edit(callback, T.gift_cancel_prompt.format(id=request_id), kb_cancel_confirmation(request_id))
    await callback.answer()


@router.callback_query(F.data.startswith("gift:cancel_yes:"))
async def cb_cancel_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                            gift_service: GiftService | None = None) -> None:
    request_id = _id(callback.data)
    data = await state.get_data()
    if request_id is None or request_id != data.get("gift_cancel_request_id"):
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await state.clear()
    await session.commit()
    svc = _service(gift_service)
    try:
        request = await svc.cancel(callback.from_user.id, request_id)
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error, svc)
        return
    await _show_request(callback, svc, request)
