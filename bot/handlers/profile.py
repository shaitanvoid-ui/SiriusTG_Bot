"""Раздел «Профиль» — карточка юзера с балансом, уровнем и рефералами."""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router, html
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.sections import kb_profile
from db.models import User
from db.repositories.user import UserRepo
from locales.ru import T
from services.level import LevelService
from services.partner import PartnerService
from services.referral import ReferralService
from services.settings import SettingsService
from utils.ui import progress_bar, stars


router = Router(name="profile")


def _format_join_date(user: User) -> str:
    if user.created_at is None:
        return "—"
    return user.created_at.strftime("%d.%m.%Y")


async def _render_caption(session: AsyncSession, user: User) -> str:
    settings_svc = SettingsService(session)
    level_svc = LevelService(settings_svc)
    ref_svc = ReferralService(session, settings_svc)

    info = await level_svc.compute(user.confirmed_ref_count)
    stats = await ref_svc.stats(user.id)

    bar = progress_bar(info.progress_current, info.progress_total)
    if info.is_max:
        progress_text = T.menu_progress_max
    else:
        progress_text = T.menu_progress_to_next.format(
            next_name=info.next_name,
            to_next=info.to_next,
        )

    if user.username:
        username_line = T.profile_username_line.format(username=html.quote(user.username))
    else:
        username_line = T.profile_no_username_line

    debt_part = (
        T.profile_debt_part.format(debt=stars(user.debt))
        if user.debt > 0
        else ""
    )

    name = html.quote(user.first_name or "друг")
    return T.profile_caption.format(
        name=name,
        username_line=username_line,
        tg_id=user.tg_id,
        balance=stars(user.balance),
        debt_part=debt_part,
        level_emoji=info.emoji,
        level_name=info.name,
        progress_bar=bar,
        progress_text=progress_text,
        ref_total=stats["total"],
        ref_confirmed=stats["confirmed"],
        ref_matured=stats["matured"],
        join_date=_format_join_date(user),
        streak=user.bonus_streak,
    )


@router.callback_query(F.data == "prof:open")
async def cb_open_profile(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return
    caption = await _render_caption(session, user)
    partner = await PartnerService(session, SettingsService(session)).get_for_user(user)
    with suppress(Exception):
        await callback.message.edit_text(
            caption, reply_markup=kb_profile(is_partner=partner is not None)
        )
    await callback.answer()
