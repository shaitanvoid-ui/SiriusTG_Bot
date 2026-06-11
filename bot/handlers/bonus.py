"""Ежедневный бонус — экран и получение.

Edit-in-place: одна карточка обновляется при получении/обновлении.
Проверка bio (рефка в профиле) — через userbot (Telethon). Если userbot
не настроен/недоступен — мягкий алерт, попытка не «сгорает».
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.bonus import kb_bonus
from db.models import User
from db.repositories.user import UserRepo
from locales.ru import T
from services.bonus import BioOutcome, BonusService, BonusStatus, BonusView
from services.settings import SettingsService
from userbot import bio_reader
from utils.links import build_referral_link, get_bot_username
from utils.ui import stars


router = Router(name="bonus")


def _ladder(tiers: dict[int, float], streak: int) -> str:
    """Визуальная лесенка стрика: ✅ пройдено / 🎯 ближайшая цель / ⬜ впереди."""
    ahead = sorted(t for t in tiers if t > streak)
    next_t = ahead[0] if ahead else None
    rows: list[str] = []
    for t in sorted(tiers):
        amount = stars(tiers[t])
        if t <= streak:
            rows.append(T.bonus_ladder_done.format(days=t, amount=amount))
        elif t == next_t:
            rows.append(T.bonus_ladder_next.format(days=t, amount=amount))
        else:
            rows.append(T.bonus_ladder_locked.format(days=t, amount=amount))
    return "\n".join(rows)


def _render(view: BonusView, *, link: str, tiers: dict[int, float]) -> str:
    if view.next_threshold is not None and view.next_amount is not None:
        days = max(1, view.next_threshold - view.streak)
        next_line = T.bonus_next_line.format(days=days, amount=stars(view.next_amount))
    else:
        next_line = T.bonus_next_max

    if view.bio_required:
        bio_block = T.bonus_bio_block.format(link=link)
    else:
        bio_block = T.bonus_bio_off

    return T.bonus_caption.format(
        streak=view.streak,
        today_amount=stars(view.today_amount),
        ladder=_ladder(tiers, view.streak),
        next_line=next_line,
        balance=stars(view.balance),
        bio_block=bio_block,
    )


async def _send_card(
    callback: CallbackQuery, view: BonusView, *, link: str, tiers: dict[int, float]
) -> None:
    if callback.message is None:
        return
    text = _render(view, link=link, tiers=tiers)
    kb = kb_bonus(can_claim=not view.claimed_today)
    with suppress(Exception):
        await callback.message.edit_text(text, reply_markup=kb)


async def _resolve_user(callback: CallbackQuery, session: AsyncSession, db_user: User | None) -> User | None:
    if callback.from_user is None or callback.message is None:
        return None
    return db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)


@router.callback_query(F.data == "bns:open")
async def cb_open(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    db_user: User | None = None,
) -> None:
    user = await _resolve_user(callback, session, db_user)
    if user is None:
        await callback.answer()
        return
    svc = BonusService(session, SettingsService(session))
    view = await svc.get_view(user)
    link = await build_referral_link(bot, user.tg_id)
    await _send_card(callback, view, link=link, tiers=await svc.tiers())
    await callback.answer()


@router.callback_query(F.data == "bns:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer(T.bonus_already_alert, show_alert=False)


@router.callback_query(F.data == "bns:claim")
async def cb_claim(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    db_user: User | None = None,
) -> None:
    user = await _resolve_user(callback, session, db_user)
    if user is None:
        await callback.answer()
        return

    svc = BonusService(session, SettingsService(session))
    bot_username = await get_bot_username(bot)
    payload = f"r{user.tg_id}"

    async def _checker() -> BioOutcome:
        available, has_ref = await bio_reader.check_ref_in_bio(
            tg_id=user.tg_id,
            username=user.username,
            payload=payload,
            bot_username=bot_username,
        )
        if not available:
            return BioOutcome.UNAVAILABLE
        return BioOutcome.OK if has_ref else BioOutcome.MISSING

    result = await svc.claim(user, bio_checker=_checker)
    link = await build_referral_link(bot, user.tg_id)
    tiers = await svc.tiers()

    if result.status == BonusStatus.OK:
        view = await svc.get_view(user)
        await _send_card(callback, view, link=link, tiers=tiers)
        await callback.answer(
            T.bonus_ok_alert.format(amount=stars(result.amount), streak=result.streak),
            show_alert=True,
        )
        return

    if result.status == BonusStatus.ALREADY:
        view = await svc.get_view(user)
        await _send_card(callback, view, link=link, tiers=tiers)
        await callback.answer(T.bonus_already_alert, show_alert=False)
        return

    if result.status == BonusStatus.BIO_MISSING:
        # обновим карточку — пусть ссылка для bio будет перед глазами
        view = await svc.get_view(user)
        await _send_card(callback, view, link=link, tiers=tiers)
        await callback.answer(T.bonus_bio_missing_alert, show_alert=True)
        return

    # UNAVAILABLE
    await callback.answer(T.bonus_unavailable_alert, show_alert=True)
