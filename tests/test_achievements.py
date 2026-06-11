"""Достижения: начисление по порогу, идемпотентность, метрики, выключение."""

from __future__ import annotations

from datetime import datetime, timezone

from db.models import ClickerDay
from db.repositories.user import UserRepo
from services.achievements import AchievementsService
from services.settings import SettingsService
from tests.helpers import create_user


def _svc(session):
    return AchievementsService(session, SettingsService(session))


async def test_confirmed_refs_achievement_awarded(session):
    user = await create_user(session, tg_id=999000651, balance=0.0, confirmed_ref_count=10)
    awarded = await _svc(session).sync(user)
    assert "ref10" in {a.code for a in awarded}
    fresh = await UserRepo(session).get_by_id(user.id)
    assert round(fresh.balance, 2) == 5.0  # дефолтная награда ref10


async def test_sync_is_idempotent(session):
    user = await create_user(session, tg_id=999000652, balance=0.0, confirmed_ref_count=10)
    await _svc(session).sync(user)
    bal1 = (await UserRepo(session).get_by_id(user.id)).balance
    awarded2 = await _svc(session).sync(user)
    assert awarded2 == []
    bal2 = (await UserRepo(session).get_by_id(user.id)).balance
    assert round(bal1, 2) == round(bal2, 2)


async def test_locked_until_threshold(session):
    user = await create_user(session, tg_id=999000653, confirmed_ref_count=9)
    awarded = await _svc(session).sync(user)
    assert all(a.code != "ref10" for a in awarded)
    views = await _svc(session).list_for_user(user)
    ref10 = next(v for v in views if v.code == "ref10")
    assert ref10.unlocked is False
    assert ref10.current == 9


async def test_clicks_total_metric(session):
    user = await create_user(session, tg_id=999000654)
    today = datetime.now(tz=timezone.utc).date()
    session.add(ClickerDay(user_id=user.id, day=today, clicks=500, earned=50.0))
    await session.commit()
    awarded = await _svc(session).sync(user)
    assert any(a.code == "click500" for a in awarded)


async def test_disabled_no_award(session):
    await SettingsService(session).set("achievements.enabled", False)
    await session.commit()
    user = await create_user(session, tg_id=999000655, confirmed_ref_count=100)
    awarded = await _svc(session).sync(user)
    assert awarded == []
