"""Owner-only gift queue and evidence-backed, explicitly confirmed decisions."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.handlers.gifts import (
    _edit, _id, _service, confirmation_text, error_text, internal_cost, render_request, status_text,
)
from bot.keyboards.gifts import (
    kb_admin_cancel, kb_admin_decision, kb_admin_gifts, kb_admin_list,
    kb_admin_request,
)
from core.config import settings
from locales.ru import T
from services.gifts import GiftService, GiftServiceError
from userbot.gifts import GiftAdapterError
from utils.ui import clip, html_text


router = Router(name="admin_gifts")
router.message.filter(IsAdmin(owner_only=True))
router.callback_query.filter(IsAdmin(owner_only=True))


class GiftDecisionStates(StatesGroup):
    evidence = State()


_ACTIONS = {"retry", "manual_success", "proven_failure"}
_SECTIONS = {
    "queue": T.btn_admin_gift_queue,
    "waiting_funds": T.btn_admin_gift_waiting,
    "reconciliation_required": T.btn_admin_gift_reconciliation,
    "history": T.btn_admin_gift_history,
}


async def _owner(event: CallbackQuery | Message) -> bool:
    """Keep direct handler calls as strict as the router's owner-only filter."""
    if event.from_user is not None and event.from_user.id == settings.owner_id:
        return True
    if isinstance(event, CallbackQuery):
        await event.answer(T.admin_gift_owner_only, show_alert=True)
    else:
        await event.answer(T.admin_gift_owner_only)
    return False


def _action_name(action: str) -> str:
    return getattr(T, f"admin_gift_action_{action}", T.gift_status_unknown)


async def _error(callback: CallbackQuery, error: GiftServiceError) -> None:
    await _edit(callback, error_text(error.code), kb_admin_gifts())
    await callback.answer()


async def _show_detail(callback: CallbackQuery, svc: GiftService, request_id: int) -> None:
    details = await svc.admin_detail(callback.from_user.id, request_id)
    request = details["request"]
    if request is None:
        raise GiftServiceError("not_found")
    position = await svc.queue_position(request.id) if request.status == "pending" else 0
    # This view is deliberately restricted to reviewed identifiers/states.
    # Raw exception messages, RPC responses and account/session data never render.
    attempts = "; ".join(T.admin_gift_attempt.format(
        id=attempt.id, state=html_text(clip(str(getattr(attempt, "outcome", None) or getattr(attempt, "phase", "—")), 80)),
    ) for attempt in details.get("attempts", [])[-8:]) or "—"
    audit_rows = "; ".join(
        f"{_action_name(entry.action)} · {entry.actor_tg_id}"
        for entry in details.get("audit", [])[-5:] if entry.used_at is not None
    )
    audit = T.admin_gift_audit.format(rows=html_text(audit_rows)) if audit_rows else T.admin_gift_audit_empty
    operations = T.admin_gift_operations.format(kind=confirmation_text(request.confirmation_kind))
    if request.proof:
        if request.confirmation_kind == "telegram":
            try:
                proof = json.loads(request.proof)
            except (ValueError, TypeError):
                proof = {}
            if isinstance(proof, dict):
                references = [str(proof[key]) for key in ("form_id", "message_ids") if key in proof]
                if references:
                    operations += "\n" + T.admin_gift_proof.format(reference=html_text(clip(" · ".join(references), 300)))
        elif request.confirmation_kind in {"manual", "manual_failure"}:
            operations += "\n" + T.admin_gift_evidence.format(evidence=html_text(clip(request.proof, 800)))
    journal = "\n".join(T.admin_gift_money_row.format(
        id=operation.id,
        reason={"gift_reserve": T.admin_gift_money_reserve, "gift_release": T.admin_gift_money_release, "gift_consume": T.admin_gift_money_consume}.get(operation.reason, T.gift_status_unknown),
        balance=internal_cost(operation.balance_delta_units), reserve=internal_cost(operation.reserved_delta_units),
    ) for operation in details.get("operations", [])[-5:])
    if journal:
        operations += "\n" + T.admin_gift_money_journal.format(rows=journal)
    await _edit(callback, T.admin_gift_detail.format(
        card=render_request(request, position=position), recipient=request.recipient_tg_id,
        attempts=attempts, operations=operations, audit=audit,
    ), kb_admin_request(request))


@router.callback_query(F.data == "adm:gift:open")
async def cb_open(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _owner(callback):
        return
    await state.clear()
    await _edit(callback, T.admin_gift_root, kb_admin_gifts())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:gift:list:"))
async def cb_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                  gift_service: GiftService | None = None) -> None:
    if not await _owner(callback):
        return
    await state.clear()
    section = (callback.data or "").rsplit(":", 1)[-1]
    if section not in _SECTIONS:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await session.commit()
    svc = _service(gift_service)
    try:
        if section == "queue":
            pending, processing = await asyncio.gather(
                svc.admin_list(status="pending", limit=15), svc.admin_list(status="processing", limit=15),
            )
            requests = sorted(pending + processing, key=lambda request: request.created_at)[:15]
        else:
            requests = await svc.admin_list(status=None if section == "history" else section, limit=15)
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error)
        return
    rows = "\n\n".join(T.admin_gift_row.format(
        id=request.id, title=html_text(clip(request.title, 80)),
        status=status_text(request.status), recipient=request.recipient_tg_id,
    ) for request in requests) or T.admin_gift_empty
    await _edit(callback, T.admin_gift_list.format(title=_SECTIONS[section], rows=rows), kb_admin_list(requests, section=section))
    await callback.answer()


