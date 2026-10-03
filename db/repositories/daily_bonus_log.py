from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import DailyBonusLog
from db.repositories.base import BaseRepo
from db.money import to_units


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
            user_id=user_id, day=day, amount_units=to_units(amount), streak=streak, bio_ok=bio_ok
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_if_absent(
        self, *, user_id: int, day: date, amount: float, streak: int, bio_ok: bool
    ) -> bool:
        """Резервирует бонус идемпотентно, не ломая транзакцию конфликтом UQ."""
        stmt = (
            sqlite_insert(DailyBonusLog)
            .values(
                user_id=user_id,
                day=day,
                amount_units=to_units(amount),
                streak=streak,
                bio_ok=bio_ok,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "day"])
            .returning(DailyBonusLog.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None
