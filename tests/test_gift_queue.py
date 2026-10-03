"""Mocked MTProto contracts: no real Stars or network. Unknown != failure."""
import asyncio
from datetime import timedelta
from types import SimpleNamespace as NS

import pytest
from sqlalchemy import select, func

from core.config import settings
from db.base import utcnow
from db.models import User, MoneyOperation
from db.gift_models import GiftRequest, GiftAttempt
from db.repositories.setting import SettingRepo
from services.gifts import GiftService, GiftServiceError
from services.settings import SettingsService
from userbot.gifts import UnknownPayment, InsufficientStars, FloodWait, SenderUnavailable


class FakeAdapter:
    """PaymentResult is authoritative only for this awaited invocation."""
    def __init__(self):
        self.price, self.available, self.calls, self.error = 25, True, 0, None
        self.pause = None

    async def catalogue(self, force=False):
        return (NS(id=7, title="Gift", stars=self.price, available=self.available),)

    async def resolve_recipient(self, tg_id, username):
        return NS(tg_id=tg_id, peer=NS(user_id=tg_id))

    async def prepare(self, gift_id, peer, expected_stars):
        if self.error and isinstance(self.error, (InsufficientStars, FloodWait, SenderUnavailable)):
            raise self.error
        return NS(form_id=123, sender_id=999, recipient_id=peer.tg_id,
                  gift_id=gift_id, stars=expected_stars)

    async def pay(self, prepared):
        self.calls += 1
        if self.pause:
            await self.pause.wait()
        if self.error:
            raise self.error
        return NS(**vars(prepared), proof="payment-result:123")


@pytest.fixture
async def gift_setup(session, session_factory):
    user = User(tg_id=101, username="recipient", balance=100,
                accepted_terms_at=utcnow(), captcha_passed_at=utcnow(), subs_passed_at=utcnow(),
                confirmed_ref_count=5)
    session.add(user)
    repo = SettingRepo(session)
    await repo.set("gifts.enabled", True)
    await repo.set("gifts.daily_budget_stars", 500)
    await session.commit()
    SettingsService.invalidate()
    adapter = FakeAdapter()
    return GiftService(session_factory, adapter), adapter, user.id


async def request(service):
    q = await service.quote(101, 7)
    return await service.confirm(101, q.id)


async def account(service, user_id):
    async with service.sessions() as s:
        return await s.get(User, user_id)


@pytest.mark.asyncio
async def test_concurrent_confirm_single_reserve(gift_setup):
    svc, adapter, uid = gift_setup
    q = await svc.quote(101, 7)
    results = await asyncio.gather(*[svc.confirm(101, q.id) for _ in range(5)])
    assert len({r.id for r in results}) == 1
    u = await account(svc, uid)
    assert (u.balance_units, u.reserved_units) == (750000, 250000)
    async with svc.sessions() as s:
        assert await s.scalar(select(func.count()).select_from(GiftRequest)) == 1
        assert await s.scalar(select(func.count()).select_from(MoneyOperation).where(MoneyOperation.reason == "gift_reserve")) == 1
    assert adapter.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("change,code", [("price","price_changed"),("sold_out","gift_unavailable"),("debt","debt"),("ban","restricted"),("shadow","restricted"),("balance","balance"),("refs","referrals"),("gates","gates")])
async def test_rechecks_after_preview(gift_setup, change, code):
    svc, adapter, uid = gift_setup
    q = await svc.quote(101, 7)
    if change == "price": adapter.price = 30
    elif change == "sold_out": adapter.available = False
    else:
        async with svc.transaction() as s:
            u = await s.get(User, uid)
            if change == "debt": u.debt_units = 1
            if change == "ban": u.is_banned = True
            if change == "shadow": u.is_shadow_banned = True
            if change == "balance": u.balance_units = 0
            if change == "refs": u.confirmed_ref_count = 0
            if change == "gates": u.subs_passed_at = None
    with pytest.raises(GiftServiceError) as err:
        await svc.confirm(101, q.id)
    assert err.value.code == code
    assert (await account(svc, uid)).reserved_units == 0


@pytest.mark.asyncio
async def test_recipient_ownership_expiry_and_msk_limit(gift_setup):
    svc, adapter, uid = gift_setup
    q = await svc.quote(101, 7)
    with pytest.raises(GiftServiceError): await svc.confirm(202, q.id)
    async with svc.transaction() as s:
        from db.gift_models import GiftQuote
        (await s.get(GiftQuote, q.id)).expires_at = utcnow()-timedelta(seconds=1)
    with pytest.raises(GiftServiceError): await svc.confirm(101, q.id)
    req = await request(svc)
    with pytest.raises(GiftServiceError): await svc.cancel(202, req.id)
    async with svc.transaction() as s:
        await SettingRepo(s).set("withdraw.per_day_limit", 1)
    SettingsService.invalidate()
    with pytest.raises(GiftServiceError) as err: await svc.quote(101, 7)
    assert err.value.code == "daily_limit"


@pytest.mark.asyncio
async def test_daily_admission_boundary_is_midnight_moscow(gift_setup):
    from utils.tz import msk_day_start_utc
    svc, adapter, uid = gift_setup
    req = await request(svc)
    cutoff = msk_day_start_utc()
    assert cutoff.hour == 21  # Moscow midnight on the preceding UTC date
    async with svc.transaction() as s:
        await SettingRepo(s).set("withdraw.per_day_limit", 1)
        (await s.get(GiftRequest, req.id)).created_at = cutoff-timedelta(microseconds=1)
    SettingsService.invalidate()
    await svc.quote(101, 7)
    async with svc.transaction() as s:
        (await s.get(GiftRequest, req.id)).created_at = cutoff
    with pytest.raises(GiftServiceError) as err:
        await svc.quote(101, 7)
    assert err.value.code == "daily_limit"


