from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import LeaderboardPayout
from db.repositories.base import BaseRepo


class LeaderboardPayoutRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def exists_for_week(self, week_key: str) -> bool:
        res = await self.session.execute(
            select(func.count(LeaderboardPayout.id)).where(
                LeaderboardPayout.week_key == week_key
            )
        )
        return int(res.scalar_one() or 0) > 0

    async def create(
        self, *, week_key: str, user_id: int, rank: int, amount: float
    ) -> LeaderboardPayout:
        row = LeaderboardPayout(
            week_key=week_key, user_id=user_id, rank=rank, amount=amount
        )
        self.session.add(row)
        await self.session.flush()
        return row
