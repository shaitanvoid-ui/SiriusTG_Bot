"""Админ-CRUD промокодов."""

from __future__ import annotations

import math
import re
from contextlib import suppress
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.admin_promos import (
    kb_promo_add_cancel,
    kb_promo_add_honeypot,
    kb_promo_card,
    kb_promo_delete_confirm,
    kb_promos_list,
)
from bot.states.admin import AddPromoStates
from db.models import Promo
from db.repositories.promo import PromoRepo
from locales.ru import T
from services.promo import normalize_code
from utils.tz import FMT_DATE_TIME, fmt_dt
from utils.ui import stars


router = Router(name="admin_promos")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


CODE_RE = re.compile(r"^[A-Z0-9_\-]{1,64}$")


# ---------- list ----------

async def _render_list(callback: CallbackQuery, session: AsyncSession) -> None:
    repo = PromoRepo(session)
    promos = await repo.list_all(limit=25)
    total = await repo.count_all()
    active = sum(1 for p in promos if p.is_active)
    honeypots = sum(1 for p in promos if p.is_honeypot)
    if total == 0:
        head = T.admin_promos_empty
    else:
        head = T.admin_promos_count.format(total=total, active=active, honeypots=honeypots)
    text = T.admin_promos_root.format(count_line=head)
    if callback.message is not None:
        with suppress(TelegramAPIError):
            await callback.message.edit_text(text, reply_markup=kb_promos_list(promos))


@router.callback_query(F.data == "adm:promo:list")
async def cb_list(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await _render_list(callback, session)
    await callback.answer()


# ---------- card ----------

def _format_card(p: Promo) -> str:
    if p.expires_at is None:
        expires = T.admin_promo_expires_never
    else:
        expires = fmt_dt(p.expires_at, FMT_DATE_TIME) + " МСК"
    if p.max_activations == 0:
        usage = T.admin_promo_usage_unlimited.format(used=p.used_count)
    else:
        usage = T.admin_promo_usage_limited.format(used=p.used_count, max=p.max_activations)
    status = T.admin_promo_status_active if p.is_active else T.admin_promo_status_paused
    badge = T.admin_promo_kind_honeypot if p.is_honeypot else T.admin_promo_kind_normal
    return T.admin_promo_card.format(
        code=p.code,
        kind=badge,
        status=status,
        reward=stars(p.reward),
        usage=usage,
        expires=expires,
    )


async def _render_card(callback: CallbackQuery, p: Promo) -> None:
    if callback.message is not None:
        with suppress(TelegramAPIError):
            await callback.message.edit_text(_format_card(p), reply_markup=kb_promo_card(p))


@router.callback_query(F.data.startswith("adm:promo:open:"))
async def cb_open(callback: CallbackQuery, session: AsyncSession) -> None:
    pid = _parse_id(callback.data)
    if pid is None:
        await callback.answer()
        return
    p = await PromoRepo(session).get(pid)
    if p is None:
        await callback.answer(T.admin_promo_deleted, show_alert=True)
        await _render_list(callback, session)
        return
    await _render_card(callback, p)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:promo:toggle:"))
async def cb_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    pid = _parse_id(callback.data)
    if pid is None:
        await callback.answer()
        return
    repo = PromoRepo(session)
    p = await repo.get(pid)
    if p is None:
        await callback.answer(T.admin_promo_deleted, show_alert=True)
        return
    await repo.set_active(pid, not p.is_active)
    p = await repo.get(pid)
    if p is None:
        await _render_list(callback, session)
        await callback.answer()
        return
    await callback.answer(
        T.admin_promo_toggled_on if p.is_active else T.admin_promo_toggled_off
    )
    await _render_card(callback, p)


@router.callback_query(F.data.startswith("adm:promo:del_ask:"))
async def cb_delete_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    pid = _parse_id(callback.data)
    if pid is None:
        await callback.answer()
        return
    p = await PromoRepo(session).get(pid)
    if p is None:
        await callback.answer(T.admin_promo_deleted, show_alert=True)
        return
    if callback.message is not None:
        with suppress(TelegramAPIError):
            await callback.message.edit_text(
                _format_card(p) + "\n\n<b>Удалить этот промокод?</b>",
                reply_markup=kb_promo_delete_confirm(pid),
            )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:promo:del_yes:"))
async def cb_delete_yes(callback: CallbackQuery, session: AsyncSession) -> None:
    pid = _parse_id(callback.data)
    if pid is None:
        await callback.answer()
        return
    await PromoRepo(session).delete(pid)
    await callback.answer(T.admin_promo_deleted)
    await _render_list(callback, session)


# ---------- add wizard ----------

@router.callback_query(F.data == "adm:promo:add")
async def cb_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddPromoStates.waiting_code)
    if callback.message is not None:
        with suppress(TelegramAPIError):
            await callback.message.edit_text(T.addpromo_step1, reply_markup=kb_promo_add_cancel())
    await callback.answer()