@router.callback_query(F.data == "adm:gift:account")
async def cb_account(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                     gift_service: GiftService | None = None) -> None:
    if not await _owner(callback):
        return
    await state.clear()
    await session.commit()
    svc = _service(gift_service)
    try:
        account, budget = await asyncio.gather(svc.account(), svc.budget())
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error)
        return
    await _edit(callback, T.admin_gift_account.format(
        status=T.admin_gift_account_ready if account.available else T.admin_gift_account_offline,
        stars=account.stars if account.stars is not None else "—",
        spent=budget["daily_stars"], limit=budget["limit_stars"],
        detail=T.admin_gift_account_ready_detail if account.available else T.admin_gift_account_offline_detail,
    ), kb_admin_gifts())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:gift:request:"))
async def cb_request(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                     gift_service: GiftService | None = None) -> None:
    if not await _owner(callback):
        return
    await state.clear()
    request_id = _id(callback.data)
    if request_id is None:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await session.commit()
    svc = _service(gift_service)
    try:
        await _show_detail(callback, svc, request_id)
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error)
        return
    await callback.answer()


async def _confirmation(state: FSMContext, svc: GiftService, *, owner_id: int,
                        request_id: int, action: str, evidence: str) -> tuple[str, Any]:
    token = await svc.admin_confirmation(owner_id, request_id, action)
    await state.set_state(None)
    await state.update_data(
        gift_admin_request_id=request_id, gift_admin_action=action,
        gift_admin_evidence=evidence, gift_admin_token=token,
    )
    return T.admin_gift_decision_prompt.format(
        id=request_id, action=_action_name(action), evidence=html_text(evidence),
    ), kb_admin_decision(request_id, token)


@router.callback_query(F.data.startswith("adm:gift:action:"))
async def cb_action(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                    gift_service: GiftService | None = None) -> None:
    if not await _owner(callback):
        return
    await state.clear()
    parts = (callback.data or "").split(":")
    request_id = _id(parts[-2]) if len(parts) == 5 else None
    action = parts[-1]
    if request_id is None or action not in _ACTIONS:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await session.commit()
    svc = _service(gift_service)
    try:
        details = await svc.admin_detail(callback.from_user.id, request_id)
        request = details["request"]
        if request is None:
            raise GiftServiceError("not_found")
        if request.reserve_state != "held" or (
            action == "retry" and request.status != "waiting_funds"
        ) or (action != "retry" and request.status != "reconciliation_required"):
            await callback.answer(T.gift_error_retry, show_alert=True)
            return
        if action == "retry":
            text, keyboard = await _confirmation(
                state, svc, owner_id=callback.from_user.id, request_id=request_id,
                action=action, evidence=T.admin_gift_retry_evidence,
            )
        else:
            await state.set_state(GiftDecisionStates.evidence)
            await state.update_data(gift_admin_request_id=request_id, gift_admin_action=action)
            text = T.admin_gift_evidence_prompt.format(id=request_id, action=_action_name(action))
            keyboard = kb_admin_cancel(request_id)
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error)
        return
    await _edit(callback, text, keyboard)
    await callback.answer()


@router.message(GiftDecisionStates.evidence, F.text)
async def msg_evidence(message: Message, session: AsyncSession, state: FSMContext,
                       gift_service: GiftService | None = None) -> None:
    if not await _owner(message):
        return
    data = await state.get_data()
    request_id, action = data.get("gift_admin_request_id"), data.get("gift_admin_action")
    if not isinstance(request_id, int) or action not in {"manual_success", "proven_failure"}:
        await state.clear()
        await message.answer(T.stale_screen_alert, reply_markup=kb_admin_gifts())
        return
    evidence = (message.text or "").strip()
    if not 12 <= len(evidence) <= 1000:
        await message.answer(T.admin_gift_evidence_invalid, reply_markup=kb_admin_cancel(request_id))
        return
    await session.commit()
    svc = _service(gift_service)
    try:
        text, keyboard = await _confirmation(
            state, svc, owner_id=message.from_user.id, request_id=request_id,
            action=action, evidence=evidence,
        )
    except (GiftServiceError, GiftAdapterError) as error:
        await state.clear()
        await message.answer(error_text(error.code), reply_markup=kb_admin_gifts())
        return
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("adm:gift:decide:"))
async def cb_decide(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                    gift_service: GiftService | None = None) -> None:
    if not await _owner(callback):
        return
    data = await state.get_data()
    token = (callback.data or "").rsplit(":", 1)[-1]
    request_id, action = data.get("gift_admin_request_id"), data.get("gift_admin_action")
    evidence = data.get("gift_admin_evidence")
    if token != data.get("gift_admin_token") or not isinstance(request_id, int) or action not in _ACTIONS or not isinstance(evidence, str):
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await state.clear()
    await session.commit()
    svc = _service(gift_service)
    try:
        await svc.admin_decide(callback.from_user.id, request_id, action, token, evidence)
        await _show_detail(callback, svc, request_id)
    except (GiftServiceError, GiftAdapterError) as error:
        await _error(callback, error)
        return
    await callback.answer(T.admin_gift_decision_saved)
