"""Owner-only antifraud explanations, evidence and reviewed reset decisions."""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.antifraud import (
    kb_antifraud_cancel, kb_antifraud_confirm, kb_antifraud_create, kb_antifraud_queue, kb_antifraud_user,
)
from core.config import settings
from locales.ru import T
from services.antifraud import AntifraudService
from services.settings import SettingsService
from utils.telegram import ignore_unchanged
from utils.ui import html_text, clip
from utils.tz import fmt_dt


router = Router(name="admin_antifraud")
router.message.filter(IsAdmin(owner_only=True))
router.callback_query.filter(IsAdmin(owner_only=True))


class AntifraudStates(StatesGroup):
    reason = State()
    reset_confirm = State()
    create_confirm = State()


async def _owner(event) -> bool:
    if event.from_user is not None and event.from_user.id == settings.owner_id:
        return True
    await event.answer(T.antifraud_owner_only, **({"show_alert": True} if isinstance(event, CallbackQuery) else {}))
    return False


def _target(data: str | None) -> int | None:
    raw = (data or "").rsplit(":", 1)[-1]
    return int(raw) if raw.isdecimal() and 0 < int(raw) <= 2**63 - 1 else None


async def _edit(callback, text, markup):
    if callback.message is not None:
        with ignore_unchanged():
            await callback.message.edit_text(text, reply_markup=markup)


def _signal(name: str) -> str:
    return getattr(T, f"antifraud_signal_{name}", html_text(name))


async def _queue(callback, session, page=0):
    svc = AntifraudService(session)
    rows, has_more = await svc.review_queue(actor_tg_id=callback.from_user.id, page=page)
    policy = await SettingsService(session).get_many({"antifraud.shadow_threshold": 70, "antifraud.auto_shadow": True,
        "antifraud.actions_per_minute": 20, "antifraud.window_seconds": 60})
    await _edit(callback, T.antifraud_root.format(
        threshold=policy["antifraud.shadow_threshold"], auto=T.antifraud_on if policy["antifraud.auto_shadow"] else T.antifraud_off,
        limit=policy["antifraud.actions_per_minute"], window=policy["antifraud.window_seconds"],
        rows=T.antifraud_queue_count.format(count=len(rows)) if rows else T.antifraud_empty,
    ), kb_antifraud_queue(rows, page=page, has_more=has_more))


async def _detail(callback, session, user_id):
    try:
        user, snapshot, events = await AntifraudService(session).review_detail(actor_tg_id=callback.from_user.id, user_id=user_id)
    except ValueError:
        await callback.answer(T.admin_user_not_found, show_alert=True)
        return False
    reasons = "\n".join(T.antifraud_reason_row.format(name=_signal(name), weight=weight)
        for name, weight in json.loads(snapshot.reasons_json)) if snapshot else ""
    audit = []
    for event in events:
        details = json.loads(event.details_json)
        detail = html_text(clip(str(details.get("reason", details.get("source_id", ""))), 180))
        audit.append(T.antifraud_event_row.format(name=_signal(event.kind), when=fmt_dt(event.created_at),
            actor=event.actor_tg_id or "—", detail=detail))
    await _edit(callback, T.antifraud_card.format(
        tg_id=user.tg_id, score=snapshot.score if snapshot else 0,
        status=T.antifraud_restricted if user.is_shadow_banned else T.antifraud_observation,
        reasons=reasons or T.antifraud_no_signals, events="\n".join(audit) or T.antifraud_no_events,
    ), kb_antifraud_user(user.id, shadow=user.is_shadow_banned))
    return True


