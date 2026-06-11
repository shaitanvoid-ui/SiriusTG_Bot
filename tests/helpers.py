"""Фабрики тестовых сущностей. Создают ORM-объекты напрямую и flush'ат."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Promo, Sponsor, SponsorKind, User


async def create_user(session: AsyncSession, *, tg_id: int, balance: float = 0.0, **kw: Any) -> User:
    user = User(tg_id=tg_id, balance=balance, **kw)
    session.add(user)
    await session.flush()
    return user


async def create_sponsor(
    session: AsyncSession,
    *,
    title: str = "Test",
    is_required: bool = False,
    is_active: bool = True,
    reward: float = 0.0,
    username: str | None = None,
    chat_id: int | None = None,
    subs_limit: int = 0,
    **kw: Any,
) -> Sponsor:
    sponsor = Sponsor(
        kind=SponsorKind.PUBLIC.value,
        title=title,
        is_required=is_required,
        is_active=is_active,
        reward=reward,
        username=username,
        chat_id=chat_id,
        subs_limit=subs_limit,
        **kw,
    )
    session.add(sponsor)
    await session.flush()
    return sponsor


async def create_promo(
    session: AsyncSession,
    *,
    code: str,
    reward: float = 1.0,
    max_activations: int = 0,
    is_honeypot: bool = False,
    is_active: bool = True,
    expires_at: datetime | None = None,
    **kw: Any,
) -> Promo:
    promo = Promo(
        code=code,
        reward=reward,
        max_activations=max_activations,
        is_honeypot=is_honeypot,
        is_active=is_active,
        expires_at=expires_at,
        **kw,
    )
    session.add(promo)
    await session.flush()
    return promo
