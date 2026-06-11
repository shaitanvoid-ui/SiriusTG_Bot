"""Партнёрская панель (Этап 10): статистика, UTM-ссылки, свои каналы, выплаты.

Доступ — только юзерам с активной/приостановленной партнёрской записью
(назначает owner из админки). Все суммы и лимиты — из settings `partner.*`.
"""

from __future__ import annotations

import re
from contextlib import suppress

from aiogram import Bot, F, Router, html
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.partner import (
    kb_partner_back,
    kb_partner_cancel,
    kb_partner_link_card,
    kb_partner_links,
    kb_partner_payout_method,
    kb_partner_root,
    kb_partner_sponsors,
)
from bot.states.partner import PartnerLinkStates, PartnerPayoutStates, PartnerSponsorStates
from db.models import Partner, PartnerStatus, PayoutMethod, PayoutStatus, SponsorKind, User
from db.repositories.partner import PartnerLinkRepo, PartnerPayoutRepo
from db.repositories.sponsor import SponsorRepo
from locales.ru import T
from services.partner import PartnerService, PayoutRequestStatus
from services.settings import SettingsService
from utils.links import get_bot_username
from utils.tz import fmt_date
from utils.ui import stars


router = Router(name="partner")

_USERNAME_RE = re.compile(r"^@?([A-Za-z][A-Za-z0-9_]{3,31})$")


def _svc(session: AsyncSession) -> PartnerService:
    return PartnerService(session, SettingsService(session))


async def _get_partner(
    callback: CallbackQuery, session: AsyncSession, db_user: User | None
) -> Partner | None:
    """Партнёрская запись текущего юзера или None (+ alert, если паужен/не партнёр)."""
    if db_user is None:
        await callback.answer()
        return None
    partner = await _svc(session).get_for_user(db_user)
    if partner is None:
        await callback.answer(T.forbidden, show_alert=True)
        return None
    return partner


async def _render_root(
    message, session: AsyncSession, partner: Partner
) -> None:
    svc = _svc(session)
    st = await svc.stats(partner)
    cpa = await svc.reward_per_user(partner)
    percent = await svc.percent_sponsor(partner)
    rate = await svc.settings.get_float("partner.rub_per_star", 1.5)
    min_payout = await svc.settings.get_float("partner.min_payout_stars", 50.0)
    text = T.partner_caption.format(
        balance=stars(st.balance),
        total_earned=stars(st.total_earned),
        links_count=st.links_count,
        clicks=st.clicks,
        joins=st.joins,
        passed=st.passed,
        cpa=stars(cpa),
        percent=f"{percent:g}",
        rate=f"{rate:g}",
        min_payout=stars(min_payout),
    )
    with suppress(Exception):
        await message.edit_text(text, reply_markup=kb_partner_root())


