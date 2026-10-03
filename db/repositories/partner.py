"""Репозитории партнёрской системы (Этап 10)."""

from __future__ import annotations

from sqlalchemy import func, literal, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import utcnow
from db.models import MoneyOperation, Partner, PartnerLink, PartnerPayout, PartnerStatus, PayoutStatus, User
from db.money import MAX_UNITS, from_units, settlement_units, to_units
from db.repositories.user import UserRepo
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
            values["reward_per_user_units"] = None if reward_per_user is None else to_units(reward_per_user)
        if percent_sponsor is not ...:
            values["percent_sponsor"] = percent_sponsor
        if values:
            await self.session.execute(
                update(Partner).where(Partner.id == partner_id).values(**values)
            )

    async def _change(self, partner_id: int, *, balance_delta: int = 0, reserved_delta: int = 0, earned_delta: int = 0, reason: str, reference: str | None = None, conditions=(), check_owner: bool = False) -> bool:
        conditions = list(conditions)
        if check_owner:
            conditions.append(select(User.id).where(User.id == Partner.user_id, *UserRepo.reward_conditions()).exists())
        if reference:
            conditions.append(~select(MoneyOperation.id).where(MoneyOperation.reference == reference).exists())
        old = (await self.session.execute(update(Partner).where(Partner.id == partner_id, *conditions)
            .values(balance_units=Partner.balance_units)
            .returning(Partner.balance_units, Partner.reserved_units, Partner.total_earned_units)
            .execution_options(synchronize_session=False))).one_or_none()
        if old is None:
            return False
        balance, reserved, earned = old[0]+balance_delta, old[1]+reserved_delta, old[2]+earned_delta
        if any(value < 0 or value > MAX_UNITS for value in (balance, reserved, earned)):
            raise ValueError("partner account outside integer storage bounds")
        await self.session.execute(update(Partner).where(Partner.id == partner_id).values(
            balance_units=balance, reserved_units=reserved, total_earned_units=earned
        ).execution_options(synchronize_session="fetch"))
        self.session.add(MoneyOperation(account_kind="partner", partner_id=partner_id, reason=reason, reference=reference,
            balance_delta_units=balance_delta, debt_delta_units=0, reserved_delta_units=reserved_delta,
            balance_after_units=balance, debt_after_units=0, reserved_after_units=reserved))
        await self.session.flush()
        return True

    async def add_earning(self, partner_id: int, amount, *, reason: str = "partner_credit", reference: str | None = None) -> bool:
        units = settlement_units(amount)
        if units <= 0:
            return False
        return await self._change(partner_id, balance_delta=units, earned_delta=units, reason=reason, reference=reference, check_owner=True,
            conditions=(Partner.is_deleted.is_(False), Partner.status == PartnerStatus.ACTIVE.value))

    async def subtract_balance(self, partner_id: int, amount) -> bool:
        units = settlement_units(amount)
        if units <= 0:
            return False
        return await self._change(partner_id, balance_delta=-units, reason="partner_debit", check_owner=True, conditions=(Partner.balance_units >= units,))

    async def reserve_payout_balance(self, partner_id: int, amount) -> bool:
        units = settlement_units(amount)
        if units <= 0:
            return False
        pending_exists = select(PartnerPayout.id).where(PartnerPayout.partner_id == partner_id, PartnerPayout.status == PayoutStatus.PENDING.value).exists()
        return await self._change(partner_id, balance_delta=-units, reserved_delta=units, reason="partner_payout_reserve", check_owner=True,
            conditions=(Partner.status == PartnerStatus.ACTIVE.value, Partner.is_deleted.is_(False), Partner.balance_units >= units, ~pending_exists))

    async def refund_balance(self, partner_id: int, amount, *, reference: str | None = None) -> bool:
        units = settlement_units(amount)
        if units <= 0:
            return False
        return await self._change(partner_id, balance_delta=units, reserved_delta=-units, reason="partner_payout_release", reference=reference,
            conditions=(Partner.reserved_units >= units,))

    async def consume_payout_reserve(self, partner_id: int, amount, *, reference: str) -> bool:
        units = settlement_units(amount)
        return await self._change(partner_id, reserved_delta=-units, reason="partner_payout_consume", reference=reference,
            conditions=(Partner.reserved_units >= units,))

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

    async def create_if_below_limit(
        self, *, partner_id: int, code: str, title: str, limit: int
    ) -> PartnerLink | None:
        """Вставляет ссылку, атомарно соблюдая лимит партнёра."""
        active_links = (
            select(func.count(PartnerLink.id))
            .where(
                PartnerLink.partner_id == partner_id,
                PartnerLink.is_deleted.is_(False),
            )
            .scalar_subquery()
        )
        stmt = (
            sqlite_insert(PartnerLink)
            .from_select(
                ["partner_id", "code", "title"],
                select(
                    literal(partner_id),
                    literal(code),
                    literal(title),
                ).where(active_links < max(0, limit)),
            )
            .on_conflict_do_nothing(index_elements=["code"])
            .returning(PartnerLink.id)
        )
        link_id = (await self.session.execute(stmt)).scalar_one_or_none()
        return await self.session.get(PartnerLink, link_id) if link_id else None

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
            amount_stars_units=settlement_units(amount_stars),
            rate_rub_units=to_units(rate_rub),
            amount_rub_units=settlement_units(from_units(settlement_units(amount_stars)) * from_units(to_units(rate_rub))),
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
    ) -> bool:
        """Переводит только pending-заявку; возвращает, кто выиграл гонку."""
        result = await self.session.execute(
            update(PartnerPayout)
            .where(
                PartnerPayout.id == payout_id,
                PartnerPayout.status == PayoutStatus.PENDING.value,
            )
            .values(status=status.value, note=note, processed_at=utcnow())
            .execution_options(synchronize_session="fetch")
        )
        return bool(result.rowcount)
