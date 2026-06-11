"""Ежедневный бонус + streak: ступени, сброс, идемпотентность, bio-гейт."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from db.models import DailyBonusLog
from services.bonus import BioOutcome, BonusService, BonusStatus, _today
from services.settings import SettingsService
from tests.helpers import create_user


def _bio_ok():
    async def _c() -> BioOutcome:
        return BioOutcome.OK
    return _c


def _bio_missing():
    async def _c() -> BioOutcome:
        return BioOutcome.MISSING
    return _c


def _bio_unavailable():
    async def _c() -> BioOutcome:
        return BioOutcome.UNAVAILABLE
    return _c


def _bio_explode():
    async def _c() -> BioOutcome:
        raise AssertionError("bio_checker не должен вызываться при bio_required=False")
    return _c


def _svc(session):
    return BonusService(session, SettingsService(session))


async def test_first_claim_ok(session):
    user = await create_user(session, tg_id=999000201, balance=0.0)
    res = await _svc(session).claim(user, bio_checker=_bio_ok())
    assert res.status == BonusStatus.OK
    assert res.streak == 1
    assert res.amount == 0.5
    assert round(user.balance, 2) == 0.5
    assert user.last_bonus_date == _today()


async def test_second_claim_same_day_is_already(session):
    user = await create_user(session, tg_id=999000202, balance=0.0)
    await _svc(session).claim(user, bio_checker=_bio_ok())
    res = await _svc(session).claim(user, bio_checker=_bio_ok())
    assert res.status == BonusStatus.ALREADY
    assert round(user.balance, 2) == 0.5  # повторно не начислили


async def test_streak_progression_tiers(session):
    # streak 2 → завтра станет 3 → ступень 0.7
    user = await create_user(
        session, tg_id=999000203, balance=0.0,
        bonus_streak=2, last_bonus_date=_today() - timedelta(days=1),
    )
    res = await _svc(session).claim(user, bio_checker=_bio_ok())
    assert res.status == BonusStatus.OK
    assert res.streak == 3
    assert res.amount == 0.7


async def test_streak_reaches_week(session):
    user = await create_user(
        session, tg_id=999000204, balance=0.0,
        bonus_streak=6, last_bonus_date=_today() - timedelta(days=1),
    )
    res = await _svc(session).claim(user, bio_checker=_bio_ok())
    assert res.streak == 7
    assert res.amount == 1.0


async def test_gap_resets_streak(session):
    user = await create_user(
        session, tg_id=999000205, balance=0.0,
        bonus_streak=10, last_bonus_date=_today() - timedelta(days=2),
    )
    res = await _svc(session).claim(user, bio_checker=_bio_ok())
    assert res.status == BonusStatus.OK
    assert res.streak == 1
    assert res.amount == 0.5


async def test_bio_missing_blocks_and_keeps_state(session):
    user = await create_user(session, tg_id=999000206, balance=3.0, bonus_streak=4)
    res = await _svc(session).claim(user, bio_checker=_bio_missing())
    assert res.status == BonusStatus.BIO_MISSING
    assert round(user.balance, 2) == 3.0
    assert user.bonus_streak == 4
    assert user.last_bonus_date is None


async def test_bio_unavailable_does_not_burn_attempt(session):
    user = await create_user(session, tg_id=999000207, balance=0.0)
    res = await _svc(session).claim(user, bio_checker=_bio_unavailable())
    assert res.status == BonusStatus.UNAVAILABLE
    assert round(user.balance, 2) == 0.0
    assert user.last_bonus_date is None


async def test_bio_not_required_grants_without_check(session):
    await SettingsService(session).set("bonus.bio_required", False)
    await session.commit()
    user = await create_user(session, tg_id=999000208, balance=0.0)
    res = await _svc(session).claim(user, bio_checker=_bio_explode())
    assert res.status == BonusStatus.OK
    assert res.amount == 0.5


async def test_claim_writes_log_row(session):
    user = await create_user(session, tg_id=999000209, balance=0.0)
    await _svc(session).claim(user, bio_checker=_bio_ok())
    rows = await session.execute(
        select(DailyBonusLog).where(DailyBonusLog.user_id == user.id)
    )
    log = rows.scalars().first()
    assert log is not None
    assert log.amount == 0.5
    assert log.streak == 1
    assert log.bio_ok is True