@router.callback_query(F.data == "pa:open")
async def cb_open(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    partner = await _get_partner(callback, session, db_user)
    if partner is None or callback.message is None:
        return
    await state.clear()
    if partner.status != PartnerStatus.ACTIVE.value:
        await callback.answer(T.partner_paused_alert, show_alert=True)
    await _render_root(callback.message, session, partner)
    await callback.answer()


# ---------- UTM-ссылки ----------

async def _render_links(message, session: AsyncSession, partner: Partner) -> None:
    links = await PartnerLinkRepo(session).list_for_partner(partner.id)
    max_links = await SettingsService(session).get_int("partner.max_links", 10)
    if links:
        rows = "\n".join(
            T.partner_link_row.format(
                title=html.quote(l.title), clicks=l.clicks, joins=l.joins, passed=l.passed
            )
            for l in links
        )
    else:
        rows = T.partner_links_empty
    with suppress(Exception):
        await message.edit_text(
            T.partner_links_caption.format(rows=rows, max_links=max_links),
            reply_markup=kb_partner_links(links),
        )


@router.callback_query(F.data == "pa:links")
async def cb_links(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    partner = await _get_partner(callback, session, db_user)
    if partner is None or callback.message is None:
        return
    await state.clear()
    await _render_links(callback.message, session, partner)
    await callback.answer()


@router.callback_query(F.data == "pa:lnk:add")
async def cb_link_add(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    partner = await _get_partner(callback, session, db_user)
    if partner is None or callback.message is None:
        return
    max_links = await SettingsService(session).get_int("partner.max_links", 10)
    if await PartnerLinkRepo(session).count_for_partner(partner.id) >= max_links:
        await callback.answer(
            T.partner_link_limit_alert.format(max_links=max_links), show_alert=True
        )
        return
    await state.set_state(PartnerLinkStates.waiting_title)
    with suppress(Exception):
        await callback.message.edit_text(
            T.partner_link_title_prompt, reply_markup=kb_partner_cancel()
        )
    await callback.answer()


@router.message(PartnerLinkStates.waiting_title, F.text)
async def msg_link_title(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if db_user is None:
        return
    partner = await _svc(session).get_for_user(db_user)
    if partner is None:
        await state.clear()
        return
    title = (message.text or "").strip()
    if not title:
        await message.answer(T.partner_link_title_prompt, reply_markup=kb_partner_cancel())
        return
    link = await _svc(session).create_link(partner, title)
    await state.clear()
    if link is None:
        max_links = await SettingsService(session).get_int("partner.max_links", 10)
        await message.answer(T.partner_link_limit_alert.format(max_links=max_links))
        return
    sent = await message.answer("…")
    await _render_link_card(sent, message.bot, link)


async def _render_link_card(message, bot: Bot | None, link) -> None:
    username = await get_bot_username(bot) if bot else ""
    url = f"https://t.me/{username}?start=p{link.code}" if username else f"start=p{link.code}"
    with suppress(Exception):
        await message.edit_text(
            T.partner_link_card.format(
                title=html.quote(link.title),
                url=url,
                clicks=link.clicks,
                joins=link.joins,
                passed=link.passed,
            ),
            reply_markup=kb_partner_link_card(link.id),
        )


@router.callback_query(F.data.startswith("pa:lnk:del:"))
async def cb_link_delete(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    partner = await _get_partner(callback, session, db_user)
    if partner is None or callback.message is None or callback.data is None:
        return
    link_id = int(callback.data.rsplit(":", 1)[-1])
    repo = PartnerLinkRepo(session)
    link = await repo.get(link_id)
    if link is None or link.partner_id != partner.id:
        await callback.answer()
        return
    await repo.soft_delete(link_id)
    await callback.answer(T.partner_link_deleted_alert, show_alert=False)
    await _render_links(callback.message, session, partner)


@router.callback_query(F.data.startswith("pa:lnk:"))
async def cb_link_card(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    partner = await _get_partner(callback, session, db_user)
    if partner is None or callback.message is None or callback.data is None:
        return
    try:
        link_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer()
        return
    link = await PartnerLinkRepo(session).get(link_id)
    if link is None or link.partner_id != partner.id or link.is_deleted:
        await callback.answer()
        return
    await _render_link_card(callback.message, callback.bot, link)
    await callback.answer()


# ---------- свои каналы (спонсоры партнёра) ----------

async def _render_sponsors(message, session: AsyncSession, partner: Partner) -> None:
    all_sponsors = await SponsorRepo(session).list_all()
    own = [s for s in all_sponsors if s.partner_id == partner.id]
    if own:
        rows = "\n".join(
            T.partner_sponsor_row.format(
                status=(
                    T.partner_sponsor_status_active
                    if s.is_active
                    else (
                        T.partner_sponsor_status_pending
                        if s.reward <= 0
                        else T.partner_sponsor_status_paused
                    )
                ),
                title=html.quote(s.title),
                reward=stars(s.reward),
            )
            for s in own
        )
    else:
        rows = T.partner_sponsors_empty
    with suppress(Exception):
        await message.edit_text(
            T.partner_sponsors_caption.format(rows=rows),
            reply_markup=kb_partner_sponsors(),
        )


@router.callback_query(F.data == "pa:sp")
async def cb_sponsors(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    partner = await _get_partner(callback, session, db_user)
    if partner is None or callback.message is None:
        return
    await state.clear()
    await _render_sponsors(callback.message, session, partner)
    await callback.answer()


@router.callback_query(F.data == "pa:sp:add")
async def cb_sponsor_add(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    partner = await _get_partner(callback, session, db_user)
    if partner is None or callback.message is None:
        return
    await state.set_state(PartnerSponsorStates.waiting_channel)
    with suppress(Exception):
        await callback.message.edit_text(
            T.partner_sponsor_prompt, reply_markup=kb_partner_cancel()
        )
    await callback.answer()


@router.message(PartnerSponsorStates.waiting_channel, F.text)
async def msg_sponsor_channel(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    db_user: User | None = None,
) -> None:
    if db_user is None:
        return
    partner = await _svc(session).get_for_user(db_user)
    if partner is None:
        await state.clear()
        return

    m = _USERNAME_RE.match((message.text or "").strip())
    if m is None:
        await message.answer(T.partner_sponsor_invalid, reply_markup=kb_partner_cancel())
        return
    username = m.group(1)

    try:
        chat = await bot.get_chat(f"@{username}")
        member = await bot.get_chat_member(chat.id, bot.id)
        if member.status not in ("administrator", "creator"):
            await message.answer(T.partner_sponsor_invalid, reply_markup=kb_partner_cancel())
            return
    except TelegramAPIError:
        await message.answer(T.partner_sponsor_invalid, reply_markup=kb_partner_cancel())
        return

    repo = SponsorRepo(session)
    existing = await repo.get_by_username(username) or (
        await repo.get_by_chat_id(chat.id) if chat.id else None
    )
    if existing is not None:
        await message.answer(T.partner_sponsor_exists, reply_markup=kb_partner_cancel())
        return

    title = chat.title or username
    sponsor = await repo.create(
        kind=SponsorKind.PUBLIC,
        title=title,
        chat_id=chat.id,
        username=username,
        is_required=False,
        is_active=False,  # активирует owner после проверки и установки награды
    )
    sponsor.partner_id = partner.id
    await state.clear()
    await message.answer(
        T.partner_sponsor_created.format(title=html.quote(title)),
        reply_markup=kb_partner_back(),
    )


# ---------- выплаты ----------

@router.callback_query(F.data == "pa:pay")
async def cb_payout(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    partner = await _get_partner(callback, session, db_user)
    if partner is None or callback.message is None:
        return
    await state.clear()
    svc = _svc(session)
    min_amount = await svc.settings.get_float("partner.min_payout_stars", 50.0)
    if partner.status != PartnerStatus.ACTIVE.value:
        await callback.answer(T.partner_payout_not_active_alert, show_alert=True)
        return
    if await PartnerPayoutRepo(session).get_pending_for_partner(partner.id) is not None:
        await callback.answer(T.partner_payout_pending_alert, show_alert=True)
        return
    if partner.balance < min_amount:
        await callback.answer(
            T.partner_payout_too_small_alert.format(min_amount=stars(min_amount)),
            show_alert=True,
        )
        return
    rate = await svc.settings.get_float("partner.rub_per_star", 1.5)
    with suppress(Exception):
        await callback.message.edit_text(
            T.partner_payout_intro.format(
                balance=stars(partner.balance),
                rub=f"{partner.balance * rate:.2f}",
                rate=f"{rate:g}",
            ),
            reply_markup=kb_partner_payout_method(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("pa:pay:m:"))
async def cb_payout_method(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    partner = await _get_partner(callback, session, db_user)
    if partner is None or callback.message is None or callback.data is None:
        return
    method = callback.data.rsplit(":", 1)[-1]
    if method not in (PayoutMethod.CARD.value, PayoutMethod.YOOMONEY.value):
        await callback.answer()
        return
    await state.set_state(PartnerPayoutStates.waiting_requisites)
    await state.update_data(payout_method=method)
    what = (
        T.partner_payout_what_card
        if method == PayoutMethod.CARD.value
        else T.partner_payout_what_yoomoney
    )
    with suppress(Exception):
        await callback.message.edit_text(
            T.partner_payout_requisites_prompt.format(
                what=what, amount=stars(partner.balance)
            ),
            reply_markup=kb_partner_cancel(),
        )
    await callback.answer()


@router.message(PartnerPayoutStates.waiting_requisites, F.text)
async def msg_payout_requisites(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    db_user: User | None = None,
) -> None:
    if db_user is None:
        return
    svc = _svc(session)
    partner = await svc.get_for_user(db_user)
    if partner is None:
        await state.clear()
        return
    data = await state.get_data()
    method = PayoutMethod(data.get("payout_method", PayoutMethod.CARD.value))
    requisites = (message.text or "").strip()
    if not requisites:
        return

    result = await svc.request_payout(partner, method=method, requisites=requisites)
    await state.clear()

    if result.status == PayoutRequestStatus.ALREADY_PENDING:
        await message.answer(T.partner_payout_pending_alert, reply_markup=kb_partner_back())
        return
    if result.status == PayoutRequestStatus.NOT_ACTIVE:
        await message.answer(T.partner_payout_not_active_alert, reply_markup=kb_partner_back())
        return
    if result.status == PayoutRequestStatus.TOO_SMALL or result.payout is None:
        await message.answer(
            T.partner_payout_too_small_alert.format(min_amount=stars(result.min_amount)),
            reply_markup=kb_partner_back(),
        )
        return

    payout = result.payout
    await message.answer(
        T.partner_payout_created.format(
            amount=stars(payout.amount_stars), rub=f"{payout.amount_rub:.2f}"
        ),
        reply_markup=kb_partner_back(),
    )

    # лог-канал — после успешной заявки
    from core.config import settings as app_settings

    if app_settings.log_channel_id is not None:
        name = f"@{db_user.username}" if db_user.username else str(db_user.tg_id)
        with suppress(TelegramAPIError):
            await bot.send_message(
                app_settings.log_channel_id,
                T.log_partner_payout_requested.format(
                    id=payout.id,
                    name=name,
                    stars=stars(payout.amount_stars),
                    rub=f"{payout.amount_rub:.2f}",
                ),
            )


@router.callback_query(F.data == "pa:hist")
async def cb_history(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    partner = await _get_partner(callback, session, db_user)
    if partner is None or callback.message is None:
        return
    payouts = await PartnerPayoutRepo(session).list_for_partner(partner.id, limit=10)
    status_icons = {
        PayoutStatus.PENDING.value: T.payout_status_pending,
        PayoutStatus.PAID.value: T.payout_status_paid,
        PayoutStatus.REJECTED.value: T.payout_status_rejected,
    }
    if payouts:
        rows = "\n".join(
            T.partner_history_row.format(
                status=status_icons.get(p.status, "•"),
                stars=stars(p.amount_stars),
                rub=f"{p.amount_rub:.2f}",
                date=fmt_date(p.created_at) if p.created_at else "—",
            )
            for p in payouts
        )
    else:
        rows = T.partner_history_empty
    with suppress(Exception):
        await callback.message.edit_text(
            T.partner_history_caption.format(rows=rows), reply_markup=kb_partner_back()
        )
    await callback.answer()
