"""Лидерборд — Топ по рефералам с переключателем периода (неделя/месяц/всё время)."""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router, html
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.leaderboard import kb_leaderboard
from db.models import User
from db.repositories.user import UserRepo
from locales.ru import T
from services.leaderboard import PERIODS, LeaderboardService, LeaderboardView
from services.settings import SettingsService
from utils.ui import SOFT_DIVIDER


router = Router(name="leaderboard")

_PERIOD_NAMES = {
    "week": T.top_period_week,
    "month": T.top_period_month,
    "all": T.top_period_all,
}


def _medal(rank: int) -> str:
    return {1: "👑", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")


def _your_line(view: LeaderboardView) -> str:
    if view.your_rank is not None:
        return T.top_your_ranked.format(rank=view.your_rank, score=view.your_score)
    return T.top_your_unranked.format(
        score=view.your_score, min_confirmed=view.min_confirmed
    )


def _render(view: LeaderboardView) -> str:
    period_name = _PERIOD_NAMES.get(view.period, T.top_period_all)
    your_line = _your_line(view)
    if not view.rows:
        return T.top_empty.format(
            period_name=period_name,
            min_confirmed=view.min_confirmed,
            your_line=your_line,
        )
    row_lines: list[str] = []
    for r in view.rows:
        row_lines.append(
            T.top_row.format(medal=_medal(r.rank), name=html.quote(r.name), score=r.score)
        )
        # визуально отделяем подиум (топ-3) от остального списка
        if r.rank == 3 and len(view.rows) > 3:
            row_lines.append(SOFT_DIVIDER)
    rows = "\n".join(row_lines)
    return T.top_caption.format(
        period_name=period_name,
        rows=rows,
        your_line=your_line,
        min_confirmed=view.min_confirmed,
    )


async def _show(
    callback: CallbackQuery, session: AsyncSession, user: User, period: str
) -> None:
    svc = LeaderboardService(session, SettingsService(session))
    if not await svc.enabled():
        await callback.answer(T.top_disabled_alert, show_alert=True)
        return
    view = await svc.get_view(period=period, viewer_user_id=user.id)
    if callback.message is not None:
        with suppress(Exception):
            await callback.message.edit_text(
                _render(view), reply_markup=kb_leaderboard(view.period)
            )
    await callback.answer()


@router.callback_query(F.data == "top:open")
async def cb_open(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return
    await _show(callback, session, user, "week")


@router.callback_query(F.data.startswith("top:p:"))
async def cb_period(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.data is None or callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    period = callback.data.rsplit(":", 1)[-1]
    if period not in PERIODS:
        period = "week"
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return
    await _show(callback, session, user, period)
