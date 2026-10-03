from __future__ import annotations

from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import WheelSpin
from db.repositories.base import BaseRepo
from db.money import to_units


class WheelSpinRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def count_free_today(self, user_id: int, day: date) -> int:
        res = await self.session.execute(
            select(func.count(WheelSpin.id)).where(
                WheelSpin.user_id == user_id,
                WheelSpin.day == day,
                WheelSpin.is_free.is_(True),
            )
        )
        return int(res.scalar_one() or 0)

    async def create(
        self,
        *,
        user_id: int,
        day: date,
        prize: float,
        cost: float,
        is_free: bool,
        free_slot: int | None = None,
    ) -> WheelSpin:
        row = WheelSpin(
            user_id=user_id,
            day=day,
            prize_units=to_units(prize),
            cost_units=to_units(cost),
            is_free=is_free,
            free_slot=free_slot,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def reserve_free(
        self,
        *,
        user_id: int,
        day: date,
        prize: float,
        limit: int,
    ) -> WheelSpin | None:
        """Атомарно занимает первый свободный дневной слот."""
        for slot in range(1, max(0, limit) + 1):
            stmt = (
                sqlite_insert(WheelSpin)
                .values(
                    user_id=user_id,
                    day=day,
                    prize_units=to_units(prize),
                    cost_units=0,
                    is_free=True,
                    free_slot=slot,
                )
                .on_conflict_do_nothing(
                    index_elements=["user_id", "day", "free_slot"]
                )
                .returning(WheelSpin.id)
            )
            spin_id = (await self.session.execute(stmt)).scalar_one_or_none()
            if spin_id is not None:
                return await self.session.get(WheelSpin, spin_id)
        return None

    async def reserve_paid(self, *, user_id: int, day: date, prize: float, cost: float,
                           request_token: str) -> WheelSpin | None:
        statement = sqlite_insert(WheelSpin).values(
            user_id=user_id, day=day, prize_units=to_units(prize), cost_units=to_units(cost), is_free=False, request_token=request_token,
        ).on_conflict_do_nothing(index_elements=["user_id", "request_token"]).returning(WheelSpin.id)
        spin_id = (await self.session.execute(statement)).scalar_one_or_none()
        return await self.session.get(WheelSpin, spin_id) if spin_id is not None else None

    async def release_unfunded_reservation(self, spin_id: int) -> None:
        # No money or outcome was committed for this transient reservation.
        await self.session.execute(delete(WheelSpin).where(WheelSpin.id == spin_id))
