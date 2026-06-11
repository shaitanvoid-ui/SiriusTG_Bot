"""Лидерборд по подтверждённым рефералам.

Периоды: week / month / all. Минимум подтв. рефов для попадания — из settings.
Воркер недельных выплат живёт в `workers/leaderboard_payout.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.referral import ReferralRepo
from services.settings import SettingsService


PERIODS: tuple[str, ...] = ("week", "month", "all")


def period_since(period: str) -> datetime | None:
    now = datetime.now(tz=timezone.utc)
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    return None


@dataclass(frozen=True)
class LeaderRow:
    rank: int
    user_id: int
    tg_id: int
    name: str
    username: str | None
    score: int


@dataclass(frozen=True)
class LeaderboardView:
    period: str
    rows: tuple[LeaderRow, ...]
    min_confirmed: int
    your_rank: int | None
    your_score: int


class LeaderboardService:
    def __init__(self, session: AsyncSession, settings_svc: SettingsService) -> None:
        self.session = session
        self.settings = settings_svc
        self.ref_repo = ReferralRepo(session)

    async def enabled(self) -> bool:
        return await self.settings.get_bool("leaderboard.enabled", True)

    async def top(
        self, period: str, *, limit: int | None = None, min_confirmed: int | None = None
    ) -> list[LeaderRow]:
        if period not in PERIODS:
            period = "all"
        if limit is None:
            limit = await self.settings.get_int("leaderboard.display_size", 15)
        if min_confirmed is None:
            min_confirmed = await self.settings.get_int("leaderboard.min_confirmed_refs", 10)
        rows = await self.ref_repo.leaderboard(
            since=period_since(period), limit=limit, min_confirmed=min_confirmed
        )
        out: list[LeaderRow] = []
        for i, (user_id, score, tg_id, first_name, username) in enumerate(rows):
            out.append(
                LeaderRow(
                    rank=i + 1,
                    user_id=user_id,
                    tg_id=tg_id,
                    name=(first_name or "Игрок"),
                    username=username,
                    score=score,
                )
            )
        return out

    async def rank_of(self, user_id: int, period: str) -> tuple[int | None, int]:
        """Возвращает (ранг, score). Ранг None, если не дотянул до минимума."""
        since = period_since(period)
        score = await self.ref_repo.confirmed_count(user_id, since=since)
        min_confirmed = await self.settings.get_int("leaderboard.min_confirmed_refs", 10)
        if score < min_confirmed:
            return None, score
        above = await self.ref_repo.count_referrers_above(score=score, since=since)
        return above + 1, score

    async def get_view(self, *, period: str, viewer_user_id: int) -> LeaderboardView:
        if period not in PERIODS:
            period = "all"
        min_confirmed = await self.settings.get_int("leaderboard.min_confirmed_refs", 10)
        rows = await self.top(period, min_confirmed=min_confirmed)
        your_rank, your_score = await self.rank_of(viewer_user_id, period)
        return LeaderboardView(
            period=period,
            rows=tuple(rows),
            min_confirmed=min_confirmed,
            your_rank=your_rank,
            your_score=your_score,
        )
