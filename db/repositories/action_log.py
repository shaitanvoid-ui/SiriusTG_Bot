from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ActionLog
from db.repositories.base import BaseRepo


class ActionLogRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def log(
        self,
        *,
        user_tg_id: int | None,
        action: str,
        payload: Any = None,
    ) -> None:
        self.session.add(
            ActionLog(
                user_tg_id=user_tg_id,
                action=action,
                payload=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            )
        )

    async def list_recent_for_user(self, tg_id: int, limit: int = 5) -> list[ActionLog]:
        """Последние действия юзера — для админ-карточки (Этап 9)."""
        res = await self.session.execute(
            select(ActionLog)
            .where(ActionLog.user_tg_id == tg_id)
            .order_by(ActionLog.created_at.desc(), ActionLog.id.desc())
            .limit(limit)
        )
        return list(res.scalars().all())

    # ---------- история операций (Этап 11) ----------

    async def list_page_for_user(
        self,
        tg_id: int,
        actions: tuple[str, ...],
        *,
        offset: int,
        limit: int,
    ) -> list[ActionLog]:
        """Страница денежных операций юзера (новые сверху)."""
        res = await self.session.execute(
            select(ActionLog)
            .where(ActionLog.user_tg_id == tg_id, ActionLog.action.in_(actions))
            .order_by(ActionLog.created_at.desc(), ActionLog.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(res.scalars().all())

    async def count_for_user(self, tg_id: int, actions: tuple[str, ...]) -> int:
        res = await self.session.execute(
            select(func.count(ActionLog.id)).where(
                ActionLog.user_tg_id == tg_id, ActionLog.action.in_(actions)
            )
        )
        return int(res.scalar_one() or 0)