@router.callback_query(F.data == "adm:promo:add_cancel")
async def cb_add_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await callback.answer(T.addpromo_cancelled)
    await _render_list(callback, session)


@router.message(AddPromoStates.waiting_code)
async def msg_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.text is None:
        await message.answer(T.addpromo_code_invalid, reply_markup=kb_promo_add_cancel())
        return
    code = normalize_code(message.text)
    if not CODE_RE.match(code):
        await message.answer(T.addpromo_code_invalid, reply_markup=kb_promo_add_cancel())
        return
    # дубль?
    existing = await PromoRepo(session).get_by_code(code)
    if existing is not None:
        await message.answer(T.addpromo_code_duplicate, reply_markup=kb_promo_add_cancel())
        return
    await state.update_data(code=code)
    await state.set_state(AddPromoStates.waiting_reward)
    await message.answer(T.addpromo_step2.format(code=code), reply_markup=kb_promo_add_cancel())


@router.message(AddPromoStates.waiting_reward)
async def msg_reward(message: Message, state: FSMContext) -> None:
    if message.text is None:
        await message.answer(T.addpromo_reward_invalid, reply_markup=kb_promo_add_cancel())
        return
    raw = message.text.strip().replace(",", ".")
    try:
        reward = float(raw)
    except ValueError:
        await message.answer(T.addpromo_reward_invalid, reply_markup=kb_promo_add_cancel())
        return
    if not math.isfinite(reward) or reward < 0 or reward > 1_000_000:
        await message.answer(T.addpromo_reward_invalid, reply_markup=kb_promo_add_cancel())
        return
    reward = round(reward, 2)
    await state.update_data(reward=reward)
    await state.set_state(AddPromoStates.waiting_max_activations)
    await message.answer(T.addpromo_step3, reply_markup=kb_promo_add_cancel())


@router.message(AddPromoStates.waiting_max_activations)
async def msg_max(message: Message, state: FSMContext) -> None:
    if message.text is None:
        await message.answer(T.addpromo_max_invalid, reply_markup=kb_promo_add_cancel())
        return
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer(T.addpromo_max_invalid, reply_markup=kb_promo_add_cancel())
        return
    max_act = int(raw)
    if max_act > 1_000_000_000:
        await message.answer(T.addpromo_max_invalid, reply_markup=kb_promo_add_cancel())
        return
    await state.update_data(max_activations=max_act)
    await state.set_state(AddPromoStates.waiting_expires_days)
    await message.answer(T.addpromo_step4, reply_markup=kb_promo_add_cancel())


@router.message(AddPromoStates.waiting_expires_days)
async def msg_expires(message: Message, state: FSMContext) -> None:
    if message.text is None:
        await message.answer(T.addpromo_expires_invalid, reply_markup=kb_promo_add_cancel())
        return
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer(T.addpromo_expires_invalid, reply_markup=kb_promo_add_cancel())
        return
    days = int(raw)
    if days > 36500:
        await message.answer(T.addpromo_expires_invalid, reply_markup=kb_promo_add_cancel())
        return
    expires_at: datetime | None = None
    if days > 0:
        expires_at = datetime.now(tz=timezone.utc) + timedelta(days=days)
    await state.update_data(expires_at_iso=expires_at.isoformat() if expires_at else None)
    await state.set_state(AddPromoStates.waiting_honeypot)
    await message.answer(T.addpromo_step5, reply_markup=kb_promo_add_honeypot())


@router.callback_query(
    AddPromoStates.waiting_honeypot,
    F.data.in_({"adm:promo:hp:yes", "adm:promo:hp:no"}),
)
async def cb_honeypot(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    is_honeypot = callback.data.endswith(":yes")
    data = await state.get_data()
    expires_iso = data.get("expires_at_iso")
    expires_at = datetime.fromisoformat(expires_iso) if expires_iso else None

    promo = await PromoRepo(session).create(
        code=data["code"],
        reward=float(data["reward"]),
        max_activations=int(data["max_activations"]),
        expires_at=expires_at,
        is_honeypot=is_honeypot,
        description=None,
    )
    await state.clear()
    await callback.answer(T.addpromo_created_alert)
    with suppress(TelegramAPIError):
        await callback.message.edit_text(
            T.addpromo_created.format(code=promo.code) + "\n\n" + _format_card(promo),
            reply_markup=kb_promo_card(promo),
        )


# ---------- helpers ----------

def _parse_id(data: str | None) -> int | None:
    if data is None:
        return None
    parts = data.split(":")
    if not parts[-1].isdigit():
        return None
    return int(parts[-1])
