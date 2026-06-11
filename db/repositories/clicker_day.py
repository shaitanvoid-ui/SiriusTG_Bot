from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ClickerDay
from db.repositories.base import BaseRepo


class ClickerDayRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def total_clicks(self, user_id: int) -> int:
        """Сумма тапов за всё время. Для достижений-кликера."""
        res = await self.session.execute(
            select(func.coalesce(func.sum(ClickerDay.clicks), 0)).where(
                ClickerDay.user_id == user_id
            )
        )
        return int(res.scalar_one() or 0)

    async def get(self, user_id: int, day: date) -> ClickerDay | None:
        res = await self.session.execute(
            select(ClickerDay).where(
                ClickerDay.user_id == user_id,
                ClickerDay.day == day,
            )
        )
        return res.scalar_one_or_none()

    async def get_or_create(self, user_id: int, day: date) -> ClickerDay:
        row = await self.get(user_id, day)
        if row is not None:
            return row
        row = ClickerDay(user_id=user_id, day=day)
        self.session.add(row)
        await self.session.flush()
        return row
