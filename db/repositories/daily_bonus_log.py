from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import DailyBonusLog
from db.repositories.base import BaseRepo


class DailyBonusLogRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, user_id: int, day: date) -> DailyBonusLog | None:
        res = await self.session.execute(
            select(DailyBonusLog).where(
                DailyBonusLog.user_id == user_id,
                DailyBonusLog.day == day,
            )
        )
        return res.scalar_one_or_none()

    async def create(
        self, *, user_id: int, day: date, amount: float, streak: int, bio_ok: bool
    ) -> DailyBonusLog:
        row = DailyBonusLog(
            user_id=user_id, day=day, amount=amount, streak=streak, bio_ok=bio_ok
        )
        self.session.add(row)
        await self.session.flush()
        return row
