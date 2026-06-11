from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserAchievement
from db.repositories.base import BaseRepo


class UserAchievementRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_codes(self, user_id: int) -> set[str]:
        res = await self.session.execute(
            select(UserAchievement.code).where(UserAchievement.user_id == user_id)
        )
        return {str(c) for c in res.scalars().all()}

    async def create(self, *, user_id: int, code: str, reward: float) -> UserAchievement:
        row = UserAchievement(user_id=user_id, code=code, reward=reward)
        self.session.add(row)
        await self.session.flush()
        return row
