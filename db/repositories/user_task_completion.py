from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserTaskCompletion
from db.repositories.base import BaseRepo


class UserTaskCompletionRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, user_id: int, sponsor_id: int) -> UserTaskCompletion | None:
        res = await self.session.execute(
            select(UserTaskCompletion).where(
                UserTaskCompletion.user_id == user_id,
                UserTaskCompletion.sponsor_id == sponsor_id,
            )
        )
        return res.scalar_one_or_none()

    async def get_by_id(self, completion_id: int) -> UserTaskCompletion | None:
        res = await self.session.execute(
            select(UserTaskCompletion).where(UserTaskCompletion.id == completion_id)
        )
        return res.scalar_one_or_none()

    async def list_sample(self, limit: int) -> list[UserTaskCompletion]:
        """Случайная выборка completion'ов для пере-проверки заданий."""
        res = await self.session.execute(
            select(UserTaskCompletion).order_by(func.random()).limit(limit)
        )
        return list(res.scalars().all())

    async def delete(self, completion_id: int) -> None:
        await self.session.execute(
            delete(UserTaskCompletion).where(UserTaskCompletion.id == completion_id)
        )

    async def count_for_user(self, user_id: int) -> int:
        """Сколько опц. заданий выполнил юзер. Для достижений."""
        res = await self.session.execute(
            select(func.count(UserTaskCompletion.id)).where(
                UserTaskCompletion.user_id == user_id
            )
        )
        return int(res.scalar_one() or 0)

    async def list_completed_ids(self, user_id: int) -> set[int]:
        res = await self.session.execute(
            select(UserTaskCompletion.sponsor_id).where(
                UserTaskCompletion.user_id == user_id
            )
        )
        return {int(r) for r in res.scalars().all()}

    async def create(
        self,
        *,
        user_id: int,
        sponsor_id: int,
        reward: float,
    ) -> UserTaskCompletion:
        row = UserTaskCompletion(
            user_id=user_id,
            sponsor_id=sponsor_id,
            reward=reward,
        )
        self.session.add(row)
        await self.session.flush()
        return row
