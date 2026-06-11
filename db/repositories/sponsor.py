from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Sponsor, SponsorKind
from db.repositories.base import BaseRepo


class SponsorRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, sponsor_id: int) -> Sponsor | None:
        res = await self.session.execute(select(Sponsor).where(Sponsor.id == sponsor_id))
        return res.scalar_one_or_none()

    async def list_required_active(self) -> list[Sponsor]:
        res = await self.session.execute(
            select(Sponsor)
            .where(Sponsor.is_required.is_(True), Sponsor.is_active.is_(True))
            .order_by(Sponsor.sort_order.asc(), Sponsor.id.asc())
        )
        return list(res.scalars().all())

    async def list_optional_active(self) -> list[Sponsor]:
        """Опциональные (не обязательные) активные спонсоры — для раздела «Задания»."""
        res = await self.session.execute(
            select(Sponsor)
            .where(Sponsor.is_required.is_(False), Sponsor.is_active.is_(True))
            .order_by(Sponsor.sort_order.asc(), Sponsor.id.asc())
        )
        return list(res.scalars().all())

    async def set_reward(self, sponsor_id: int, reward: float) -> None:
        await self.session.execute(
            update(Sponsor).where(Sponsor.id == sponsor_id).values(reward=reward)
        )

    async def set_subs_limit(self, sponsor_id: int, subs_limit: int) -> None:
        await self.session.execute(
            update(Sponsor).where(Sponsor.id == sponsor_id).values(subs_limit=subs_limit)
        )

    async def list_all(self) -> list[Sponsor]:
        res = await self.session.execute(
            select(Sponsor).order_by(Sponsor.is_active.desc(), Sponsor.sort_order.asc(), Sponsor.id.asc())
        )
        return list(res.scalars().all())

    async def get_by_chat_id(self, chat_id: int) -> Sponsor | None:
        res = await self.session.execute(select(Sponsor).where(Sponsor.chat_id == chat_id))
        return res.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Sponsor | None:
        res = await self.session.execute(select(Sponsor).where(Sponsor.username == username))
        return res.scalar_one_or_none()

    async def create(
        self,
        *,
        kind: SponsorKind,
        title: str,
        chat_id: int | None = None,
        username: str | None = None,
        invite_link: str | None = None,
        is_required: bool = True,
        is_active: bool = True,
        sort_order: int = 0,
        subs_limit: int = 0,
        reward: float = 0.0,
        is_honeypot: bool = False,
    ) -> Sponsor:
        sponsor = Sponsor(
            kind=kind.value if isinstance(kind, SponsorKind) else kind,
            title=title,
            chat_id=chat_id,
            username=username,
            invite_link=invite_link,
            is_required=is_required,
            is_active=is_active,
            sort_order=sort_order,
            subs_limit=subs_limit,
            reward=reward,
            is_honeypot=is_honeypot,
        )
        self.session.add(sponsor)
        await self.session.flush()
        return sponsor

    async def delete(self, sponsor_id: int) -> bool:
        res = await self.session.execute(delete(Sponsor).where(Sponsor.id == sponsor_id))
        return (res.rowcount or 0) > 0

    async def set_active(self, sponsor_id: int, is_active: bool) -> None:
        await self.session.execute(
            update(Sponsor).where(Sponsor.id == sponsor_id).values(is_active=is_active)
        )

    async def inc_counter(self, sponsor_id: int, delta: int = 1) -> None:
        await self.session.execute(
            update(Sponsor)
            .where(Sponsor.id == sponsor_id)
            .values(subs_counter=Sponsor.subs_counter + delta)
        )
