"""Раздел «Рефералы» — ссылка, статистика, готовый текст для шеринга."""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.referral import kb_referral, kb_referral_text_view
from db.models import User
from db.repositories.user import UserRepo
from locales.ru import T
from services.referral import ReferralService
from services.settings import SettingsService
from utils.links import build_referral_link, build_share_url
from utils.ui import stars


router = Router(name="referral")


async def _render_caption(session: AsyncSession, user: User, link: str) -> str:
    settings_svc = SettingsService(session)
    ref_svc = ReferralService(session, settings_svc)

    reward = await settings_svc.get_float("ref.reward", 3.0)
    daily_limit = await settings_svc.get_int("ref.daily_limit", 0)
    maturation_days = await settings_svc.get_int("ref.maturation_days", 7)
    stats = await ref_svc.stats(user.id)

    debt_part = (
        T.referral_debt_part.format(debt=stars(stats["debt"]))
        if stats["debt"] > 0
        else ""
    )
    limit_part = (
        T.referral_with_limit.format(daily_limit=daily_limit)
        if daily_limit > 0
        else T.referral_no_limit
    )

    return T.referral_caption.format(
        reward=stars(reward),
        link=link,
        total=stats["total"],
        confirmed=stats["confirmed"],
        matured=stats["matured"],
        earned=stars(stats["earned"]),
        debt_part=debt_part,
        maturation_days=maturation_days,
        limit_part=limit_part,
    )


@router.callback_query(F.data == "ref:open")
async def cb_open_referrals(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.message is None or callback.from_user is None or callback.bot is None:
        await callback.answer()
        return
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return
    link = await build_referral_link(callback.bot, user.tg_id)
    caption = await _render_caption(session, user, link)
    share_text = T.ref_share_text.format(link=link)
    share_url = build_share_url(link, share_text)
    with suppress(Exception):
        await callback.message.edit_text(
            caption,
            reply_markup=kb_referral(share_url=share_url),
            disable_web_page_preview=True,
        )
    await callback.answer()


@router.callback_query(F.data == "ref:txt")
async def cb_referral_text(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.message is None or callback.from_user is None or callback.bot is None:
        await callback.answer()
        return
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return
    link = await build_referral_link(callback.bot, user.tg_id)
    share_text = T.ref_share_text.format(link=link)
    caption = T.ref_share_view_caption + f"\n<pre>{share_text}</pre>"
    with suppress(Exception):
        await callback.message.edit_text(
            caption,
            reply_markup=kb_referral_text_view(),
            disable_web_page_preview=True,
        )
    await callback.answer()
