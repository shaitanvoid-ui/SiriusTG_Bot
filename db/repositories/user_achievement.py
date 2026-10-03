from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserAchievement
from db.repositories.base import BaseRepo
from db.money import to_units


class UserAchievementRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_codes(self, user_id: int) -> set[str]:
        res = await self.session.execute(
            select(UserAchievement.code).where(UserAchievement.user_id == user_id)
        )
        return {str(c) for c in res.scalars().all()}

    async def create(self, *, user_id: int, code: str, reward: float) -> UserAchievement:
        row = UserAchievement(user_id=user_id, code=code, reward_units=to_units(reward))
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_if_absent(self, *, user_id: int, code: str, reward: float) -> bool:
        stmt = (
            sqlite_insert(UserAchievement)
            .values(user_id=user_id, code=code, reward_units=to_units(reward))
            .on_conflict_do_nothing(index_elements=["user_id", "code"])
            .returning(UserAchievement.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None
