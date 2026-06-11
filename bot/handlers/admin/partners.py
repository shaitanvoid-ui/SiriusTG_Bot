"""Админка: раздел «Партнёры» (Этап 10).

Назначение партнёров, карточка со статистикой и персональными ставками,
обработка заявок на выплату (выплачено / отклонить с возвратом ⭐).
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import Bot, F, Router, html
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.handlers.admin._common import user_label as _user_label
from bot.keyboards.admin_panel import (
    kb_pa_cancel,
    kb_pa_card,
    kb_pa_payout_card,
    kb_pa_payouts,
    kb_pa_root,
)
from bot.states.admin import PartnerAdminStates
from db.models import Partner, PartnerStatus, PayoutMethod
from db.repositories.partner import PartnerPayoutRepo, PartnerRepo
from db.repositories.user import UserRepo
from locales.ru import T
from services.partner import PartnerService
from services.settings import SettingsService
from utils.ui import stars


router = Router(name="admin_partners")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _svc(session: AsyncSession) -> PartnerService:
    return PartnerService(session, SettingsService(session))


async def _render_root(message, session: AsyncSession) -> None:
    repo = PartnerRepo(session)
    user_repo = UserRepo(session)
    partners = await repo.list_all(limit=25)
    pending = await PartnerPayoutRepo(session).count_pending()
    rows: list[tuple[int, str]] = []
    for p in partners:
        user = await user_repo.get_by_id(p.user_id)
        status = "✅" if p.status == PartnerStatus.ACTIVE.value else "⏸"
        rows.append(
            (p.id, T.admin_pa_row.format(status=status, name=_user_label(user), balance=f"{p.balance:.2f}"))
        )
    text = T.admin_pa_root.format(active=await repo.count_active(), pending=pending)
    with suppress(Exception):
        await message.edit_text(text, reply_markup=kb_pa_root(rows, pending))


@router.callback_query(F.data == "adm:pa")
async def cb_root(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    if callback.message is None:
        await callback.answer()
        return
    await _render_root(callback.message, session)
    await callback.answer()


# ---------- назначение ----------

@router.callback_query(F.data == "adm:pa:add")
async def cb_add(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.set_state(PartnerAdminStates.waiting_user_query)
    with suppress(Exception):
        await callback.message.edit_text(T.admin_pa_add_prompt, reply_markup=kb_pa_cancel())
    await callback.answer()


@router.message(PartnerAdminStates.waiting_user_query, F.text)
async def msg_add(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    query = (message.text or "").strip()
    repo = UserRepo(session)
    if query.lstrip("-").isdigit():
        user = await repo.get_by_tg_id(int(query))
    else:
        user = await repo.get_by_username(query.lstrip("@"))
    if user is None:
        await message.answer(T.admin_pa_user_not_found, reply_markup=kb_pa_cancel())
        return
    await _svc(session).assign(user)
    await state.clear()
    await message.answer(T.admin_pa_assigned.format(name=html.quote(_user_label(user))))
    with suppress(TelegramAPIError):
        await bot.send_message(user.tg_id, T.notify_partner_assigned)
    sent = await message.answer("…")
    await _render_root(sent, session)


# ---------- карточка ----------

async def _render_card(message, session: AsyncSession, partner: Partner) -> None:
    svc = _svc(session)
    st = await svc.stats(partner)
    user = await UserRepo(session).get_by_id(partner.user_id)
    cpa = await svc.reward_per_user(partner)
    percent = await svc.percent_sponsor(partner)
    is_active = partner.status == PartnerStatus.ACTIVE.value
    text = T.admin_pa_card.format(
        id=partner.id,
        user_info=html.quote(_user_label(user)),
        status="✅ активен" if is_active else "⏸ на паузе",
        balance=stars(st.balance),
        total_earned=stars(st.total_earned),
        links_count=st.links_count,
        clicks=st.clicks,
        joins=st.joins,
        passed=st.passed,
        cpa=stars(cpa),
        cpa_mark=T.admin_pa_custom_mark if partner.reward_per_user is not None else "",
        percent=f"{percent:g}",
        percent_mark=T.admin_pa_custom_mark if partner.percent_sponsor is not None else "",
    )
    with suppress(Exception):
        await message.edit_text(text, reply_markup=kb_pa_card(partner.id, is_active))


async def _resolve(callback: CallbackQuery, session: AsyncSession) -> Partner | None:
    try:
        partner_id = int((callback.data or "0").rsplit(":", 1)[-1])
    except ValueError:
        return None
    return await PartnerRepo(session).get(partner_id)


@router.callback_query(F.data.startswith("adm:pa:open:"))
async def cb_card(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    partner = await _resolve(callback, session)
    if partner is None or callback.message is None:
        await callback.answer()
        return
    await _render_card(callback.message, session, partner)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:pa:tgl:"))
async def cb_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    partner = await _resolve(callback, session)
    if partner is None or callback.message is None:
        await callback.answer()
        return
    new_status = (
        PartnerStatus.PAUSED
        if partner.status == PartnerStatus.ACTIVE.value
        else PartnerStatus.ACTIVE
    )
    await PartnerRepo(session).set_status(partner.id, new_status)
    await session.refresh(partner)
    await _render_card(callback.message, session, partner)
    await callback.answer()


# ---------- персональные ставки ----------

@router.callback_query(F.data.startswith("adm:pa:cpa:"))
async def cb_cpa(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    partner = await _resolve(callback, session)
    if partner is None or callback.message is None:
        await callback.answer()
        return
    svc = _svc(session)
    current = await svc.reward_per_user(partner)
    await state.set_state(PartnerAdminStates.waiting_cpa)
    await state.update_data(pa_id=partner.id)
    with suppress(Exception):
        await callback.message.edit_text(
            T.admin_pa_cpa_prompt.format(
                current=stars(current),
                mark=T.admin_pa_custom_mark if partner.reward_per_user is not None else "",
            ),
            reply_markup=kb_pa_cancel(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:pa:pct:"))
async def cb_pct(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    partner = await _resolve(callback, session)
    if partner is None or callback.message is None:
        await callback.answer()
        return
    svc = _svc(session)
    current = await svc.percent_sponsor(partner)
    await state.set_state(PartnerAdminStates.waiting_percent)
    await state.update_data(pa_id=partner.id)
    with suppress(Exception):
        await callback.message.edit_text(
            T.admin_pa_percent_prompt.format(
                current=f"{current:g}",
                mark=T.admin_pa_custom_mark if partner.percent_sponsor is not None else "",
            ),
            reply_markup=kb_pa_cancel(),
        )
    await callback.answer()


def _parse_rate(raw: str) -> tuple[float | None, bool]:
    """(значение, ok). «-» → (None, True) — сброс на дефолт."""
    raw = raw.strip().replace(",", ".")
    if raw == "-":
        return None, True
    try:
        value = round(float(raw), 2)
    except ValueError:
        return None, False
    if value < 0:
        return None, False
    return value, True


async def _apply_rate(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    *,
    field: str,
) -> None:
    value, ok = _parse_rate(message.text or "")
    if not ok:
        await message.answer(T.admin_pa_rate_invalid, reply_markup=kb_pa_cancel())
        return
    data = await state.get_data()
    partner = await PartnerRepo(session).get(int(data.get("pa_id", 0)))
    if partner is None:
        await state.clear()
        return
    if field == "cpa":
        await PartnerRepo(session).set_rates(partner.id, reward_per_user=value)
    else:
        await PartnerRepo(session).set_rates(partner.id, percent_sponsor=value)
    await state.clear()
    await session.refresh(partner)
    await message.answer(T.admin_pa_rate_saved)
    sent = await message.answer("…")
    await _render_card(sent, session, partner)


@router.message(PartnerAdminStates.waiting_cpa, F.text)
async def msg_cpa(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await _apply_rate(message, state, session, field="cpa")


@router.message(PartnerAdminStates.waiting_percent, F.text)
async def msg_pct(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await _apply_rate(message, state, session, field="pct")


# ---------- заявки на выплату ----------

async def _render_payouts(message, session: AsyncSession) -> None:
    payouts = await PartnerPayoutRepo(session).list_pending(limit=25)
    partner_repo = PartnerRepo(session)
    user_repo = UserRepo(session)
    rows: list[tuple[int, str]] = []
    for p in payouts:
        partner = await partner_repo.get(p.partner_id)
        user = await user_repo.get_by_id(partner.user_id) if partner else None
        rows.append(
            (
                p.id,
                T.admin_pa_payout_row.format(
                    id=p.id,
                    name=_user_label(user),
                    stars=f"{p.amount_stars:.2f}⭐",
                    rub=f"{p.amount_rub:.2f}",
                ),
            )
        )
    body = "\n".join(label for _, label in rows) if rows else T.admin_pa_payouts_empty
    with suppress(Exception):
        await message.edit_text(
            T.admin_pa_payouts_caption.format(rows=body), reply_markup=kb_pa_payouts(rows)
        )


@router.callback_query(F.data == "adm:pa:pays")
async def cb_payouts(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    if callback.message is None:
        await callback.answer()
        return
    await _render_payouts(callback.message, session)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:pa:pay:"))
async def cb_payout_card(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None or callback.data is None:
        await callback.answer()
        return
    try:
        payout_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer()
        return
    payout = await PartnerPayoutRepo(session).get(payout_id)
    if payout is None:
        await callback.answer(T.admin_pa_payout_gone_alert, show_alert=True)
        return
    partner = await PartnerRepo(session).get(payout.partner_id)
    user = await UserRepo(session).get_by_id(partner.user_id) if partner else None
    method_name = (
        T.payout_method_card if payout.method == PayoutMethod.CARD.value else T.payout_method_yoomoney
    )
    text = T.admin_pa_payout_card.format(
        id=payout.id,
        user_info=html.quote(_user_label(user)),
        stars=f"{payout.amount_stars:.2f}⭐",
        rub=f"{payout.amount_rub:.2f}",
        rate=f"{payout.rate_rub:g}",
        method=method_name,
        requisites=html.quote(payout.requisites),
        date=payout.created_at.strftime("%d.%m.%Y %H:%M") if payout.created_at else "—",
    )
    with suppress(Exception):
        await callback.message.edit_text(text, reply_markup=kb_pa_payout_card(payout.id))
    await callback.answer()


async def _payout_user_tg_id(session: AsyncSession, partner_id: int) -> int | None:
    partner = await PartnerRepo(session).get(partner_id)
    if partner is None:
        return None
    user = await UserRepo(session).get_by_id(partner.user_id)
    return user.tg_id if user else None


@router.callback_query(F.data.startswith("adm:pa:paid:"))
async def cb_payout_paid(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if callback.message is None or callback.data is None:
        await callback.answer()
        return
    payout_id = int(callback.data.rsplit(":", 1)[-1])
    payout = await _svc(session).mark_payout_paid(payout_id)
    if payout is None:
        await callback.answer(T.admin_pa_payout_gone_alert, show_alert=True)
        return
    await session.commit()
    tg_id = await _payout_user_tg_id(session, payout.partner_id)
    if tg_id is not None:
        with suppress(TelegramAPIError):
            await bot.send_message(
                tg_id,
                T.notify_payout_paid.format(
                    stars=f"{payout.amount_stars:.2f}⭐", rub=f"{payout.amount_rub:.2f}"
                ),
            )
    await callback.answer(T.admin_pa_payout_done_alert, show_alert=False)
    await _render_payouts(callback.message, session)


@router.callback_query(F.data.startswith("adm:pa:rej:"))
async def cb_payout_reject(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if callback.message is None or callback.data is None:
        await callback.answer()
        return
    payout_id = int(callback.data.rsplit(":", 1)[-1])
    payout = await _svc(session).reject_payout(payout_id)
    if payout is None:
        await callback.answer(T.admin_pa_payout_gone_alert, show_alert=True)
        return
    await session.commit()
    tg_id = await _payout_user_tg_id(session, payout.partner_id)
    if tg_id is not None:
        note_part = T.notify_payout_note_part.format(note=html.quote(payout.note)) if payout.note else ""
        with suppress(TelegramAPIError):
            await bot.send_message(
                tg_id,
                T.notify_payout_rejected.format(
                    stars=f"{payout.amount_stars:.2f}⭐", note_part=note_part
                ),
            )
    await callback.answer(T.admin_pa_payout_rejected_alert, show_alert=False)
    await _render_payouts(callback.message, session)
