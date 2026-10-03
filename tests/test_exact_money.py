"""Integer accounting regressions; no network, real account or production DB."""
from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text

from db.models import MoneyOperation, Referral, Review, ReviewStatus
from db.money import from_units, settlement_units, to_units
from db.repositories.partner import PartnerRepo
from db.repositories.user import UserRepo
from services.achievements import AchievementsService
from services.bonus import BonusService, BonusStatus
from services.clicker import ClickerService, ClickStatus
from services.partner import PartnerService
from services.promo import PromoService, PromoStatus
from services.referral import ReferralService
from services.reviews import ReviewService
from services.settings import SettingsService
from services.tasks import TasksService, TaskStatus
from services.wheel import SpinStatus, WheelService
from tests.helpers import create_user


def test_conversion_has_explicit_decimal_half_even_and_range():
    assert to_units("0.01255") == 126
    assert to_units("0.01245") == 124
    assert to_units(0.30000000000000004) == 3000
    assert settlement_units("0.015") == 200
    assert settlement_units("0.025") == 200
    assert from_units(12345) == Decimal("1.2345")
    for value in ["NaN", "Infinity", "-Infinity", "1e30"]:
        with pytest.raises(ValueError):
            to_units(value)


async def test_tenths_credit_and_debt_are_exact_and_journal_reconciles(session):
    user = await create_user(session, tg_id=9917001, debt=0.3)
    repo = UserRepo(session)
    for _ in range(10):
        assert await repo.add_balance(user.id, "0.1", reason="test_credit")
    await session.refresh(user)
    assert (user.balance_units, user.debt_units, user.reserved_units) == (7000, 0, 0)
    assert user.balance == Decimal("0.7")
    sums = (await session.execute(select(
        func.sum(MoneyOperation.balance_delta_units), func.sum(MoneyOperation.debt_delta_units)
    ).where(MoneyOperation.user_id == user.id))).one()
    assert sums == (7000, -3000)
    storage = (await session.execute(text("SELECT typeof(balance_units),typeof(debt_units) FROM users WHERE id=:id"), {"id": user.id})).one()
    assert storage == ("integer", "integer")


async def test_reserve_reference_has_one_terminal_operation_and_owner(session):
    user = await create_user(session, tg_id=9917002, balance=10)
    other = await create_user(session, tg_id=9917003, balance=10)
    repo = UserRepo(session)
    assert await repo.reserve(user.id, 50_000, reference="gift:a")
    assert not await repo.reserve(user.id, 50_000, reference="gift:a")
    assert not await repo.release_reserve(other.id, 50_000, reference="gift:a")
    assert not await repo.release_reserve(user.id, 40_000, reference="gift:a")
    assert await repo.release_reserve(user.id, 50_000, reference="gift:a")
    assert not await repo.release_reserve(user.id, 50_000, reference="gift:a")
    assert not await repo.consume_reserve(user.id, 50_000, reference="gift:a")
    await session.refresh(user)
    assert (user.balance_units, user.reserved_units) == (100_000, 0)
    assert await session.scalar(select(func.count()).select_from(MoneyOperation)) == 2


async def test_reserve_refund_pays_debt_and_reversal_can_apply_when_blocked(session):
    user = await create_user(session, tg_id=9917004, balance=10)
    repo = UserRepo(session)
    assert await repo.reserve(user.id, 50_000, reference="gift:b")
    await repo.set_shadow_banned(user.id, True)
    assert await repo.subtract_with_debt(user.id, 12, reason="reversal") == Decimal("7")
    assert await repo.release_reserve(user.id, 50_000, reference="gift:b")
    await session.refresh(user)
    assert (user.balance_units, user.debt_units, user.reserved_units) == (0, 20_000, 0)


async def test_concurrent_same_reserve_serializes_and_journals_once(session, session_factory):
    user = await create_user(session, tg_id=9917005, balance=10)
    user_id = user.id
    await session.commit()

    async def attempt():
        async with session_factory() as worker:
            won = await UserRepo(worker).reserve(user_id, 50_000, reference="gift:c")
            await worker.commit()
            return won

    assert sorted(await asyncio.gather(attempt(), attempt())) == [False, True]
    await session.refresh(user)
    assert (user.balance_units, user.reserved_units) == (50_000, 50_000)
    assert await session.scalar(select(func.count()).select_from(MoneyOperation)) == 1


