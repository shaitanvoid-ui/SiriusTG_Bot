from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ClickerDay
from db.money import to_units
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
        await self.session.execute(
            sqlite_insert(ClickerDay)
            .values(user_id=user_id, day=day)
            .on_conflict_do_nothing(index_elements=["user_id", "day"])
        )
        row = await self.get(user_id, day)
        if row is None:  # pragma: no cover - INSERT/SELECT инвариант
            raise RuntimeError("clicker day row was not created")
        return row

    async def ensure_captcha_threshold(self, row_id: int, threshold: int) -> None:
        await self.session.execute(
            update(ClickerDay)
            .where(ClickerDay.id == row_id, ClickerDay.captcha_threshold <= 0)
            .values(captcha_threshold=threshold)
            .execution_options(synchronize_session="fetch")
        )

    async def try_click(
        self,
        *,
        row_id: int,
        now_ms: int,
        min_interval_ms: int,
        daily_limit: int,
        reward: float,
    ) -> bool:
        """Проверяет ограничения и записывает клик одним UPDATE."""
        result = await self.session.execute(
            update(ClickerDay)
            .where(
                ClickerDay.id == row_id,
                ClickerDay.captcha_token.is_(None),
                ClickerDay.clicks < daily_limit,
                or_(
                    ClickerDay.last_click_ms <= 0,
                    ClickerDay.last_click_ms <= now_ms - min_interval_ms,
                ),
            )
            .values(
                clicks=ClickerDay.clicks + 1,
                earned_units=ClickerDay.earned_units + to_units(reward),
                last_click_ms=now_ms,
                since_captcha=ClickerDay.since_captcha + 1,
            )
            .execution_options(synchronize_session="fetch")
        )
        return bool(result.rowcount)
