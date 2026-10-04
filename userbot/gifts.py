"""Ordinary Stars gifts through the owner's MTProto account.

Verified against Telethon 1.45.0 (TL layer 229) and core.telegram.org/api/gifts.
This adapter never buys resale/TON/auction gifts and never retries a payment.
Only a direct payments.PaymentResult proves this call completed. Telegram's
gift invoice has no application idempotency key, and transaction history has
no form_id: price/recipient/time matches cannot resolve an unknown payment.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from telethon import TelegramClient, errors
from telethon.tl import functions, types

from userbot.client import TELETHON_OPERATION_ERRORS, disconnect, get_client, status_reason
from utils.gift_labels import ordinary_gift_label


@dataclass(frozen=True, slots=True)
class Gift:
    gift_id: int
    title: str
    stars: int
    available: bool = True
    reason: str | None = None
    kind: str = "ordinary"
    limited: bool = False
    availability_remains: int | None = None
    requires_premium: bool = False
    per_user_remains: int | None = None
    convert_stars: int = 0
    locked_until: datetime | None = None

    @property
    def id(self) -> int:
        return self.gift_id


@dataclass(frozen=True, slots=True)
class SenderStatus:
    available: bool
    tg_id: int | None = None
    username: str | None = None
    premium: bool = False
    stars: int | None = None
    reason: str | None = None

    @property
    def authenticated(self) -> bool:
        return self.available


@dataclass(frozen=True, slots=True)
class Recipient:
    tg_id: int
    username: str | None
    peer: types.InputPeerUser = field(repr=False)


@dataclass(frozen=True, slots=True)
class PreparedGift:
    form_id: int
    gift_id: int
    recipient_id: int
    sender_id: int
    stars: int
    invoice: types.InputInvoiceStarGift = field(repr=False)
    prepared_at: float = field(default_factory=time.monotonic)


@dataclass(frozen=True, slots=True)
class PaymentReceipt:
    form_id: int
    gift_id: int
    recipient_id: int
    sender_id: int
    stars: int
    proof: dict[str, Any]


class GiftAdapterError(RuntimeError):
    """Safe error code for DB/locales; never include raw request/exception text."""

    def __init__(self, code: str, *, retry_after: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after


class SenderUnavailable(GiftAdapterError):
    pass


class TemporaryFailure(GiftAdapterError):
    """A read-only call failed before payment; bounded retry is safe."""


class RecipientUnavailable(GiftAdapterError):
    pass


class GiftUnavailable(GiftAdapterError):
    pass


class PriceChanged(GiftAdapterError):
    pass


class InsufficientStars(GiftAdapterError):
    pass


class FloodWait(GiftAdapterError):
    pass


class UnknownPayment(GiftAdapterError):
    """Do not buy/refund/fail over automatically; retain reserve for review."""


class GiftAdapter(Protocol):
    async def catalogue(self, force: bool = False) -> tuple[Gift, ...]: ...
    async def sender_status(self) -> SenderStatus: ...
    async def resolve_recipient(self, tg_id: int, username: str | None) -> Recipient: ...
    async def prepare(self, gift_id: int, peer: Recipient, expected_stars: int) -> PreparedGift: ...
    async def pay(self, prepared: PreparedGift) -> PaymentReceipt: ...
    async def reconcile(self, attempt: object) -> PaymentReceipt | None: ...


_AUTH_ERRORS = (
    errors.AuthKeyError, errors.AuthKeyUnregisteredError,
    errors.AuthKeyDuplicatedError, errors.SessionRevokedError,
    errors.SessionExpiredError, errors.UserDeactivatedError,
)
_FLOOD_ERRORS = (errors.FloodWaitError, errors.FloodPremiumWaitError,
                 errors.SlowModeWaitError)


def _rpc_code(exc: errors.RPCError) -> str:
    return str(getattr(exc, "message", "")).upper()


def _classified_failure(exc: Exception, *, paying: bool) -> GiftAdapterError:
    # Only explicit negative replies prove a payment was not performed.
    if isinstance(exc, _FLOOD_ERRORS):
        return FloodWait("flood_wait", retry_after=max(1, int(exc.seconds)))
    if isinstance(exc, _AUTH_ERRORS):
        return SenderUnavailable("not_authorized")
    code = _rpc_code(exc) if isinstance(exc, errors.RPCError) else ""
    if code == "BALANCE_TOO_LOW":
        return InsufficientStars("insufficient_stars")
    if code in {"STARS_FORM_AMOUNT_MISMATCH", "GIFT_STARS_INVALID"}:
        return PriceChanged("price_changed")
    if code in {"STARGIFT_USAGE_LIMITED", "STARGIFT_NOT_FOUND"}:
        return GiftUnavailable("gift_sold_out")
    if code == "STARGIFT_USER_USAGE_LIMITED":
        return GiftUnavailable("gift_user_limit")
    if code in {"PREMIUM_ACCOUNT_REQUIRED", "PREMIUM_REQUIRED"}:
        return GiftUnavailable("premium_required")
    if code in {"FORM_EXPIRED", "FORM_ID_EMPTY", "FORM_UNSUPPORTED",
                "API_GIFT_RESTRICTED_UPDATE_APP", "BOT_INVOICE_INVALID"}:
        return GiftUnavailable("gift_form_unavailable")
    if code in {"PEER_ID_INVALID", "USER_PRIVACY_RESTRICTED", "USER_IS_BLOCKED"}:
        return RecipientUnavailable("recipient_unresolved")
    # FORM_SUBMIT_DUPLICATE means it may have succeeded earlier. ServerError,
    # network disconnect, timeout or an unfamiliar error also remain unknown.
    if paying:
        return UnknownPayment("payment_unknown")
    return TemporaryFailure("read_failed")


def _ordinary_gift(raw: types.StarGift) -> Gift:
    reason: str | None = None
    collectible = (bool(raw.limited) or raw.upgrade_stars is not None
                   or raw.availability_resale is not None or raw.resell_min_stars is not None
                   or raw.upgrade_variants is not None or bool(raw.peer_color_available)
                   or raw.background is not None)
    if raw.auction:
        reason = "gift_auction_unsupported"
    elif collectible:
        reason = "gift_collectible_unsupported"
    elif raw.sold_out:
        reason = "gift_sold_out"
    elif raw.limited_per_user and (raw.per_user_remains or 0) <= 0:
        reason = "gift_user_limit"
    elif raw.stars <= 0:
        reason = "gift_unsupported"
    return Gift(
        gift_id=raw.id, title=ordinary_gift_label(raw), stars=raw.stars,
        available=reason is None, reason=reason,
        kind="auction" if raw.auction else "collectible" if collectible else "ordinary",
        limited=bool(raw.limited), availability_remains=raw.availability_remains,
        requires_premium=bool(raw.require_premium), per_user_remains=raw.per_user_remains,
        convert_stars=raw.convert_stars, locked_until=raw.locked_until_date,
    )


class TelethonGiftAdapter:
    def __init__(
        self, *, client_provider: Callable[[], Awaitable[TelegramClient | None]] | None = None,
        catalogue_ttl: float = 60.0, request_timeout: float = 30.0,
    ) -> None:
        self._client_provider = client_provider
        self._ttl = catalogue_ttl
        self._timeout = request_timeout
        self._gifts: tuple[Gift, ...] | None = None
        self._hash = 0
        self._cached_at = 0.0
        self._catalogue_lock = asyncio.Lock()
        self._payment_lock = asyncio.Lock()
        self._submitted_forms: set[tuple[int, int]] = set()

    async def _client(self) -> TelegramClient:
        try:
            client = await asyncio.wait_for((self._client_provider or get_client)(), self._timeout)
        except TELETHON_OPERATION_ERRORS as exc:
            raise _classified_failure(exc, paying=False) from None
        if client is None:
            raise SenderUnavailable(status_reason())
        return client

    async def _read(self, client: TelegramClient, request: object) -> Any:
        try:
            return await asyncio.wait_for(client(request), timeout=self._timeout)
        except TELETHON_OPERATION_ERRORS as exc:
            raise _classified_failure(exc, paying=False) from None

    async def _abort_transport(self, client: TelegramClient) -> None:
        # Telethon's MessagePacker does not remove a queued request just because
        # its awaiting Future was cancelled. Close the transport so an expired
        # call cannot be transmitted later or requeued after a bad-salt reply.
        if self._client_provider is None:
            await asyncio.shield(disconnect())
        elif hasattr(client, "disconnect"):
            await asyncio.shield(client.disconnect())

    async def catalogue(self, force: bool = False) -> tuple[Gift, ...]:
        async with self._catalogue_lock:
            if not force and self._gifts is not None and time.monotonic() - self._cached_at < self._ttl:
                return self._gifts
            client = await self._client()
            response = await self._read(client, functions.payments.GetStarGiftsRequest(hash=self._hash))
            if isinstance(response, types.payments.StarGiftsNotModified):
                if self._gifts is None:
                    raise GiftAdapterError("catalogue_unavailable")
            elif isinstance(response, types.payments.StarGifts):
                self._gifts = tuple(_ordinary_gift(raw) for raw in response.gifts
                                    if isinstance(raw, types.StarGift))
                self._hash = response.hash
            else:
                raise GiftAdapterError("catalogue_unavailable")
            self._cached_at = time.monotonic()
            return self._gifts or ()

    async def sender_status(self) -> SenderStatus:
        try:
            client = await self._client()
            if not await asyncio.wait_for(client.is_user_authorized(), self._timeout):
                return SenderStatus(False, reason="not_authorized")
            me = await asyncio.wait_for(client.get_me(), self._timeout)
            if me is None or getattr(me, "bot", False):
                return SenderStatus(False, reason="not_authorized")
            response = await self._read(client, functions.payments.GetStarsStatusRequest(peer=types.InputPeerSelf()))
            if not isinstance(response, types.payments.StarsStatus) or not isinstance(response.balance, types.StarsAmount):
                return SenderStatus(False, reason="balance_unavailable")
            # Buy only whole Stars and floor the exact signed nanos fraction.
            # Ignoring negative nanos would overestimate usable funds by one.
            return SenderStatus(True, me.id, me.username, bool(me.premium),
                                max(0, response.balance.amount + response.balance.nanos // 1_000_000_000))
        except GiftAdapterError as exc:
            return SenderStatus(False, reason=exc.code)
        except TELETHON_OPERATION_ERRORS as exc:
            return SenderStatus(False, reason=_classified_failure(exc, paying=False).code)

    async def resolve_recipient(self, tg_id: int, username: str | None) -> Recipient:
        if tg_id <= 0:
            raise RecipientUnavailable("recipient_unresolved")
        client = await self._client()
        # Numeric ID works only when this account has actually encountered it.
        # A public username is resolved on Telegram then checked against bot ID.
        candidates: tuple[int | str, ...] = (tg_id,)
        if username and username.strip().lstrip("@").isascii():
            candidates += ("@" + username.strip().lstrip("@"),)
        for candidate in candidates:
            try:
                peer = await asyncio.wait_for(client.get_input_entity(candidate), self._timeout)
            except ValueError:
                continue
            except _AUTH_ERRORS:
                raise SenderUnavailable("not_authorized") from None
            except TELETHON_OPERATION_ERRORS as exc:
                raise _classified_failure(exc, paying=False) from None
            if not isinstance(peer, types.InputPeerUser):
                continue
            if peer.user_id != tg_id:
                raise RecipientUnavailable("recipient_mismatch")
            # Hash is obtained from Telegram/entity cache, never fabricated.
            if not peer.access_hash:
                continue
            return Recipient(tg_id, username, peer)
        # StringSession deliberately does not persist entity/access-hash caches.
        # A recent private message gives a real dialog that can be reloaded after
        # restart. Read only a bounded recent page, and never guess a hash/name.
        try:
            dialogs = await asyncio.wait_for(client.get_dialogs(limit=100), self._timeout)
        except _AUTH_ERRORS:
            raise SenderUnavailable("not_authorized") from None
        except TELETHON_OPERATION_ERRORS as exc:
            raise _classified_failure(exc, paying=False) from None
        for dialog in dialogs:
            peer = getattr(dialog, "input_entity", None)
            if isinstance(peer, types.InputPeerUser) and peer.user_id == tg_id and peer.access_hash:
                return Recipient(tg_id, username, peer)
        raise RecipientUnavailable("recipient_unresolved")

    async def _preflight(self, gift_id: int, expected_stars: int) -> tuple[TelegramClient, SenderStatus]:
        gifts = await self.catalogue(force=True)
        gift = next((item for item in gifts if item.gift_id == gift_id), None)
        if gift is None or gift.kind != "ordinary":
            raise GiftUnavailable("gift_unsupported")
        if not gift.available:
            raise GiftUnavailable(gift.reason or "gift_unavailable")
        if gift.stars != expected_stars or expected_stars <= 0:
            raise PriceChanged("price_changed")
        status = await self.sender_status()
        if not status.available or status.tg_id is None:
            raise SenderUnavailable(status.reason or "sender_unavailable")
        if gift.requires_premium and not status.premium:
            raise GiftUnavailable("premium_required")
        if status.stars is None or status.stars < expected_stars:
            raise InsufficientStars("insufficient_stars")
        client = await self._client()
        config = await self._read(client, functions.help.GetAppConfigRequest(hash=0))
        if not isinstance(config, types.help.AppConfig) or not isinstance(config.config, types.JsonObject):
            raise GiftUnavailable("gift_support_unavailable")
        blocked = next((value.value for value in config.config.value
                        if value.key == "stargifts_blocked"), None)
        if isinstance(blocked, types.JsonBool) and blocked.value:
            raise GiftUnavailable("gift_support_unavailable")
        if gift.locked_until is not None:
            can_send = await self._read(client, functions.payments.CheckCanSendGiftRequest(gift_id))
            if not isinstance(can_send, types.payments.CheckCanSendGiftResultOk):
                raise GiftUnavailable("gift_locked")
        return client, status

    async def prepare(self, gift_id: int, peer: Recipient, expected_stars: int) -> PreparedGift:
        if not isinstance(peer, Recipient) or not isinstance(peer.peer, types.InputPeerUser) or peer.peer.user_id != peer.tg_id or not peer.peer.access_hash:
            raise RecipientUnavailable("recipient_mismatch")
        client, status = await self._preflight(gift_id, expected_stars)
        invoice = types.InputInvoiceStarGift(peer=peer.peer, gift_id=gift_id)
        form = await self._read(client, functions.payments.GetPaymentFormRequest(invoice=invoice))
        if not isinstance(form, types.payments.PaymentFormStarGift) or not form.form_id:
            raise GiftUnavailable("gift_form_unavailable")
        if form.invoice.currency != "XTR" or form.invoice.test or sum(price.amount for price in form.invoice.prices) != expected_stars:
            raise PriceChanged("price_changed")
        return PreparedGift(form.form_id, gift_id, peer.tg_id, status.tg_id,
                            expected_stars, invoice)

    async def pay(self, prepared: PreparedGift) -> PaymentReceipt:
        async with self._payment_lock:
            key = (prepared.sender_id, prepared.form_id)
            if key in self._submitted_forms:
                raise UnknownPayment("payment_unknown")
            invoice = prepared.invoice
            if not isinstance(invoice, types.InputInvoiceStarGift) or invoice.gift_id != prepared.gift_id or not isinstance(invoice.peer, types.InputPeerUser) or invoice.peer.user_id != prepared.recipient_id or invoice.include_upgrade or invoice.message is not None:
                raise GiftUnavailable("gift_form_unavailable")
            if time.monotonic() - prepared.prepared_at >= 600:
                raise GiftUnavailable("gift_form_unavailable")
            client, status = await self._preflight(prepared.gift_id, prepared.stars)
            if status.tg_id != prepared.sender_id:
                raise SenderUnavailable("account_mismatch")
            self._submitted_forms.add(key)
            try:
                # Exactly one logical call. Its transport failure is ambiguous;
                # the queue must durably mark payment-started BEFORE this method.
                result = await asyncio.wait_for(client(functions.payments.SendStarsFormRequest(
                    form_id=prepared.form_id, invoice=invoice,
                )), timeout=self._timeout)
            except asyncio.CancelledError:
                await self._abort_transport(client)
                raise
            except TELETHON_OPERATION_ERRORS as exc:
                failure = _classified_failure(exc, paying=True)
                if not isinstance(failure, UnknownPayment):
                    self._submitted_forms.discard(key)
                else:
                    await self._abort_transport(client)
                raise failure from None
            if not isinstance(result, types.payments.PaymentResult):
                await self._abort_transport(client)
                raise UnknownPayment("payment_unknown")
            message_ids: list[int] = []
            for update in getattr(result.updates, "updates", ()):
                message = getattr(update, "message", None)
                if isinstance(getattr(message, "action", None), types.MessageActionStarGift):
                    action = message.action
                    if action.gift.id == prepared.gift_id and getattr(message.peer_id, "user_id", None) == prepared.recipient_id:
                        message_ids.append(message.id)
            return PaymentReceipt(
                prepared.form_id, prepared.gift_id, prepared.recipient_id,
                prepared.sender_id, prepared.stars,
                {"method": "payments.sendStarsForm", "result": "payments.paymentResult",
                 "form_id": prepared.form_id, "gift_id": prepared.gift_id,
                 "recipient_id": prepared.recipient_id, "sender_id": prepared.sender_id,
                 "stars": prepared.stars, "message_ids": message_ids},
            )

    async def reconcile(self, attempt: object) -> PaymentReceipt | None:
        # A starsTransaction has no form_id for InputInvoiceStarGift. The owner
        # may buy the same gift for the same recipient outside this bot. Even a
        # single history match or balance delta therefore is not unique proof.
        # Do not call sendStarsForm again to "check" an already submitted form.
        return None


adapter = TelethonGiftAdapter()
