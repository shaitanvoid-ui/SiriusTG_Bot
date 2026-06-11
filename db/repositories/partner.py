"""Репозитории партнёрской системы (Этап 10)."""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import utcnow
from db.models import Partner, PartnerLink, PartnerPayout, PartnerStatus, PayoutStatus
from db.repositories.base import BaseRepo


class PartnerRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, partner_id: int) -> Partner | None:
        res = await self.session.execute(select(Partner).where(Partner.id == partner_id))
        return res.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> Partner | None:
        res = await self.session.execute(select(Partner).where(Partner.user_id == user_id))
        return res.scalar_one_or_none()

    async def create(self, user_id: int) -> Partner:
        partner = Partner(user_id=user_id, status=PartnerStatus.ACTIVE.value)
        self.session.add(partner)
        await self.session.flush()
        return partner

    async def list_all(self, limit: int = 50) -> list[Partner]:
        res = await self.session.execute(
            select(Partner)
            .where(Partner.is_deleted.is_(False))
            .order_by(Partner.total_earned.desc(), Partner.id.asc())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def set_status(self, partner_id: int, status: PartnerStatus) -> None:
        await self.session.execute(
            update(Partner).where(Partner.id == partner_id).values(status=status.value)
        )

    async def set_rates(
        self,
        partner_id: int,
        *,
        reward_per_user: float | None = ...,
        percent_sponsor: float | None = ...,
    ) -> None:
        values: dict = {}
        if reward_per_user is not ...:
            values["reward_per_user"] = reward_per_user
        if percent_sponsor is not ...:
            values["percent_sponsor"] = percent_sponsor
        if values:
            await self.session.execute(
                update(Partner).where(Partner.id == partner_id).values(**values)
            )

    async def add_earning(self, partner_id: int, amount: float) -> None:
        """Начисление партнёру: balance и total_earned растут вместе."""
        if amount <= 0:
            return
        await self.session.execute(
            update(Partner)
            .where(Partner.id == partner_id)
            .values(
                balance=func.round(Partner.balance + amount, 2),
                total_earned=func.round(Partner.total_earned + amount, 2),
            )
        )

    async def subtract_balance(self, partner_id: int, amount: float) -> bool:
        """Атомарно списывает amount с баланса. False — если средств не хватает."""
        res = await self.session.execute(
            update(Partner)
            .where(Partner.id == partner_id, Partner.balance >= amount)
            .values(balance=func.round(Partner.balance - amount, 2))
        )
        return (res.rowcount or 0) > 0

    async def refund_balance(self, partner_id: int, amount: float) -> None:
        """Возврат зарезервированной суммы (отклонённая выплата) — без total_earned."""
        if amount <= 0:
            return
        await self.session.execute(
            update(Partner)
            .where(Partner.id == partner_id)
            .values(balance=func.round(Partner.balance + amount, 2))
        )

    async def count_active(self) -> int:
        res = await self.session.execute(
            select(func.count(Partner.id)).where(
                Partner.status == PartnerStatus.ACTIVE.value,
                Partner.is_deleted.is_(False),
            )
        )
        return int(res.scalar_one() or 0)


class PartnerLinkRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, link_id: int) -> PartnerLink | None:
        res = await self.session.execute(
            select(PartnerLink).where(PartnerLink.id == link_id)
        )
        return res.scalar_one_or_none()

    async def get_by_code(self, code: str) -> PartnerLink | None:
        res = await self.session.execute(
            select(PartnerLink).where(
                PartnerLink.code == code, PartnerLink.is_deleted.is_(False)
            )
        )
        return res.scalar_one_or_none()

    async def create(self, *, partner_id: int, code: str, title: str) -> PartnerLink:
        link = PartnerLink(partner_id=partner_id, code=code, title=title)
        self.session.add(link)
        await self.session.flush()
        return link

    async def list_for_partner(self, partner_id: int) -> list[PartnerLink]:
        res = await self.session.execute(
            select(PartnerLink)
            .where(PartnerLink.partner_id == partner_id, PartnerLink.is_deleted.is_(False))
            .order_by(PartnerLink.id.asc())
        )
        return list(res.scalars().all())

    async def count_for_partner(self, partner_id: int) -> int:
        res = await self.session.execute(
            select(func.count(PartnerLink.id)).where(
                PartnerLink.partner_id == partner_id, PartnerLink.is_deleted.is_(False)
            )
        )
        return int(res.scalar_one() or 0)

    async def soft_delete(self, link_id: int) -> None:
        await self.session.execute(
            update(PartnerLink).where(PartnerLink.id == link_id).values(is_deleted=True)
        )

    async def inc_clicks(self, link_id: int) -> None:
        await self.session.execute(
            update(PartnerLink)
            .where(PartnerLink.id == link_id)
            .values(clicks=PartnerLink.clicks + 1)
        )

    async def inc_joins(self, link_id: int) -> None:
        await self.session.execute(
            update(PartnerLink)
            .where(PartnerLink.id == link_id)
            .values(joins=PartnerLink.joins + 1)
        )

    async def inc_passed(self, link_id: int) -> None:
        await self.session.execute(
            update(PartnerLink)
            .where(PartnerLink.id == link_id)
            .values(passed=PartnerLink.passed + 1)
        )

    async def totals_for_partner(self, partner_id: int) -> dict[str, int]:
        res = await self.session.execute(
            select(
                func.coalesce(func.sum(PartnerLink.clicks), 0),
                func.coalesce(func.sum(PartnerLink.joins), 0),
                func.coalesce(func.sum(PartnerLink.passed), 0),
            ).where(
                PartnerLink.partner_id == partner_id, PartnerLink.is_deleted.is_(False)
            )
        )
        clicks, joins, passed = res.one()
        return {"clicks": int(clicks), "joins": int(joins), "passed": int(passed)}


class PartnerPayoutRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, payout_id: int) -> PartnerPayout | None:
        res = await self.session.execute(
            select(PartnerPayout).where(PartnerPayout.id == payout_id)
        )
        return res.scalar_one_or_none()

    async def create(
        self,
        *,
        partner_id: int,
        amount_stars: float,
        rate_rub: float,
        method: str,
        requisites: str,
    ) -> PartnerPayout:
        payout = PartnerPayout(
            partner_id=partner_id,
            amount_stars=round(amount_stars, 2),
            rate_rub=round(rate_rub, 4),
            amount_rub=round(amount_stars * rate_rub, 2),
            method=method,
            requisites=requisites,
            status=PayoutStatus.PENDING.value,
        )
        self.session.add(payout)
        await self.session.flush()
        return payout

    async def get_pending_for_partner(self, partner_id: int) -> PartnerPayout | None:
        res = await self.session.execute(
            select(PartnerPayout).where(
                PartnerPayout.partner_id == partner_id,
                PartnerPayout.status == PayoutStatus.PENDING.value,
            )
        )
        return res.scalars().first()

    async def list_pending(self, limit: int = 50) -> list[PartnerPayout]:
        res = await self.session.execute(
            select(PartnerPayout)
            .where(PartnerPayout.status == PayoutStatus.PENDING.value)
            .order_by(PartnerPayout.id.asc())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def count_pending(self) -> int:
        res = await self.session.execute(
            select(func.count(PartnerPayout.id)).where(
                PartnerPayout.status == PayoutStatus.PENDING.value
            )
        )
        return int(res.scalar_one() or 0)

    async def list_for_partner(self, partner_id: int, limit: int = 10) -> list[PartnerPayout]:
        res = await self.session.execute(
            select(PartnerPayout)
            .where(PartnerPayout.partner_id == partner_id)
            .order_by(PartnerPayout.id.desc())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def set_status(
        self, payout_id: int, status: PayoutStatus, note: str | None = None
    ) -> None:
        await self.session.execute(
            update(PartnerPayout)
            .where(PartnerPayout.id == payout_id)
            .values(status=status.value, note=note, processed_at=utcnow())
        )
