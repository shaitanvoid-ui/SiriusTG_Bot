"""Промокоды: ok / already_used / not_found / honeypot / inactive / exhausted."""

from __future__ import annotations

from datetime import timedelta

from db.base import utcnow
from db.repositories.promo import PromoRepo
from db.repositories.user import UserRepo
from services.promo import PromoService, PromoStatus
from services.settings import SettingsService
from tests.helpers import create_promo, create_user


async def test_redeem_ok_then_already_used(session):
    user = await create_user(session, tg_id=999000010)
    await create_promo(session, code="WELCOME", reward=2.0)
    svc = PromoService(session, SettingsService(session))

    r = await svc.redeem(user=user, raw_code="welcome")  # нормализация регистра
    assert r.status == PromoStatus.OK
    assert r.reward == 2.0
    assert r.balance == 2.0

    r2 = await svc.redeem(user=user, raw_code="WELCOME")
    assert r2.status == PromoStatus.ALREADY_USED


async def test_not_found(session):
    user = await create_user(session, tg_id=999000011)
    svc = PromoService(session, SettingsService(session))
    r = await svc.redeem(user=user, raw_code="DOESNOTEXIST")
    assert r.status == PromoStatus.NOT_FOUND


async def test_honeypot_shadows_user_without_hard_ban(session):
    user = await create_user(session, tg_id=999000012)
    await create_promo(session, code="TRAP", reward=5.0, is_honeypot=True)
    svc = PromoService(session, SettingsService(session))

    r = await svc.redeem(user=user, raw_code="TRAP")
    assert r.status == PromoStatus.HONEYPOT_BANNED

    fresh = await UserRepo(session).get_by_id(user.id)
    assert fresh.is_shadow_banned is True
    assert fresh.is_banned is False
    assert fresh.balance == 0.0


async def test_inactive(session):
    user = await create_user(session, tg_id=999000013)
    await create_promo(session, code="OFF", reward=1.0, is_active=False)
    svc = PromoService(session, SettingsService(session))
    r = await svc.redeem(user=user, raw_code="OFF")
    assert r.status == PromoStatus.INACTIVE


async def test_exhausted_branch(session):
    """Активен, но used_count уже == max_activations → EXHAUSTED."""
    user = await create_user(session, tg_id=999000016)
    promo = await create_promo(session, code="FULL", reward=1.0, max_activations=1)
    promo.used_count = 1
    await session.flush()

    svc = PromoService(session, SettingsService(session))
    r = await svc.redeem(user=user, raw_code="FULL")
    assert r.status == PromoStatus.EXHAUSTED


async def test_second_user_after_exhaustion_gets_inactive(session):
    """Один юзер исчерпывает промо (max=1 → auto-deactivate), второй видит INACTIVE."""
    u1 = await create_user(session, tg_id=999000014)
    u2 = await create_user(session, tg_id=999000015)
    await create_promo(session, code="ONE", reward=1.0, max_activations=1)
    svc = PromoService(session, SettingsService(session))

    assert (await svc.redeem(user=u1, raw_code="ONE")).status == PromoStatus.OK
    # после первой активации промо деактивировано → даже автор видит INACTIVE
    assert (await svc.redeem(user=u1, raw_code="ONE")).status == PromoStatus.INACTIVE
    assert (await svc.redeem(user=u2, raw_code="ONE")).status == PromoStatus.INACTIVE


async def test_already_used_while_promo_stays_active(session):
    """max=2 → промо остаётся активным, повтор тем же юзером даёт ALREADY_USED."""
    user = await create_user(session, tg_id=999000017)
    await create_promo(session, code="MULTI", reward=1.0, max_activations=2)
    svc = PromoService(session, SettingsService(session))

    assert (await svc.redeem(user=user, raw_code="MULTI")).status == PromoStatus.OK
    assert (await svc.redeem(user=user, raw_code="MULTI")).status == PromoStatus.ALREADY_USED


async def test_atomic_reservation_rejects_expired_active_promo(session):
    promo = await create_promo(session, code="JUSTEXPIRED", reward=1.0)
    promo.expires_at = utcnow() - timedelta(seconds=1)
    await session.flush()

    assert not await PromoRepo(session).try_reserve_use(promo.id)
    await session.refresh(promo)
    assert promo.used_count == 0
    assert promo.is_active is True
