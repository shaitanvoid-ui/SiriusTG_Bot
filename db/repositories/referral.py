from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import utcnow
from db.models import Referral, ReferralSource, User
from db.repositories.base import BaseRepo


class ReferralRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_referred(self, referred_user_id: int) -> Referral | None:
        res = await self.session.execute(
            select(Referral).where(Referral.referred_user_id == referred_user_id)
        )
        return res.scalar_one_or_none()

    async def create(
        self,
        *,
        referrer_user_id: int,
        referred_user_id: int,
        source: ReferralSource = ReferralSource.DIRECT,
    ) -> Referral:
        ref = Referral(
            referrer_user_id=referrer_user_id,
            referred_user_id=referred_user_id,
            source=source.value if isinstance(source, ReferralSource) else source,
        )
        self.session.add(ref)
        await self.session.flush()
        return ref

    async def count_today_by_referrer(self, referrer_user_id: int) -> int:
        since = utcnow() - timedelta(hours=24)
        res = await self.session.execute(
            select(func.count(Referral.id)).where(
                Referral.referrer_user_id == referrer_user_id,
                Referral.created_at >= since,
            )
        )
        return int(res.scalar_one() or 0)

    async def confirm(
        self,
        referral_id: int,
        *,
        reward: float,
        at: datetime | None = None,
    ) -> None:
        ref = await self.session.get(Referral, referral_id)
        if ref is None:
            return
        ref.is_confirmed = True
        ref.is_rewarded = True
        ref.reward_amount = reward
        ref.confirmed_at = at or utcnow()
        ref.lost_at = None

    async def mark_lost(self, referral_id: int, *, debt: float = 0.0) -> None:
        ref = await self.session.get(Referral, referral_id)
        if ref is None:
            return
        ref.is_confirmed = False
        ref.is_rewarded = False
        ref.debt_amount = round(ref.debt_amount + debt, 2)
        ref.lost_at = utcnow()

    async def mark_matured(self, referral_id: int, at: datetime | None = None) -> None:
        ref = await self.session.get(Referral, referral_id)
        if ref is None:
            return
        ref.is_matured = True
        ref.matured_at = at or utcnow()

    async def list_for_maturation(self, *, maturation_days: int, limit: int = 500) -> list[Referral]:
        threshold = utcnow() - timedelta(days=maturation_days)
        res = await self.session.execute(
            select(Referral)
            .where(
                Referral.is_confirmed.is_(True),
                Referral.is_matured.is_(False),
                Referral.confirmed_at.is_not(None),
                Referral.confirmed_at <= threshold,
            )
            .limit(limit)
        )
        return list(res.scalars().all())

    async def stats_for_referrer(self, referrer_user_id: int) -> dict[str, float]:
        confirmed_case = case((Referral.is_confirmed.is_(True), 1), else_=0)
        matured_case = case((Referral.is_matured.is_(True), 1), else_=0)
        res = await self.session.execute(
            select(
                func.count(Referral.id),
                func.coalesce(func.sum(confirmed_case), 0),
                func.coalesce(func.sum(matured_case), 0),
                func.coalesce(func.sum(Referral.reward_amount), 0.0),
                func.coalesce(func.sum(Referral.debt_amount), 0.0),
            ).where(Referral.referrer_user_id == referrer_user_id)
        )
        total, confirmed, matured, earned, debt = res.one()
        return {
            "total": int(total or 0),
            "confirmed": int(confirmed or 0),
            "matured": int(matured or 0),
            "earned": float(earned or 0.0),
            "debt": float(debt or 0.0),
        }

    # ---------- лидерборд (Этап 6) ----------

    async def leaderboard(
        self,
        *,
        since: datetime | None,
        limit: int,
        min_confirmed: int,
    ) -> list[tuple[int, int, int, str | None, str | None]]:
        """Топ рефереров по числу подтверждённых рефов.

        since=None — всё время; иначе считаем подтверждения с этой даты.
        Возвращает (referrer_user_id, score, tg_id, first_name, username).
        Баны/удалённые отфильтрованы.
        """
        score_col = func.count(Referral.id).label("score")
        conds = [Referral.is_confirmed.is_(True)]
        if since is not None:
            conds.append(Referral.confirmed_at >= since)
        res = await self.session.execute(
            select(
                Referral.referrer_user_id,
                score_col,
                User.tg_id,
                User.first_name,
                User.username,
            )
            .join(User, User.id == Referral.referrer_user_id)
            .where(*conds, User.is_banned.is_(False), User.is_deleted.is_(False))
            .group_by(Referral.referrer_user_id, User.tg_id, User.first_name, User.username)
            .having(func.count(Referral.id) >= min_confirmed)
            .order_by(func.count(Referral.id).desc(), Referral.referrer_user_id.asc())
            .limit(limit)
        )
        return [
            (int(r[0]), int(r[1]), int(r[2]), r[3], r[4]) for r in res.all()
        ]

    async def confirmed_count(
        self, referrer_user_id: int, *, since: datetime | None
    ) -> int:
        """Сколько подтверждённых рефов у реферера (за период или за всё время)."""
        conds = [
            Referral.referrer_user_id == referrer_user_id,
            Referral.is_confirmed.is_(True),
        ]
        if since is not None:
            conds.append(Referral.confirmed_at >= since)
        res = await self.session.execute(
            select(func.count(Referral.id)).where(*conds)
        )
        return int(res.scalar_one() or 0)

    async def count_referrers_above(
        self, *, score: int, since: datetime | None
    ) -> int:
        """Сколько рефереров строго выше переданного score (для расчёта ранга)."""
        cnt = func.count(Referral.id)
        conds = [Referral.is_confirmed.is_(True)]
        if since is not None:
            conds.append(Referral.confirmed_at >= since)
        sub = (
            select(Referral.referrer_user_id)
            .join(User, User.id == Referral.referrer_user_id)
            .where(*conds, User.is_banned.is_(False), User.is_deleted.is_(False))
            .group_by(Referral.referrer_user_id)
            .having(cnt > score)
            .subquery()
        )
        res = await self.session.execute(select(func.count()).select_from(sub))
        return int(res.scalar_one() or 0)
