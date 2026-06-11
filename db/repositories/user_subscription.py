from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import utcnow
from db.models import SubscriptionStatus, UserSubscription
from db.repositories.base import BaseRepo


class UserSubscriptionRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def upsert_status(
        self,
        *,
        user_id: int,
        sponsor_id: int,
        status: SubscriptionStatus,
    ) -> None:
        stmt = sqlite_insert(UserSubscription).values(
            user_id=user_id,
            sponsor_id=sponsor_id,
            status=status.value,
            last_checked_at=utcnow(),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "sponsor_id"],
            set_={
                "status": status.value,
                "last_checked_at": utcnow(),
                "updated_at": utcnow(),
            },
        )
        await self.session.execute(stmt)

    async def list_for_user(self, user_id: int) -> list[UserSubscription]:
        res = await self.session.execute(
            select(UserSubscription).where(UserSubscription.user_id == user_id)
        )
        return list(res.scalars().all())
