from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import utcnow
from db.models import UserbotSession
from db.repositories.base import BaseRepo


class UserbotSessionRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_phone(self, phone: str) -> UserbotSession | None:
        res = await self.session.execute(
            select(UserbotSession).where(UserbotSession.phone == phone)
        )
        return res.scalar_one_or_none()

    async def get_active(self) -> UserbotSession | None:
        """Первая активная сессия (main). Backup-выбор — на Этапе 7."""
        res = await self.session.execute(
            select(UserbotSession)
            .where(UserbotSession.is_active.is_(True))
            .order_by(UserbotSession.id)
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def upsert(
        self, *, phone: str, session_enc: str, label: str | None = None
    ) -> None:
        stmt = sqlite_insert(UserbotSession).values(
            phone=phone,
            session_enc=session_enc,
            is_active=True,
            label=label,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["phone"],
            set_={"session_enc": session_enc, "is_active": True, "updated_at": utcnow()},
        )
        await self.session.execute(stmt)