@pytest.mark.asyncio
async def test_cancel_release_and_claim_race(gift_setup):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    results = await asyncio.gather(svc.claim(), svc.cancel(101, req.id), return_exceptions=True)
    stored = await svc.detail(101, req.id)
    u = await account(svc, uid)
    if stored.status == "cancelled":
        assert u.reserved_units == 0 and u.balance_units == 1000000
        await svc.cancel(101, req.id)
    else:
        assert stored.status == "processing" and u.reserved_units == 250000
        assert any(isinstance(r, GiftServiceError) for r in results)


@pytest.mark.asyncio
async def test_second_worker_cannot_claim_and_success_once(gift_setup):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    adapter.pause = asyncio.Event()
    task = asyncio.create_task(svc.process_one())
    for _ in range(100):
        if adapter.calls: break
        await asyncio.sleep(.005)
    assert await svc.claim() is None
    adapter.pause.set()
    await task
    assert await svc.process_one() is False
    stored = await svc.detail(101, req.id)
    assert stored.status == "succeeded" and stored.confirmation_kind == "telegram"
    assert (await account(svc, uid)).reserved_units == 0
    assert adapter.calls == 1
    with pytest.raises(GiftServiceError): await svc.cancel(101, req.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("phase,expected", [("preparing","pending"),("payment_started","reconciliation_required")])
async def test_restart_stale_lease_requires_evidence(gift_setup, phase, expected):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    claimed = await svc.claim()
    async with svc.transaction() as s:
        (await s.get(GiftRequest, req.id)).lease_until = utcnow()-timedelta(seconds=1)
        attempt = await s.scalar(select(GiftAttempt).where(GiftAttempt.worker_token == claimed.worker_token))
        attempt.phase = phase
    restarted = GiftService(svc.sessions, adapter)
    assert await restarted.recover() == 1
    assert (await svc.detail(101, req.id)).status == expected
    assert (await account(svc, uid)).reserved_units == 250000
    assert adapter.calls == 0


@pytest.mark.asyncio
async def test_unknown_outcome_keeps_reserve_blocks_retry_and_manual_once(gift_setup):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    adapter.error = UnknownPayment("payment_unknown")
    await svc.process_one()
    assert (await svc.detail(101, req.id)).status == "reconciliation_required"
    assert (await account(svc, uid)).reserved_units == 250000
    assert await svc.process_one() is False
    token = await svc.admin_confirmation(settings.owner_id, req.id, "retry")
    with pytest.raises(GiftServiceError): await svc.admin_decide(settings.owner_id, req.id, "retry", token, "retry")
    token = await svc.admin_confirmation(settings.owner_id, req.id, "manual_success")
    with pytest.raises(GiftServiceError): await svc.admin_decide(settings.owner_id, req.id, "manual_success", token, "")
    evidence = "Owner reviewed sender Telegram receipt manually"
    await svc.admin_decide(settings.owner_id, req.id, "manual_success", token, evidence)
    await svc.admin_decide(settings.owner_id, req.id, "manual_success", token, evidence)
    assert (await svc.detail(101, req.id)).confirmation_kind == "manual"
    assert (await account(svc, uid)).reserved_units == 0
    assert adapter.calls == 1
    with pytest.raises(GiftServiceError): await svc.admin_confirmation(99999, req.id, "retry")


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [InsufficientStars("insufficient_stars"), SenderUnavailable("sender_unavailable"), FloodWait("flood_wait", retry_after=60)])
async def test_proven_pre_payment_waits_no_purchase(gift_setup, error):
    svc, adapter, uid = gift_setup
    req = await request(svc)
    adapter.error = error
    await svc.process_one()
    stored = await svc.detail(101, req.id)
    assert stored.status in {"pending", "waiting_funds"}
    assert stored.attempts_count == 0
    assert (await account(svc, uid)).reserved_units == 250000 and adapter.calls == 0
    async with svc.transaction() as s:
        (await s.get(GiftRequest, req.id)).next_attempt_at = None
        if isinstance(error, FloodWait):
            for attempt in (await s.scalars(select(GiftAttempt).where(GiftAttempt.request_id == req.id))).all():
                attempt.cooldown_until = utcnow()-timedelta(seconds=1)
    adapter.error = None
    await svc.process_one()
    assert (await svc.detail(101, req.id)).status == "succeeded"


@pytest.mark.asyncio
async def test_notification_failure_does_not_repeat_payment(gift_setup):
    from workers.gifts import GiftWorker
    from aiogram.exceptions import TelegramNetworkError
    from aiogram.methods import SendMessage
    svc, adapter, uid = gift_setup
    req = await request(svc)
    await svc.process_one()
    class BrokenBot:
        async def send_message(self, *args, **kwargs):
            raise TelegramNetworkError(SendMessage(chat_id=101,text="test"), "offline")
    worker = GiftWorker(svc, BrokenBot())
    await worker.notify()
    await worker.notify()
    assert (await svc.detail(101, req.id)).notification_error == "TelegramNetworkError"
    assert await svc.process_one() is False and adapter.calls == 1
