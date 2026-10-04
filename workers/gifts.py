"""One durable sender queue; notifications are claimed after result commit."""
from __future__ import annotations

import asyncio
from contextlib import suppress
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select

from core.config import settings
from core.logger import get_logger
from db.gift_models import GiftRequest
from locales.ru import T
from services.gifts import GiftService
from services.settings import SettingsService
from bot.keyboards.gifts import kb_gift_notification
from utils.gift_labels import gift_label
from utils.ui import html_text

log = get_logger(__name__)


class GiftWorker:
    def __init__(self, service: GiftService, bot):
        self.service, self.bot = service, bot
        self.stop_event = asyncio.Event()
        self.task = None

    async def notify(self):
        async with self.service.transaction() as s:
            req = await s.scalar(select(GiftRequest).where(
                (GiftRequest.status.in_(["succeeded", "failed", "cancelled", "reconciliation_required", "waiting_funds"]) &
                 (GiftRequest.notified_status.is_(None) | (GiftRequest.notified_status != GiftRequest.status))) |
                ((GiftRequest.error_code == "late_receipt_conflict") &
                 (GiftRequest.alerted_key.is_(None) | (GiftRequest.alerted_key != "late_receipt_conflict")))
            ).order_by(GiftRequest.id).limit(1))
            if req is None:
                return
            # At most one send attempt for a status. Telegram sendMessage has no
            # idempotency key; a failed notification must never re-run payment.
            notify_user = req.notified_status != req.status
            req.notified_status = req.status
            alert_key = "late_receipt_conflict" if req.error_code == "late_receipt_conflict" else req.status
            alert_owner = req.alerted_key != alert_key and (req.status in {"reconciliation_required", "waiting_funds", "failed"} or alert_key == "late_receipt_conflict")
            if alert_owner:
                req.alerted_key = alert_key
            request_id, recipient, status = req.id, req.recipient_tg_id, req.status
            title = gift_label(req.title)
        try:
            if notify_user:
                await self.bot.send_message(recipient, T.gift_notification.format(
                    request_id=request_id, title=html_text(title), status=T.gift_statuses[status]),
                    reply_markup=kb_gift_notification(request_id), disable_notification=True)
        except TelegramAPIError as exc:
            async with self.service.transaction() as s:
                req = await s.get(GiftRequest, request_id)
                req.notification_error = type(exc).__name__
        if alert_owner:
            try:
                await self.bot.send_message(settings.owner_id, T.gift_owner_alert.format(
                    request_id=request_id, status=T.gift_owner_receipt_conflict if alert_key == "late_receipt_conflict" else T.gift_statuses[status]), disable_notification=True)
            except TelegramAPIError:
                log.warning("gift_owner_notification_failed", request_id=request_id)

    async def run(self):
        await self.service.recover()
        while not self.stop_event.is_set():
            try:
                await self.service.process_one()
                await self.notify()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Never emit RPC request fields/session strings into logs.
                log.error("gift_worker_failed", error_type=type(exc).__name__)
            async with self.service.sessions() as s:
                interval = max(1, await SettingsService(s).get_int("gifts.poll_seconds", 15))
            with suppress(TimeoutError):
                await asyncio.wait_for(self.stop_event.wait(), interval)

    def start(self):
        self.task = asyncio.create_task(self.run(), name="gift-queue")

    async def stop(self):
        self.service.accepting = False
        self.stop_event.set()
        if self.task:
            try:
                await asyncio.wait_for(asyncio.shield(self.task), 20)
            except TimeoutError:
                self.task.cancel()
                with suppress(asyncio.CancelledError):
                    await self.task