async def test_reserve_finish_race_can_only_release_or_consume(session, session_factory):
    user = await create_user(session, tg_id=9917006, balance=10)
    user_id = user.id
    assert await UserRepo(session).reserve(user_id, 50_000, reference="gift:d")
    await session.commit()

    async def finish(consume):
        async with session_factory() as worker:
            repo = UserRepo(worker)
            method = repo.consume_reserve if consume else repo.release_reserve
            won = await method(user_id, 50_000, reference="gift:d")
            await worker.commit()
            return won

    assert sorted(await asyncio.gather(finish(True), finish(False))) == [False, True]
    await session.refresh(user)
    assert user.reserved_units == 0
    assert user.balance_units in [50_000, 100_000]
    assert await session.scalar(select(func.count()).select_from(MoneyOperation)) == 2


@pytest.mark.parametrize("flag", ["is_banned", "is_shadow_banned", "is_deleted"])
async def test_all_reward_services_and_direct_repositories_reject_flags(session, flag):
    user = await create_user(session, tg_id=9917100, balance=10, confirmed_ref_count=100, **{flag: True})
    settings = SettingsService(session)
    repo = UserRepo(session)

    async def external_call_forbidden():
        raise AssertionError("blocked account must not call external gate")

    assert (await BonusService(session, settings).claim(user, bio_checker=external_call_forbidden)).status == BonusStatus.BLOCKED
    assert (await ClickerService(session, settings).click(user)).status == ClickStatus.BLOCKED
    assert (await WheelService(session, settings).spin(user, paid=False)).status == SpinStatus.BLOCKED
    assert (await WheelService(session, settings).spin(user, paid=True)).status == SpinStatus.BLOCKED
    assert (await TasksService(session, settings).claim(None, user=user, sponsor_id=999)).status == TaskStatus.BLOCKED
    assert (await PromoService(session, settings).redeem(user=user, raw_code="ANY")).status == PromoStatus.BLOCKED
    assert await AchievementsService(session, settings).sync(user) == []
    assert not await repo.add_balance(user.id, 2)
    assert not await repo.try_spend_balance(user.id, 1)
    assert not await repo.reserve(user.id, 10_000, reference="blocked")
    partner = await PartnerRepo(session).create(user.id)
    assert not await PartnerRepo(session).add_earning(partner.id, 1)
    await session.refresh(user)
    assert user.balance_units == 100_000
    assert user.bonus_streak == 0 and user.last_bonus_date is None
    assert await session.scalar(select(func.count()).select_from(MoneyOperation)) == 0


@pytest.mark.parametrize("blocked_role", ["referrer", "referred"])
async def test_referrals_require_both_users_to_be_allowed(session, blocked_role):
    referrer = await create_user(session, tg_id=9917201)
    referred = await create_user(session, tg_id=9917202)
    ref = Referral(referrer_user_id=referrer.id, referred_user_id=referred.id)
    session.add(ref)
    await session.flush()
    blocked = referrer if blocked_role == "referrer" else referred
    await UserRepo(session).set_shadow_banned(blocked.id, True)
    assert await ReferralService(session, SettingsService(session)).on_user_passed_subs(user=referred) is None
    await session.refresh(ref)
    assert not ref.is_confirmed
    assert referrer.balance_units == 0 and referrer.confirmed_ref_count == 0


async def test_review_approval_does_not_silently_award_blocked_account(session):
    user = await create_user(session, tg_id=9917301, is_shadow_banned=True)
    review = Review(user_id=user.id, rating=5, text="A pending review remains available for later moderation")
    session.add(review)
    await session.flush()
    assert await ReviewService(session).moderate(review.id, "approve") == (None, "blocked")
    await session.refresh(review)
    assert review.status == ReviewStatus.PENDING.value


async def test_partner_cpa_is_not_claimed_when_source_is_blocked(session):
    owner = await create_user(session, tg_id=9917401)
    partner = await PartnerRepo(session).create(owner.id)
    source = await create_user(session, tg_id=9917402, partner_id=partner.id, is_shadow_banned=True)
    assert await PartnerService(session, SettingsService(session)).accrue_passed_user(source) == 0
    await session.refresh(source)
    assert not source.partner_rewarded
    assert partner.balance_units == 0


async def test_debt_blocks_spending_and_gift_reserves(session):
    user = await create_user(session, tg_id=9917501, balance=10, debt=1)
    assert not await UserRepo(session).try_spend_balance(user.id, 1)
    assert not await UserRepo(session).reserve(user.id, 10_000, reference="debt")
    assert user.balance_units == 100_000 and user.debt_units == 10_000


async def test_click_stat_matches_settled_reward_instead_of_theoretical_fraction(session):
    user = await create_user(session, tg_id=9917601)
    settings = SettingsService(session)
    await settings.set("click.base_reward", 0.025)
    result = await ClickerService(session, settings).click(user)
    assert result.status == ClickStatus.OK
    assert result.reward == 0.02
    assert user.balance_units == 200
    assert result.earned_today == Decimal("0.02")
