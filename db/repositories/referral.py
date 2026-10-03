from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, func, literal, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import utcnow
from db.money import from_units, settlement_units, to_units
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

    async def create_if_absent(
        self,
        *,
        referrer_user_id: int,
        referred_user_id: int,
        source: ReferralSource = ReferralSource.DIRECT,
        daily_limit: int = 0,
    ) -> Referral | None:
        source_value = source.value if isinstance(source, ReferralSource) else source
        insert_stmt = sqlite_insert(Referral)
        if daily_limit > 0:
            since = utcnow() - timedelta(hours=24)
            used_slots = (
                select(func.count(Referral.id))
                .where(
                    Referral.referrer_user_id == referrer_user_id,
                    Referral.created_at >= since,
                )
                .scalar_subquery()
            )
            insert_stmt = insert_stmt.from_select(
                ["referrer_user_id", "referred_user_id", "source"],
                select(
                    literal(referrer_user_id),
                    literal(referred_user_id),
                    literal(source_value),
                ).where(used_slots < daily_limit),
            )
        else:
            insert_stmt = insert_stmt.values(
                referrer_user_id=referrer_user_id,
                referred_user_id=referred_user_id,
                source=source_value,
            )
        stmt = (
            insert_stmt.on_conflict_do_nothing(index_elements=["referred_user_id"])
            .returning(Referral.id)
        )
        referral_id = (await self.session.execute(stmt)).scalar_one_or_none()
        return await self.session.get(Referral, referral_id) if referral_id else None

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
    ) -> bool:
        result = await self.session.execute(
            update(Referral)
            .where(
                Referral.id == referral_id,
                Referral.is_confirmed.is_(False),
            )
            .values(
                is_confirmed=True,
                is_rewarded=True,
                reward_amount_units=to_units(reward),
                confirmed_at=at or utcnow(),
                lost_at=None,
            )
            .returning(Referral.id)
            .execution_options(synchronize_session="fetch")
        )
        return result.scalar_one_or_none() is not None

    async def claim_loss(self, referral_id: int) -> bool:
        """Атомарно резервирует откат подтверждённого незрелого реферала."""
        result = await self.session.execute(
            update(Referral)
            .where(
                Referral.id == referral_id,
                Referral.is_confirmed.is_(True),
                Referral.is_matured.is_(False),
            )
            .values(is_confirmed=False, is_rewarded=False, lost_at=utcnow())
            .returning(Referral.id)
            .execution_options(synchronize_session="fetch")
        )
        return result.scalar_one_or_none() is not None

    async def add_loss_debt(self, referral_id: int, debt: float) -> None:
        if debt <= 0:
            return
        await self.session.execute(
            update(Referral)
            .where(Referral.id == referral_id)
            .values(debt_amount_units=Referral.debt_amount_units + settlement_units(debt))
            .execution_options(synchronize_session="fetch")
        )

    async def mark_lost(self, referral_id: int, *, debt: float = 0.0) -> None:
        """Совместимый фасад для старых вызовов."""
        if await self.claim_loss(referral_id):
            await self.add_loss_debt(referral_id, debt)

    async def mark_matured(self, referral_id: int, at: datetime | None = None) -> bool:
        result = await self.session.execute(
            update(Referral)
            .where(
                Referral.id == referral_id,
                Referral.is_confirmed.is_(True),
                Referral.is_matured.is_(False),
            )
            .values(is_matured=True, matured_at=at or utcnow())
            .returning(Referral.id)
            .execution_options(synchronize_session="fetch")
        )
        return result.scalar_one_or_none() is not None

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
                func.coalesce(func.sum(Referral.reward_amount_units), 0),
                func.coalesce(func.sum(Referral.debt_amount_units), 0),
            ).where(Referral.referrer_user_id == referrer_user_id)
        )
        total, confirmed, matured, earned, debt = res.one()
        return {
            "total": int(total or 0),
            "confirmed": int(confirmed or 0),
            "matured": int(matured or 0),
            "earned": float(from_units(earned or 0)),
            "debt": float(from_units(debt or 0)),
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
            .where(*conds, User.is_banned.is_(False), User.is_shadow_banned.is_(False), User.is_deleted.is_(False))
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
            .where(*conds, User.is_banned.is_(False), User.is_shadow_banned.is_(False), User.is_deleted.is_(False))
            .group_by(Referral.referrer_user_id)
            .having(cnt > score)
            .subquery()
        )
        res = await self.session.execute(select(func.count()).select_from(sub))
        return int(res.scalar_one() or 0)
