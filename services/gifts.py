"""Short SQLite transactions around a durable, explicitly confirmed gift intent.

No Telegram call runs while a DB transaction is open. A payment-start marker is
committed BEFORE the irreversible call. Missing evidence always keeps the reserve.
"""
from __future__ import annotations

import asyncio
import secrets
import json
from functools import wraps
from contextlib import asynccontextmanager
from datetime import timedelta, timezone

from sqlalchemy import select, func, text

from core.config import settings
from db.base import utcnow
from db.gift_models import GiftQuote, GiftRequest, GiftAttempt, GiftAdminDecision
from db.models import User, MoneyOperation
from db.repositories.user import UserRepo
from db.session import SessionLocal
from db.money import to_units
from services.settings import SettingsService
from userbot.gifts import (adapter as default_adapter, GiftAdapterError, UnknownPayment,
                           FloodWait, InsufficientStars, SenderUnavailable, TemporaryFailure)
from utils.tz import msk_day_start_utc


class GiftServiceError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def api_errors(method):
    @wraps(method)
    async def wrapped(*args, **kwargs):
        try:
            return await method(*args, **kwargs)
        except GiftAdapterError as exc:
            raise GiftServiceError(exc.code) from None
    return wrapped


class GiftService:
    def __init__(self, session_factory=SessionLocal, adapter=None):
        self.sessions = session_factory
        self.adapter = adapter or default_adapter
        self.accepting = True

    @asynccontextmanager
    async def transaction(self):
        async with self.sessions() as session:
            try:
                await session.execute(text("BEGIN IMMEDIATE"))
                yield session
                await session.commit()
            except BaseException:
                await session.rollback()
                raise

    @api_errors
    async def catalogue(self):
        return await self.adapter.catalogue()

    async def account(self):
        return await self.adapter.sender_status()

    async def conditions(self):
        async with self.sessions() as s:
            config = SettingsService(s)
            return {"minimum_units": to_units(await config.get_float("withdraw.min_amount", 15)),
                    "min_refs": await config.get_int("withdraw.min_confirmed_refs", 5),
                    "daily_limit": await config.get_int("withdraw.per_day_limit", 5)}

    @staticmethod
    def eligible(user):
        if user is None or user.is_deleted or user.is_banned or user.is_shadow_banned:
            raise GiftServiceError("restricted")
        if not all((user.accepted_terms_at, user.captcha_passed_at, user.subs_passed_at)):
            raise GiftServiceError("gates")
        if user.debt_units > 0:
            raise GiftServiceError("debt")

    async def _gift(self, gift_id, force=True):
        gifts = await self.adapter.catalogue(force=force)
        gift = next((g for g in gifts if g.id == gift_id), None)
        if gift is None or not gift.available or gift.stars <= 0 or getattr(gift, "kind", "ordinary") != "ordinary":
            raise GiftServiceError("gift_unavailable")
        return gift

    @api_errors
    async def quote(self, tg_id, gift_id):
        if not self.accepting:
            raise GiftServiceError("paused")
        async with self.sessions() as s:
            user = await UserRepo(s).get_by_tg_id(tg_id)
            self.eligible(user)
            username = user.username
        gift = await self._gift(gift_id)
        await self.adapter.resolve_recipient(tg_id, username)
        async with self.transaction() as s:
            user = await UserRepo(s).get_by_tg_id(tg_id)
            self.eligible(user)
            svc = SettingsService(s)
            cost = to_units(gift.stars)  # existing 1:1 exchange, no new fee/rate
            await self._admission(s, user, cost, svc)
            quote = GiftQuote(id=secrets.token_hex(16), user_id=user.id,
                              recipient_tg_id=user.tg_id, gift_id=gift.id,
                              title=gift.title, stars=gift.stars, cost_units=cost,
                              expires_at=utcnow()+timedelta(seconds=120))
            s.add(quote)
            await s.flush()
            return quote

    async def _admission(self, s, user, cost, svc):
        if cost < to_units(await svc.get_float("withdraw.min_amount", 15)):
            raise GiftServiceError("minimum")
        if user.confirmed_ref_count < await svc.get_int("withdraw.min_confirmed_refs", 5):
            raise GiftServiceError("referrals")
        if user.balance_units < cost:
            raise GiftServiceError("balance")
        count = await s.scalar(select(func.count()).select_from(GiftRequest).where(
            GiftRequest.user_id == user.id, GiftRequest.created_at >= msk_day_start_utc()))
        limit = await svc.get_int("withdraw.per_day_limit", 5)
        if limit and count >= limit:
            raise GiftServiceError("daily_limit")

    @api_errors
    async def confirm(self, tg_id, token):
        async with self.sessions() as s:
            q = await s.get(GiftQuote, token)
            user = await UserRepo(s).get_by_tg_id(tg_id)
            if q is None or user is None or q.user_id != user.id or q.recipient_tg_id != tg_id:
                raise GiftServiceError("quote_invalid")
            existing = await s.scalar(select(GiftRequest).where(GiftRequest.quote_id == token))
            if existing:
                return existing
            if aware(q.expires_at) <= utcnow():
                raise GiftServiceError("quote_expired")
            gift_id, stars, username = q.gift_id, q.stars, user.username
        gift = await self._gift(gift_id)
        if gift.stars != stars:
            raise GiftServiceError("price_changed")
        await self.adapter.resolve_recipient(tg_id, username)
        async with self.transaction() as s:
            q = await s.get(GiftQuote, token)
            user = await UserRepo(s).get_by_tg_id(tg_id)
            existing = await s.scalar(select(GiftRequest).where(GiftRequest.quote_id == token))
            if existing:
                return existing
            if not self.accepting:
                raise GiftServiceError("paused")
            self.eligible(user)
            if q.user_id != user.id or q.recipient_tg_id != tg_id or aware(q.expires_at) <= utcnow():
                raise GiftServiceError("quote_expired")
            await self._admission(s, user, q.cost_units, SettingsService(s))
            req = GiftRequest(quote_id=q.id, user_id=user.id, recipient_tg_id=tg_id,
                              gift_id=q.gift_id, title=q.title, stars=q.stars,
                              cost_units=q.cost_units)
            s.add(req)
            await s.flush()
            if not await UserRepo(s).reserve(user.id, q.cost_units, reference=f"gift:{req.id}"):
                raise GiftServiceError("balance")
            return req

    async def history(self, tg_id, limit=10):
        async with self.sessions() as s:
            return list((await s.scalars(select(GiftRequest).join(User).where(
                User.tg_id == tg_id).order_by(GiftRequest.id.desc()).limit(min(limit, 50)))).all())

    async def detail(self, tg_id, request_id):
        async with self.sessions() as s:
            req = await s.scalar(select(GiftRequest).join(User).where(
                GiftRequest.id == request_id, User.tg_id == tg_id))
            if req is None:
                raise GiftServiceError("not_found")
            return req

    async def cancel(self, tg_id, request_id):
        async with self.transaction() as s:
            user = await UserRepo(s).get_by_tg_id(tg_id)
            req = await s.get(GiftRequest, request_id)
            if not user or not req or req.user_id != user.id:
                raise GiftServiceError("not_found")
            if req.status == "cancelled":
                return req
            if req.status not in {"pending", "waiting_funds"}:
                raise GiftServiceError("cannot_cancel")
            await self._release(s, req)
            req.status = "cancelled"
            return req

    async def queue_position(self, request_id):
        async with self.sessions() as s:
            return int(await s.scalar(select(func.count()).select_from(GiftRequest).where(
                GiftRequest.id <= request_id,
                GiftRequest.status.in_(["pending", "waiting_funds", "processing"]))) or 0)

    async def _release(self, s, req):
        if req.reserve_state == "held":
            if not await UserRepo(s).release_reserve(req.user_id, req.cost_units, reference=f"gift:{req.id}"):
                raise GiftServiceError("accounting_invariant")
            req.reserve_state = "released"

    async def _consume(self, s, req):
        if req.reserve_state == "held":
            if not await UserRepo(s).consume_reserve(req.user_id, req.cost_units, reference=f"gift:{req.id}"):
                raise GiftServiceError("accounting_invariant")
            req.reserve_state = "consumed"

    async def _spent(self, s):
        # All uncertain attempts count towards today's cap, including older
        # unresolved payments, so restarting/day rollover never frees their cap.
        return int(await s.scalar(select(func.coalesce(func.sum(GiftRequest.stars), 0)).where(
            ((GiftRequest.status == "succeeded") & (GiftRequest.paid_at >= msk_day_start_utc())) |
            GiftRequest.status.in_(["processing", "reconciliation_required"]))) or 0)

    async def budget(self):
        async with self.sessions() as s:
            return {"daily_stars": await self._spent(s),
                    "limit_stars": await SettingsService(s).get_int("gifts.daily_budget_stars", 0)}

    async def recover(self):
        async with self.transaction() as s:
            stale = list((await s.scalars(select(GiftRequest).where(
                GiftRequest.status == "processing", GiftRequest.lease_until <= utcnow()))).all())
            for req in stale:
                attempt = await s.scalar(select(GiftAttempt).where(GiftAttempt.worker_token == req.worker_token))
                req.status = "reconciliation_required" if attempt and attempt.phase == "payment_started" else "pending"
                req.error_code = "lease_expired"
                req.worker_token = None
                req.lease_until = None
            return len(stale)

    async def claim(self):
        if not self.accepting:
            return None
        await self.recover()
        async with self.transaction() as s:
            svc = SettingsService(s)
            if not await svc.get_bool("gifts.enabled", False):
                return None
            cooldown = await s.scalar(select(func.max(GiftAttempt.cooldown_until)))
            if cooldown and aware(cooldown) > utcnow():
                return None
            # Single sender: never start a second payment while another is in flight.
            if await s.scalar(select(GiftRequest.id).where(GiftRequest.status == "processing").limit(1)):
                return None
            req = await s.scalar(select(GiftRequest).where(
                GiftRequest.status.in_(["pending", "waiting_funds"]),
                (GiftRequest.next_attempt_at.is_(None)) | (GiftRequest.next_attempt_at <= utcnow())
            ).order_by(GiftRequest.id).limit(1))
            if not req:
                return None
            cap = await svc.get_int("gifts.daily_budget_stars", 0)
            if cap <= 0 or await self._spent(s) + req.stars > cap:
                req.status, req.error_code = "waiting_funds", "budget"
                req.next_attempt_at = utcnow()+timedelta(seconds=60)
                return None
            try:
                self.eligible(await s.get(User, req.user_id))
            except GiftServiceError as exc:
                await self._release(s, req)
                req.status, req.error_code = "failed", exc.code
                return None
            maximum = await svc.get_int("gifts.max_attempts", 5)
            if req.attempts_count >= maximum:
                await self._release(s, req)
                req.status, req.error_code = "failed", "retry_exhausted"
                return None
            token = secrets.token_hex(16)
            req.status, req.worker_token = "processing", token
            req.lease_until = utcnow()+timedelta(seconds=max(120, await svc.get_int("gifts.lease_seconds", 120)))
            req.attempts_count += 1
            s.add(GiftAttempt(request_id=req.id, worker_token=token))
            await s.flush()
            return req

    async def process_one(self):
        req = await self.claim()
        if req is None:
            return False
        started = False
        try:
            async with self.sessions() as s:
                user = await s.get(User, req.user_id)
                username = user.username
            peer = await asyncio.wait_for(self.adapter.resolve_recipient(req.recipient_tg_id, username), 30)
            prepared = await asyncio.wait_for(self.adapter.prepare(req.gift_id, peer, req.stars), 30)
            async with self.transaction() as s:
                current = await s.get(GiftRequest, req.id)
                if current.status != "processing" or current.worker_token != req.worker_token:
                    return False
                self.eligible(await s.get(User, current.user_id))
                user = await s.get(User, current.user_id)
                config = SettingsService(s)
                if user.confirmed_ref_count < await config.get_int("withdraw.min_confirmed_refs", 5):
                    raise GiftServiceError("referrals")
                if current.cost_units < to_units(await config.get_float("withdraw.min_amount", 15)):
                    raise GiftServiceError("minimum")
                if not await config.get_bool("gifts.enabled", False):
                    raise SenderUnavailable("paused")
                cap = await config.get_int("gifts.daily_budget_stars", 0)
                if cap <= 0 or await self._spent(s) > cap:
                    raise InsufficientStars("budget")
                attempt = await s.scalar(select(GiftAttempt).where(GiftAttempt.worker_token == req.worker_token))
                attempt.phase = "payment_started"
                attempt.form_id, attempt.sender_tg_id = prepared.form_id, prepared.sender_id
                current.lease_until = utcnow()+timedelta(seconds=120)
            started = True
            receipt = await asyncio.wait_for(self.adapter.pay(prepared), 45)
            await self._finish(req, "succeeded", receipt=receipt)
        except asyncio.CancelledError:
            await asyncio.shield(self._finish(req, "reconciliation_required" if started else "pending", code="interrupted"))
            raise
        except UnknownPayment:
            await self._finish(req, "reconciliation_required", code="payment_unknown")
        except TemporaryFailure:
            await self._finish(req, "pending", code="read_retry")
        except (FloodWait, InsufficientStars, SenderUnavailable) as exc:
            await self._finish(req, "waiting_funds" if not isinstance(exc, FloodWait) else "pending",
                               code=exc.code, delay=max(30, getattr(exc, "retry_after", None) or 60))
        except GiftAdapterError as exc:
            await self._finish(req, "failed", code=exc.code)
        except GiftServiceError as exc:
            await self._finish(req, "failed", code=exc.code)
        except Exception:
            # Unclassified transport/internal error after the durable marker is
            # ambiguous. An exception while saving success also follows this path.
            await self._finish(req, "reconciliation_required" if started else "pending", code="unknown" if started else "temporary")
        return True

    async def _finish(self, req, status, *, code=None, delay=60, receipt=None):
        async with self.transaction() as s:
            current = await s.get(GiftRequest, req.id)
            attempt = await s.scalar(select(GiftAttempt).where(GiftAttempt.worker_token == req.worker_token))
            if attempt is None or current is None:
                raise GiftServiceError("accounting_invariant")
            if receipt is not None:
                attempt.proof = json.dumps(receipt.proof, ensure_ascii=True) if isinstance(receipt.proof, dict) else str(receipt.proof)
            owns_active = current.status == "processing" and current.worker_token == req.worker_token
            late_receipt = (status == "succeeded" and current.status == "reconciliation_required"
                            and current.reserve_state == "held" and attempt.phase in {"payment_started", "unknown"})
            if not owns_active and not late_receipt:
                if receipt is not None and current.confirmation_kind != "telegram":
                    current.error_code = "late_receipt_conflict"
                return
            # Cancellation/unknown errors can land just after the DB commit and
            # before the local `started` flag is set. Trust the durable marker.
            if status == "pending" and code in {"interrupted", "temporary"} and attempt.phase == "payment_started":
                status, code = "reconciliation_required", "payment_unknown"
            if status == "succeeded":
                if (receipt.form_id != attempt.form_id or receipt.sender_id != attempt.sender_tg_id or
                    receipt.gift_id != current.gift_id or receipt.recipient_id != current.recipient_tg_id or receipt.stars != current.stars):
                    status, code = "reconciliation_required", "proof_mismatch"
                else:
                    await self._consume(s, current)
                    current.confirmation_kind = "telegram"
                    current.paid_at = utcnow()
                    proof = json.dumps(receipt.proof, ensure_ascii=True) if isinstance(receipt.proof, dict) else str(receipt.proof)
                    current.proof = proof
                    attempt.proof = proof
            if status == "failed":
                await self._release(s, current)
            attempt.phase = "unknown" if status == "reconciliation_required" else "finished"
            attempt.error_code = code
            if code == "flood_wait":
                attempt.cooldown_until = utcnow()+timedelta(seconds=delay)
            current.status, current.error_code = status, code
            current.worker_token, current.lease_until = None, None
            current.next_attempt_at = utcnow()+timedelta(seconds=delay) if status in {"pending", "waiting_funds"} else None
            if status == "waiting_funds" or (status == "pending" and code not in {"temporary", "interrupted", "read_retry"}):
                # Funds/session availability and explicit FloodWaits do not
                # exhaust retries for a proven pre-payment transport failure.
                current.attempts_count = max(0, current.attempts_count-1)

    @staticmethod
    def owner(actor):
        if actor != settings.owner_id:
            raise GiftServiceError("owner_only")

    async def admin_list(self, status=None, limit=15):
        async with self.sessions() as s:
            stmt = select(GiftRequest).order_by(GiftRequest.id.desc()).limit(min(limit, 50))
            if status:
                stmt = stmt.where(GiftRequest.status == status)
            return list((await s.scalars(stmt)).all())

    async def admin_detail(self, actor_tg_id, request_id):
        self.owner(actor_tg_id)
        async with self.sessions() as s:
            return {"request": await s.get(GiftRequest, request_id),
                    "attempts": list((await s.scalars(select(GiftAttempt).where(GiftAttempt.request_id == request_id))).all()),
                    "audit": list((await s.scalars(select(GiftAdminDecision).where(GiftAdminDecision.request_id == request_id))).all()),
                    "operations": list((await s.scalars(select(MoneyOperation).where(MoneyOperation.reference.in_(
                        [f"reserve:gift:{request_id}", f"release:gift:{request_id}", f"consume:gift:{request_id}"])))).all())}

    async def admin_confirmation(self, actor, request_id, action):
        self.owner(actor)
        if action not in {"manual_success", "proven_failure", "retry"}:
            raise GiftServiceError("invalid_action")
        async with self.transaction() as s:
            req = await s.get(GiftRequest, request_id)
            if req is None:
                raise GiftServiceError("not_found")
            token = secrets.token_hex(16)
            s.add(GiftAdminDecision(id=token, request_id=request_id, actor_tg_id=actor,
                                   action=action, expires_at=utcnow()+timedelta(seconds=120)))
            return token

    async def admin_decide(self, actor_tg_id, request_id, action, confirmation_token, evidence):
        self.owner(actor_tg_id)
        async with self.transaction() as s:
            decision = await s.get(GiftAdminDecision, confirmation_token)
            req = await s.get(GiftRequest, request_id)
            if not decision or not req or decision.actor_tg_id != actor_tg_id or decision.request_id != request_id or decision.action != action:
                raise GiftServiceError("confirmation_invalid")
            if decision.used_at:
                return req
            if aware(decision.expires_at) <= utcnow():
                raise GiftServiceError("quote_expired")
            if action == "retry":
                if req.status != "waiting_funds":
                    raise GiftServiceError("unsafe_retry")
                req.status, req.next_attempt_at = "pending", None
                req.attempts_count = 0
            else:
                if req.status != "reconciliation_required" or not evidence or len(evidence.strip()) < 12:
                    raise GiftServiceError("evidence_required")
                if action == "manual_success":
                    await self._consume(s, req)
                    req.status, req.confirmation_kind = "succeeded", "manual"
                    req.paid_at = utcnow()
                elif action == "proven_failure":
                    await self._release(s, req)
                    req.status, req.confirmation_kind = "failed", "manual_failure"
                else:
                    raise GiftServiceError("invalid_action")
                req.proof = evidence.strip()[:2000]
            decision.used_at, decision.evidence = utcnow(), (evidence or "retry")[:2000]
            return req