@router.callback_query(F.data == "adm:af:open")
@router.callback_query(F.data.startswith("adm:af:list:"))
async def cb_open(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not await _owner(callback):
        return
    await state.clear()
    page = (_target(callback.data) or 0) if callback.data != "adm:af:open" else 0
    await session.commit()
    await _queue(callback, session, min(page, 1000000))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:af:user:"))
async def cb_user(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not await _owner(callback):
        return
    await state.clear()
    user_id = _target(callback.data)
    if user_id is None:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await session.commit()
    if await _detail(callback, session, user_id):
        await callback.answer()


async def begin_reset(callback: CallbackQuery, state: FSMContext, user_id: int):
    await state.set_state(AntifraudStates.reason)
    await state.update_data(antifraud_user_id=user_id, antifraud_owner=callback.from_user.id)
    await _edit(callback, T.antifraud_reset_reason, kb_antifraud_cancel(user_id))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:af:reset:"))
async def cb_reset(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not await _owner(callback):
        return
    user_id = _target(callback.data)
    if user_id is None:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    try:
        await AntifraudService(session).review_detail(actor_tg_id=callback.from_user.id, user_id=user_id)
    except ValueError:
        await callback.answer(T.admin_user_not_found, show_alert=True)
        return
    await begin_reset(callback, state, user_id)


@router.message(AntifraudStates.reason, F.text)
async def msg_reason(message: Message, state: FSMContext):
    if not await _owner(message):
        return
    reason = (message.text or "").strip()
    if not 8 <= len(reason) <= 500:
        await message.answer(T.antifraud_reason_invalid)
        return
    data = await state.get_data()
    if data.get("antifraud_owner") != message.from_user.id or not data.get("antifraud_user_id"):
        await state.clear()
        await message.answer(T.stale_screen_alert)
        return
    token = secrets.token_hex(16)
    await state.update_data(antifraud_reason=reason, antifraud_token=token, antifraud_expiry=datetime.now(timezone.utc).timestamp() + 120)
    await state.set_state(AntifraudStates.reset_confirm)
    await message.answer(T.antifraud_reset_preview.format(reason=html_text(reason)),
        reply_markup=kb_antifraud_confirm(data["antifraud_user_id"], token))


def _valid_confirmation(data, callback) -> bool:
    token = (callback.data or "").rsplit(":", 1)[-1]
    return data.get("antifraud_owner") == callback.from_user.id and secrets.compare_digest(token, data.get("antifraud_token", "")) and data.get("antifraud_expiry", 0) > datetime.now(timezone.utc).timestamp()


@router.callback_query(F.data.startswith("adm:af:confirm:"), AntifraudStates.reset_confirm)
async def cb_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not await _owner(callback):
        return
    data = await state.get_data()
    if not _valid_confirmation(data, callback):
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    await AntifraudService(session).reset(user_id=data["antifraud_user_id"], actor_tg_id=callback.from_user.id,
        reason=data["antifraud_reason"], decision_token=data["antifraud_token"])
    await session.commit()
    await state.clear()
    await _detail(callback, session, data["antifraud_user_id"])
    await callback.answer(T.antifraud_reset_saved)


@router.callback_query(F.data == "adm:af:create")
async def cb_create(callback: CallbackQuery, state: FSMContext):
    if not await _owner(callback):
        return
    token = secrets.token_hex(16)
    await state.set_state(AntifraudStates.create_confirm)
    await state.update_data(antifraud_owner=callback.from_user.id, antifraud_token=token,
        antifraud_expiry=datetime.now(timezone.utc).timestamp() + 120)
    await _edit(callback, T.antifraud_create_preview, kb_antifraud_create(token))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:af:create_yes:"), AntifraudStates.create_confirm)
async def cb_create_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not await _owner(callback):
        return
    data = await state.get_data()
    if not _valid_confirmation(data, callback):
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    sponsor = await AntifraudService(session).create_hidden_task(actor_tg_id=callback.from_user.id, decision_token=data["antifraud_token"])
    await session.commit()
    await state.clear()
    await _queue(callback, session)
    await callback.answer(T.antifraud_task_created.format(id=sponsor.id))


@router.callback_query(F.data.startswith("adm:af:confirm:"))
@router.callback_query(F.data.startswith("adm:af:create_yes:"))
async def cb_stale(callback: CallbackQuery):
    await callback.answer(T.stale_screen_alert, show_alert=True)
