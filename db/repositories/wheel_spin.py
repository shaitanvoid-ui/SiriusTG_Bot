from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import WheelSpin
from db.repositories.base import BaseRepo


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
        self, *, user_id: int, day: date, prize: float, cost: float, is_free: bool
    ) -> WheelSpin:
        row = WheelSpin(
            user_id=user_id, day=day, prize=prize, cost=cost, is_free=is_free
        )
        self.session.add(row)
        await self.session.flush()
        return row
