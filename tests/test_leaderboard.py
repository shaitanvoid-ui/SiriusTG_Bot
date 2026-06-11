"""Лидерборд: сортировка, фильтр минимума, ранг, периоды."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from db.models import Referral
from services.leaderboard import LeaderboardService
from services.settings import SettingsService
from tests.helpers import create_user


def _svc(session):
    return LeaderboardService(session, SettingsService(session))


async def _add_confirmed_refs(session, referrer, n, *, when=None):
    when = when or datetime.now(tz=timezone.utc)
    for i in range(n):
        referred = await create_user(session, tg_id=referrer.tg_id * 1000 + i)
        session.add(
            Referral(
                referrer_user_id=referrer.id,
                referred_user_id=referred.id,
                is_confirmed=True,
                is_rewarded=True,
                reward_amount=3.0,
                confirmed_at=when,
            )
        )
    await session.flush()


async def test_top_orders_and_filters_min(session):
    a = await create_user(session, tg_id=999000701)
    b = await create_user(session, tg_id=999000702)
    c = await create_user(session, tg_id=999000703)
    await _add_confirmed_refs(session, a, 12)
    await _add_confirmed_refs(session, b, 15)
    await _add_confirmed_refs(session, c, 5)  # ниже минимума 10
    await session.commit()

    rows = await _svc(session).top("all")
    tg_ids = [r.tg_id for r in rows]
    assert tg_ids[0] == 999000702  # у b больше
    assert tg_ids[1] == 999000701
    assert 999000703 not in tg_ids  # отфильтрован минимумом
    assert rows[0].rank == 1 and rows[1].rank == 2


async def test_rank_of(session):
    a = await create_user(session, tg_id=999000711)
    b = await create_user(session, tg_id=999000712)
    await _add_confirmed_refs(session, a, 20)
    await _add_confirmed_refs(session, b, 11)
    await session.commit()

    svc = _svc(session)
    assert await svc.rank_of(a.id, "all") == (1, 20)
    assert await svc.rank_of(b.id, "all") == (2, 11)


async def test_rank_none_below_min(session):
    a = await create_user(session, tg_id=999000721)
    await _add_confirmed_refs(session, a, 5)
    await session.commit()
    rank, score = await _svc(session).rank_of(a.id, "all")
    assert rank is None
    assert score == 5


async def test_week_period_excludes_old(session):
    a = await create_user(session, tg_id=999000731)
    old = datetime.now(tz=timezone.utc) - timedelta(days=30)
    await _add_confirmed_refs(session, a, 12, when=old)
    await session.commit()

    rows_all = await _svc(session).top("all")
    rows_week = await _svc(session).top("week")
    assert any(r.tg_id == 999000731 for r in rows_all)
    assert all(r.tg_id != 999000731 for r in rows_week)  # старые — не в неделе
