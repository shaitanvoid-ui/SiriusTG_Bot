from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import PromoActivation
from db.repositories.base import BaseRepo


class PromoActivationRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, promo_id: int, user_id: int) -> PromoActivation | None:
        res = await self.session.execute(
            select(PromoActivation).where(
                PromoActivation.promo_id == promo_id,
                PromoActivation.user_id == user_id,
            )
        )
        return res.scalar_one_or_none()

    async def create(
        self,
        *,
        promo_id: int,
        user_id: int,
        reward: float,
        is_honeypot_hit: bool,
    ) -> PromoActivation:
        row = PromoActivation(
            promo_id=promo_id,
            user_id=user_id,
            reward=reward,
            is_honeypot_hit=is_honeypot_hit,
        )
        self.session.add(row)
        await self.session.flush()
        return row
