from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import utcnow
from db.models import Promo
from db.repositories.base import BaseRepo


class PromoRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, promo_id: int) -> Promo | None:
        res = await self.session.execute(select(Promo).where(Promo.id == promo_id))
        return res.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Promo | None:
        res = await self.session.execute(select(Promo).where(Promo.code == code))
        return res.scalar_one_or_none()

    async def list_all(self, *, limit: int = 50, offset: int = 0) -> list[Promo]:
        res = await self.session.execute(
            select(Promo)
            .order_by(Promo.is_active.desc(), Promo.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(res.scalars().all())

    async def count_all(self) -> int:
        res = await self.session.execute(select(func.count(Promo.id)))
        return int(res.scalar_one() or 0)

    async def create(
        self,
        *,
        code: str,
        reward: float,
        max_activations: int,
        expires_at: datetime | None,
        is_honeypot: bool,
        description: str | None,
    ) -> Promo:
        promo = Promo(
            code=code,
            reward=reward,
            max_activations=max_activations,
            expires_at=expires_at,
            is_honeypot=is_honeypot,
            description=description,
            is_active=True,
        )
        self.session.add(promo)
        await self.session.flush()
        return promo

    async def set_active(self, promo_id: int, is_active: bool) -> None:
        await self.session.execute(
            update(Promo).where(Promo.id == promo_id).values(is_active=is_active)
        )

    async def inc_used(self, promo_id: int, delta: int = 1) -> None:
        await self.session.execute(
            update(Promo)
            .where(Promo.id == promo_id)
            .values(used_count=Promo.used_count + delta)
        )

    async def try_reserve_use(
        self, promo_id: int, *, at: datetime | None = None
    ) -> bool:
        """Атомарно занимает одну непросроченную активацию."""
        checked_at = at or utcnow()
        result = await self.session.execute(
            update(Promo)
            .where(
                Promo.id == promo_id,
                Promo.is_active.is_(True),
                or_(Promo.expires_at.is_(None), Promo.expires_at > checked_at),
                or_(
                    Promo.max_activations == 0,
                    Promo.used_count < Promo.max_activations,
                ),
            )
            .values(
                used_count=Promo.used_count + 1,
                is_active=case(
                    (
                        (Promo.max_activations > 0)
                        & (Promo.used_count + 1 >= Promo.max_activations),
                        False,
                    ),
                    else_=Promo.is_active,
                ),
            )
            .execution_options(synchronize_session="fetch")
        )
        return bool(result.rowcount)

    async def release_use(self, promo_id: int) -> None:
        """Откатывает резерв, если пользователь уже активировал промокод."""
        await self.session.execute(
            update(Promo)
            .where(Promo.id == promo_id, Promo.used_count > 0)
            .values(
                is_active=case(
                    (
                        (Promo.max_activations > 0)
                        & (Promo.used_count >= Promo.max_activations),
                        True,
                    ),
                    else_=Promo.is_active,
                ),
                used_count=Promo.used_count - 1,
            )
            .execution_options(synchronize_session="fetch")
        )

    async def delete(self, promo_id: int) -> bool:
        res = await self.session.execute(delete(Promo).where(Promo.id == promo_id))
        return (res.rowcount or 0) > 0
