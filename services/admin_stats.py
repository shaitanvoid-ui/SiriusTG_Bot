"""Агрегаты для админ-дашборда (Этап 9).

Только чтение: сводка по юзерам, обязательствам и активности за московские сутки.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    ClickerDay,
    DailyBonusLog,
    Referral,
    Review,
    ReviewStatus,
    UserTaskCompletion,
    WheelSpin,
)
from db.repositories.user import UserRepo
from utils.tz import msk_day_start_utc, today_msk


def _today() -> date:
    return today_msk()


def _today_start() -> datetime:
    return msk_day_start_utc()


@dataclass(frozen=True)
class DashboardStats:
    users_total: int
    users_passed: int
    users_banned: int
    users_shadow: int
    users_new_today: int
    balance_total: float
    debt_total: float
    clicks_today: int
    bonuses_today: int
    spins_today: int
    tasks_today: int
    refs_today: int
    reviews_pending: int


class AdminStatsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def dashboard(self) -> DashboardStats:
        user_repo = UserRepo(self.session)
        counts = await user_repo.counts_summary()
        balances = await user_repo.balance_summary()
        new_today = await user_repo.joined_since(_today_start())

        today = _today()
        start = _today_start()

        clicks = await self.session.scalar(
            select(func.coalesce(func.sum(ClickerDay.clicks), 0)).where(ClickerDay.day == today)
        )
        bonuses = await self.session.scalar(
            select(func.count(DailyBonusLog.id)).where(DailyBonusLog.day == today)
        )
        spins = await self.session.scalar(
            select(func.count(WheelSpin.id)).where(WheelSpin.day == today)
        )
        tasks = await self.session.scalar(
            select(func.count(UserTaskCompletion.id)).where(
                UserTaskCompletion.created_at >= start
            )
        )
        refs = await self.session.scalar(
            select(func.count(Referral.id)).where(Referral.created_at >= start)
        )
        reviews_pending = await self.session.scalar(
            select(func.count(Review.id)).where(Review.status == ReviewStatus.PENDING.value)
        )

        return DashboardStats(
            users_total=counts["total"],
            users_passed=counts["passed"],
            users_banned=counts["banned"],
            users_shadow=counts["shadow"],
            users_new_today=int(new_today or 0),
            balance_total=balances["balance"],
            debt_total=balances["debt"],
            clicks_today=int(clicks or 0),
            bonuses_today=int(bonuses or 0),
            spins_today=int(spins or 0),
            tasks_today=int(tasks or 0),
            refs_today=int(refs or 0),
            reviews_pending=int(reviews_pending or 0),
        )
