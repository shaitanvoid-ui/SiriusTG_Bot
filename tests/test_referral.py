"""Регрессии Этапа 3: рефералы и идемпотентность finalize_subs_passed."""

from __future__ import annotations

from bot.handlers.flow import finalize_subs_passed
from db.base import utcnow
from db.models import ReferralSource
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
