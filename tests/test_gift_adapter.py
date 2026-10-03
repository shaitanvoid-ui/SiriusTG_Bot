"""Isolated MTProto boundary contracts; these tests never reach Telegram.

Negative RPC replies are simulated as proven rejection; timeout/duplicate or
verification output is simulated as unknown. No exactly-once payment claim.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from telethon import errors
from telethon.tl import functions, types

from userbot.gifts import (
    FloodWait, GiftAdapterError, GiftUnavailable, InsufficientStars,
    PriceChanged, Recipient, RecipientUnavailable, TelethonGiftAdapter,
    UnknownPayment,
)


def gift(**kwargs):
    values = dict(id=77, sticker=types.DocumentEmpty(1), stars=15, convert_stars=12,
                  title="Test gift")
    values.update(kwargs)
    return types.StarGift(**values)


class Client:
    def __init__(self):
        self.requests = []
        self.gifts = [gift()]
        self.balance = 100
        self.balance_nanos = 0
        self.premium = False
        self.not_modified = False
        self.payment_error = None
        self.payment_result = types.payments.PaymentResult(
            types.Updates(updates=[], users=[], chats=[], date=datetime.now(timezone.utc), seq=1),
        )
        self.form_amount = 15
        self.form_currency = "XTR"
        self.form_test = False
        self.recipient = types.InputPeerUser(123, 456)
        self.config_blocked = False
        self.can_send = True
        self.authorized = True
        self.disconnected = False
        self.dialogs = []
        self.dialog_queries = []

    async def disconnect(self):
        self.disconnected = True

    async def get_me(self):
        return SimpleNamespace(id=1, username="account", premium=self.premium, bot=False)

    async def is_user_authorized(self):
        return self.authorized

    async def get_input_entity(self, candidate):
        if isinstance(candidate, int):
            raise ValueError("uncached recipient")
        return self.recipient

    async def get_dialogs(self, *, limit):
        self.dialog_queries.append(limit)
        return self.dialogs

    async def __call__(self, request):
        self.requests.append(request)
        if isinstance(request, functions.payments.GetStarGiftsRequest):
            if self.not_modified:
                return types.payments.StarGiftsNotModified()
            return types.payments.StarGifts(52, self.gifts, [], [])
        if isinstance(request, functions.payments.GetStarsStatusRequest):
            assert isinstance(request.peer, types.InputPeerSelf) and not request.ton
            return types.payments.StarsStatus(types.StarsAmount(self.balance, self.balance_nanos), [], [])
        if isinstance(request, functions.help.GetAppConfigRequest):
            return types.help.AppConfig(1, types.JsonObject([
                types.JsonObjectValue("stargifts_blocked", types.JsonBool(self.config_blocked)),
            ]))
        if isinstance(request, functions.payments.CheckCanSendGiftRequest):
            if self.can_send:
                return types.payments.CheckCanSendGiftResultOk()
            return types.payments.CheckCanSendGiftResultFail(types.TextWithEntities("Not yet", []))
        if isinstance(request, functions.payments.GetPaymentFormRequest):
            assert isinstance(request.invoice, types.InputInvoiceStarGift)
            assert not request.invoice.include_upgrade
            return types.payments.PaymentFormStarGift(999, types.Invoice(
                self.form_currency, [types.LabeledPrice("gift", self.form_amount)],
                test=self.form_test,
            ))
        if isinstance(request, functions.payments.SendStarsFormRequest):
            if self.payment_error:
                raise self.payment_error
            return self.payment_result
        raise AssertionError(type(request).__name__)


@pytest.fixture
def context():
    client = Client()

    async def provider():
        return client

    return client, TelethonGiftAdapter(client_provider=provider)


async def prepared(context):
    _, adapter = context
    recipient = await adapter.resolve_recipient(123, "recipient")
    return await adapter.prepare(77, recipient, 15)


async def test_catalogue_ttl_and_server_not_modified(context):
    client, adapter = context
    first = await adapter.catalogue()
    assert first[0].stars == 15 and first[0].convert_stars == 12
    assert await adapter.catalogue() is first
    assert len(client.requests) == 1
    client.not_modified = True
    assert await adapter.catalogue(force=True) is first
    assert client.requests[-1].hash == 52


async def test_not_modified_without_known_catalogue_fails_closed(context):
    client, adapter = context
    client.not_modified = True
    with pytest.raises(GiftAdapterError, match="catalogue_unavailable"):
        await adapter.catalogue()


async def test_recipient_username_must_match_server_user_id(context):
    client, adapter = context
    client.recipient = types.InputPeerUser(124, 456)
    with pytest.raises(RecipientUnavailable, match="recipient_mismatch"):
        await adapter.resolve_recipient(123, "similar_username")
    assert not client.requests


async def test_no_username_or_access_hash_never_fabricates_peer(context):
    client, adapter = context
    with pytest.raises(RecipientUnavailable, match="recipient_unresolved"):
        await adapter.resolve_recipient(123, None)
    client.recipient = types.InputPeerUser(123, 0)
    with pytest.raises(RecipientUnavailable, match="recipient_unresolved"):
        await adapter.resolve_recipient(123, "recipient")


async def test_no_username_reloads_verified_recent_dialog_after_restart(context):
    client, adapter = context
    client.dialogs = [SimpleNamespace(input_entity=types.InputPeerUser(999, 111)),
                      SimpleNamespace(input_entity=types.InputPeerUser(123, 789))]
    first = await adapter.resolve_recipient(123, None)
    restarted = TelethonGiftAdapter(client_provider=adapter._client_provider)
    second = await restarted.resolve_recipient(123, None)
    assert first.peer.user_id == second.peer.user_id == 123
    assert first.peer.access_hash == second.peer.access_hash == 789
    assert client.dialog_queries == [100, 100]
    assert not client.requests  # no payment request


async def test_dialog_resolution_rejects_wrong_type_id_and_empty_hash(context):
    client, adapter = context
    client.dialogs = [SimpleNamespace(input_entity=types.InputPeerUser(124, 789)),
                      SimpleNamespace(input_entity=types.InputPeerUser(123, 0)),
                      SimpleNamespace(input_entity=types.InputPeerChannel(123, 456))]
    with pytest.raises(RecipientUnavailable, match="recipient_unresolved"):
        await adapter.resolve_recipient(123, None)


async def test_dialog_read_floodwait_is_safe_without_purchase(context):
    client, adapter = context
    async def flood(*, limit):
        raise errors.FloodWaitError(None, capture=60)
    client.get_dialogs = flood
    with pytest.raises(FloodWait):
        await adapter.resolve_recipient(123, None)
    assert not client.requests


@pytest.mark.parametrize("values,code", [
    ({"sold_out": True}, "gift_sold_out"),
    ({"limited": True, "availability_remains": 0, "availability_total": 1}, "gift_unsupported"),
    ({"auction": True}, "gift_unsupported"),
    ({"limited_per_user": True, "per_user_remains": 0, "per_user_total": 1}, "gift_user_limit"),
    ({"require_premium": True}, "premium_required"),
])
async def test_unsupported_unavailable_and_account_requirements(context, values, code):
    client, adapter = context
    client.gifts = [gift(**values)]
    with pytest.raises(GiftUnavailable, match=code):
        await adapter.prepare(77, Recipient(123, "recipient", client.recipient), 15)
    assert not any(isinstance(r, functions.payments.SendStarsFormRequest) for r in client.requests)


@pytest.mark.parametrize("attributes", [
    {"limited": True, "availability_remains": 10, "availability_total": 100, "title": "Snoop Dogg"},
    {"upgrade_stars": 25}, {"upgrade_stars": 0},
    {"availability_resale": 1, "resell_min_stars": 200},
    {"upgrade_variants": 0}, {"upgrade_variants": 6},
    {"peer_color_available": True}, {"background": object()},
])
async def test_non_upgraded_collectible_cannot_use_ordinary_flow(context, attributes):
    client, adapter = context
    client.gifts = [gift(**attributes)]
    catalogue = await adapter.catalogue(force=True)
    assert catalogue[0].kind == "collectible" and not catalogue[0].available
    with pytest.raises(GiftUnavailable, match="gift_unsupported"):
        await adapter.prepare(77, Recipient(123, "recipient", client.recipient), 15)
    assert not any(isinstance(r, functions.payments.SendStarsFormRequest) for r in client.requests)


@pytest.mark.parametrize("currency,amount,is_test", [("TON", 15, False), ("XTR", 16, False), ("XTR", 15, True)])
async def test_form_price_currency_and_test_mode_are_checked(context, currency, amount, is_test):
    client, _ = context
    client.form_currency, client.form_amount, client.form_test = currency, amount, is_test
    with pytest.raises(PriceChanged):
        await prepared(context)


async def test_locked_gift_and_account_blocked_are_checked(context):
    client, _ = context
    client.gifts = [gift(locked_until_date=datetime.now(timezone.utc))]
    client.can_send = False
    with pytest.raises(GiftUnavailable, match="gift_locked"):
        await prepared(context)
    client.can_send = True
    client.config_blocked = True
    with pytest.raises(GiftUnavailable, match="gift_support_unavailable"):
        await prepared(context)


async def test_recheck_catalogue_and_balance_before_payment(context):
    client, adapter = context
    form = await prepared(context)
    client.gifts = [gift(stars=16)]
    with pytest.raises(PriceChanged):
        await adapter.pay(form)
    client.gifts = [gift()]
    client.balance = 14
    with pytest.raises(InsufficientStars):
        await adapter.pay(form)
    assert not any(isinstance(r, functions.payments.SendStarsFormRequest) for r in client.requests)


async def test_direct_payment_result_confirms_one_call_and_blocks_repeat(context):
    client, adapter = context
    form = await prepared(context)
    receipt = await adapter.pay(form)
    assert receipt.proof["result"] == "payments.paymentResult"
    assert receipt.form_id == 999 and receipt.recipient_id == 123
    with pytest.raises(UnknownPayment):
        await adapter.pay(form)
    assert sum(isinstance(r, functions.payments.SendStarsFormRequest) for r in client.requests) == 1


@pytest.mark.parametrize("error", [TimeoutError(), OSError(), errors.ServerError(None, "SERVER_ERROR", 500), errors.RPCError(None, "FORM_SUBMIT_DUPLICATE", 400)])
async def test_ambiguous_payment_never_retries_or_infers_reconciliation(context, error):
    client, adapter = context
    form = await prepared(context)
    client.payment_error = error
    with pytest.raises(UnknownPayment):
        await adapter.pay(form)
    with pytest.raises(UnknownPayment):
        await adapter.pay(form)
    assert await adapter.reconcile(SimpleNamespace(form_id=999, gift_id=77)) is None
    assert sum(isinstance(r, functions.payments.SendStarsFormRequest) for r in client.requests) == 1
    assert client.disconnected  # no request remains queued after timeout/unknown


async def test_verification_result_is_unknown(context):
    client, adapter = context
    form = await prepared(context)
    client.payment_result = types.payments.PaymentVerificationNeeded("https://example.invalid")
    with pytest.raises(UnknownPayment):
        await adapter.pay(form)


async def test_floodwait_is_explicit_no_sleep_no_automatic_retry(context):
    client, adapter = context
    form = await prepared(context)
    client.payment_error = errors.FloodWaitError(None, 23)
    with pytest.raises(FloodWait) as result:
        await adapter.pay(form)
    assert result.value.retry_after == 23
    assert sum(isinstance(r, functions.payments.SendStarsFormRequest) for r in client.requests) == 1


@pytest.mark.parametrize("rpc_code,failure", [
    ("BALANCE_TOO_LOW", InsufficientStars),
    ("STARS_FORM_AMOUNT_MISMATCH", PriceChanged),
    ("STARGIFT_USAGE_LIMITED", GiftUnavailable),
])
async def test_proven_negative_rpc_is_not_an_unknown_payment(context, rpc_code, failure):
    client, adapter = context
    form = await prepared(context)
    client.payment_error = errors.RPCError(None, rpc_code, 400)
    with pytest.raises(failure):
        await adapter.pay(form)
    assert sum(isinstance(r, functions.payments.SendStarsFormRequest) for r in client.requests) == 1


async def test_revoked_authorization_account_unavailable(context):
    client, adapter = context
    client.authorized = False
    status = await adapter.sender_status()
    assert not status.available and status.reason == "not_authorized"


async def test_actual_stars_balance_floors_signed_nanos(context):
    client, adapter = context
    client.balance, client.balance_nanos = 15, -1
    assert (await adapter.sender_status()).stars == 14
    with pytest.raises(InsufficientStars):
        await prepared(context)


async def test_concurrent_pay_same_form_has_one_external_call(context):
    client, adapter = context
    form = await prepared(context)
    results = await asyncio.gather(adapter.pay(form), adapter.pay(form), return_exceptions=True)
    assert sum(isinstance(result, UnknownPayment) for result in results) == 1
    assert sum(isinstance(r, functions.payments.SendStarsFormRequest) for r in client.requests) == 1


async def test_cancelling_payment_closes_transport_and_blocks_same_form(context):
    client, adapter = context
    form = await prepared(context)
    original_call = client.__class__.__call__
    entered = asyncio.Event()
    release = asyncio.Event()

    async def delayed_call(self, request):
        if isinstance(request, functions.payments.SendStarsFormRequest):
            self.requests.append(request)
            entered.set()
            await release.wait()
        return await original_call(self, request)

    # This models a queued/in-flight transport request whose waiter is cancelled.
    # Closing the client prevents the library from sending it at a later time.
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(client.__class__, "__call__", delayed_call)
        task = asyncio.create_task(adapter.pay(form))
        try:
            await asyncio.wait_for(entered.wait(), 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    assert client.disconnected
    with pytest.raises(UnknownPayment):
        await adapter.pay(form)
    assert sum(isinstance(r, functions.payments.SendStarsFormRequest) for r in client.requests) == 1
