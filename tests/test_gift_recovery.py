"""Crash/race/account-budget contracts using an isolated DB and fake MTProto.

The fake PaymentResult proves only its direct awaiting call. A committed start
marker without a returned receipt stays uncertain, including cancellation at
the commit boundary. No network or production account is used.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import SendMessage
from sqlalchemy import func, select

from core.config import settings
from db.base import utcnow
from db.gift_models import GiftAttempt, GiftRequest
from db.models import MoneyOperation
from db.repositories.setting import SettingRepo
from services.gifts import GiftService, GiftServiceError
from services.settings import SettingsService
from tests.test_gift_queue import account, gift_setup, request  # noqa: F401 -- pytest fixture registration
from userbot.gifts import FloodWait, TemporaryFailure, UnknownPayment
from workers.gifts import GiftWorker


async def make_due(service, request_id):
    async with service.transaction() as session:
        (await session.get(GiftRequest, request_id)).next_attempt_at = None


async def test_cancellation_after_start_commit_keeps_reserve_even_before_local_flag(gift_setup, monkeypatch):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    original_transaction = svc.transaction
    armed = True

    @asynccontextmanager
    async def cancel_after_committed_marker():
        nonlocal armed
        async with original_transaction() as session:
            yield session
        # Model cancellation after SQLite committed but before the context
        # returned to process_one, whose local started flag is still False.
        if armed:
            async with svc.sessions() as session:
                phase = await session.scalar(select(GiftAttempt.phase).where(
                    GiftAttempt.request_id == req.id).order_by(GiftAttempt.id.desc()))
            if phase == "payment_started":
                armed = False
                raise asyncio.CancelledError

    monkeypatch.setattr(svc, "transaction", cancel_after_committed_marker)
    with pytest.raises(asyncio.CancelledError):
        await svc.process_one()
    stored = await svc.detail(101, req.id)
    assert stored.status == "reconciliation_required" and stored.reserve_state == "held"
    assert (await account(svc, uid)).reserved_units == 250000
    assert adapter.calls == 0
    restarted = GiftService(svc.sessions, adapter)
    assert await restarted.process_one() is False


async def test_direct_success_arriving_after_lease_recovery_retains_proof(gift_setup, monkeypatch):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    entered, release = asyncio.Event(), asyncio.Event()

    async def delayed_direct_receipt(prepared):
        adapter.calls += 1
        entered.set()
        await release.wait()
        return SimpleNamespace(**vars(prepared), proof="direct payment-result:123")

    monkeypatch.setattr(adapter, "pay", delayed_direct_receipt)
    running = asyncio.create_task(svc.process_one())
    try:
        await asyncio.wait_for(entered.wait(), 5)
        async with svc.transaction() as session:
            (await session.get(GiftRequest, req.id)).lease_until = utcnow()-timedelta(seconds=1)
        restarted = GiftService(svc.sessions, adapter)
        assert await restarted.recover() == 1
        assert (await svc.detail(101, req.id)).status == "reconciliation_required"
        release.set()
        await asyncio.wait_for(running, 5)
    finally:
        release.set()
        if not running.done():
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)
    stored = await svc.detail(101, req.id)
    assert stored.status == "succeeded" and stored.confirmation_kind == "telegram"
    assert stored.proof == "direct payment-result:123"
    assert (await account(svc, uid)).reserved_units == 0
    async with svc.sessions() as session:
        attempt = await session.scalar(select(GiftAttempt).where(GiftAttempt.request_id == req.id))
        assert attempt.proof == stored.proof
        assert await session.scalar(select(func.count()).select_from(MoneyOperation).where(
            MoneyOperation.reason == "gift_consume")) == 1
    assert await svc.process_one() is False and adapter.calls == 1


async def test_proven_read_failure_after_start_marker_retries_without_payment(gift_setup, monkeypatch):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    actual_pay = adapter.pay

    async def read_only_failure(prepared):
        raise TemporaryFailure("read_failed")

    monkeypatch.setattr(adapter, "pay", read_only_failure)
    await svc.process_one()
    stored = await svc.detail(101, req.id)
    assert stored.status == "pending" and stored.attempts_count == 1
    assert stored.reserve_state == "held" and adapter.calls == 0
    await make_due(svc, req.id)
    monkeypatch.setattr(adapter, "pay", actual_pay)
    await svc.process_one()
    assert (await svc.detail(101, req.id)).status == "succeeded"
    assert (await account(svc, uid)).reserved_units == 0 and adapter.calls == 1


async def test_floodwait_cooldown_survives_restart_and_cancel_across_requests(gift_setup, monkeypatch):
    svc, adapter, uid = gift_setup
    first, second = await request(svc), await request(svc)

    async def proven_flood_rejection(prepared):
        adapter.calls += 1
        raise FloodWait("flood_wait", retry_after=120)

    monkeypatch.setattr(adapter, "pay", proven_flood_rejection)
    await svc.process_one()
    stored = await svc.detail(101, first.id)
    assert stored.status == "pending" and stored.attempts_count == 0
    assert stored.next_attempt_at is not None
    restarted = GiftService(svc.sessions, adapter)
    assert await restarted.claim() is None  # same sender, next request also waits
    await svc.cancel(101, first.id)
    assert await restarted.claim() is None  # cancellation never bypasses account cooldown
    assert (await svc.detail(101, second.id)).status == "pending"
    assert adapter.calls == 1 and (await account(svc, uid)).reserved_units == 250000


async def test_two_workers_share_budget_and_unknown_counts_across_msk_rollover(gift_setup, monkeypatch):
    import services.gifts as gifts_module

    svc, adapter, uid = gift_setup
    first, second = await request(svc), await request(svc)
    async with svc.transaction() as session:
        await SettingRepo(session).set("gifts.daily_budget_stars", 25)
    SettingsService.invalidate()
    adapter.error = UnknownPayment("payment_unknown")
    other = GiftService(svc.sessions, adapter)
    await asyncio.gather(svc.process_one(), other.process_one())
    assert adapter.calls == 1
    assert (await svc.detail(101, first.id)).status == "reconciliation_required"
    assert (await svc.detail(101, second.id)).status in {"pending", "waiting_funds"}
    assert (await account(svc, uid)).reserved_units == 500000
    # Uncertain money is still committed even after tomorrow's MSK boundary.
    boundary = utcnow()+timedelta(days=1)
    monkeypatch.setattr(gifts_module, "msk_day_start_utc", lambda: boundary)
    await make_due(svc, second.id)
    adapter.error = None
    assert await other.claim() is None
    assert (await svc.budget())["daily_stars"] == 25
    assert adapter.calls == 1


async def test_concurrent_owner_decision_consumes_reserve_once(gift_setup):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    adapter.error = UnknownPayment("payment_unknown")
    await svc.process_one()
    token = await svc.admin_confirmation(settings.owner_id, req.id, "manual_success")
    evidence = "Owner verified the exact Telegram operation in account history"
    results = await asyncio.gather(*[
        svc.admin_decide(settings.owner_id, req.id, "manual_success", token, evidence)
        for _ in range(4)
    ])
    assert all(result.status == "succeeded" for result in results)
    assert (await account(svc, uid)).reserved_units == 0
    async with svc.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(MoneyOperation).where(
            MoneyOperation.reason == "gift_consume")) == 1
    with pytest.raises(GiftServiceError, match="owner_only"):
        await svc.admin_decide(99999, req.id, "manual_success", token, evidence)


async def test_two_notification_workers_claim_once_and_never_repeat_purchase(gift_setup):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    await svc.process_one()

    class BrokenBot:
        calls = 0

        async def send_message(self, *args, **kwargs):
            self.calls += 1
            raise TelegramNetworkError(SendMessage(chat_id=101, text="test"), "offline")

    bot = BrokenBot()
    first, second = GiftWorker(svc, bot), GiftWorker(GiftService(svc.sessions, adapter), bot)
    await asyncio.gather(first.notify(), second.notify())
    await first.notify()
    assert bot.calls == 1
    assert (await svc.detail(101, req.id)).notification_error == "TelegramNetworkError"
    assert await svc.process_one() is False and adapter.calls == 1


async def test_notification_metadata_never_moves_paid_gift_into_next_msk_budget(gift_setup):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    await svc.process_one()
    async with svc.transaction() as session:
        stored = await session.get(GiftRequest, req.id)
        stored.paid_at = utcnow()-timedelta(days=2)
        # Updating notification/error metadata changes TimestampMixin.updated_at.
        # It must not pretend an old gift was purchased again today.
        stored.notification_error = "late_notification"
    assert (await svc.budget())["daily_stars"] == 0
    assert adapter.calls == 1 and (await account(svc, uid)).reserved_units == 0


async def test_request_daily_limit_changes_exactly_at_msk_midnight(gift_setup, monkeypatch):
    import services.gifts as gifts_module

    svc, adapter, uid = gift_setup
    first = await request(svc)
    boundary = datetime(2026, 10, 2, 21, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(gifts_module, "msk_day_start_utc", lambda: boundary)
    async with svc.transaction() as session:
        (await session.get(GiftRequest, first.id)).created_at = boundary-timedelta(microseconds=1)
        await SettingRepo(session).set("withdraw.per_day_limit", 1)
    SettingsService.invalidate()
    second = await request(svc)  # previous MSK day's request does not count
    async with svc.transaction() as session:
        (await session.get(GiftRequest, second.id)).created_at = boundary
    with pytest.raises(GiftServiceError, match="daily_limit"):
        await svc.quote(101, 7)
    assert adapter.calls == 0 and (await account(svc, uid)).reserved_units == 500000
