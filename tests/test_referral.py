"""Регрессии Этапа 3: рефералы и идемпотентность finalize_subs_passed."""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from bot.handlers.flow import finalize_subs_passed
from db.base import utcnow
from db.models import Referral, ReferralSource
from db.repositories.user import UserRepo
from services.referral import ReferralService
from services.settings import SettingsService
from tests.helpers import create_user


async def test_self_referral_rejected(session):
    user = await create_user(session, tg_id=999000040)
    svc = ReferralService(session, SettingsService(session))
    res = await svc.try_attach_referrer(user=user, referrer_tg_id=user.tg_id)
    assert res.attached is False
    assert res.reason == "self"


async def test_finalize_subs_passed_idempotent(session):
    user = await create_user(session, tg_id=999000041)
    user.subs_passed_at = utcnow()
    await session.flush()
    res = await finalize_subs_passed(session=session, user=user)
    assert res is None


async def test_attach_confirm_reward_and_idempotency(session):
    referrer = await create_user(session, tg_id=999000042)
    referred = await create_user(session, tg_id=999000043)
    svc = ReferralService(session, SettingsService(session))

    attach = await svc.try_attach_referrer(
        user=referred, referrer_tg_id=referrer.tg_id, source=ReferralSource.DIRECT
    )
    assert attach.attached is True

    event = await svc.on_user_passed_subs(user=referred)
    assert event is not None
    assert event.amount == 3.0

    # повторное подтверждение — без эффекта
    again = await svc.on_user_passed_subs(user=referred)
    assert again is None

    await session.refresh(referrer)
    assert round(referrer.balance, 2) == 3.0
    assert referrer.confirmed_ref_count == 1


async def test_lost_subs_rolls_back_reward(session):
    referrer = await create_user(session, tg_id=999000044)
    referred = await create_user(session, tg_id=999000045)
    svc = ReferralService(session, SettingsService(session))

    await svc.try_attach_referrer(user=referred, referrer_tg_id=referrer.tg_id)
    await svc.on_user_passed_subs(user=referred)

    rollback = await svc.on_user_lost_subs(user=referred)
    assert rollback is not None
    assert rollback.amount == 3.0

    await session.refresh(referrer)
    assert round(referrer.balance, 2) == 0.0
    assert referrer.confirmed_ref_count == 0


async def test_parallel_attach_respects_daily_limit(session, session_factory):
    referrer = await create_user(session, tg_id=999000046)
    referred_one = await create_user(session, tg_id=999000047)
    referred_two = await create_user(session, tg_id=999000048)
    referrer_id = referrer.id
    referred_ids = [referred_one.id, referred_two.id]
    await SettingsService(session).set("ref.daily_limit", 1)
    await session.commit()

    async def attach(referred_id: int):
        async with session_factory() as worker_session:
            referred = await UserRepo(worker_session).get_by_id(referred_id)
            assert referred is not None
            result = await ReferralService(
                worker_session, SettingsService(worker_session)
            ).try_attach_referrer(
                user=referred,
                referrer_tg_id=999000046,
            )
            await worker_session.commit()
            return result

    results = await asyncio.gather(*(attach(user_id) for user_id in referred_ids))
    assert sorted((result.attached, result.reason) for result in results) == [
        (False, "limit"),
        (True, "ok"),
    ]

    async with session_factory() as check_session:
        referral_count = await check_session.scalar(
            select(func.count(Referral.id)).where(
                Referral.referrer_user_id == referrer_id
            )
        )
        fresh_referrer = await UserRepo(check_session).get_by_id(referrer_id)
        assert referral_count == 1
        assert fresh_referrer is not None and fresh_referrer.ref_count == 1
