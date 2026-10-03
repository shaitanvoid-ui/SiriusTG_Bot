"""Рассылка по всем юзерам (Этап 9).

Throttle ~25 сообщений/сек (лимит Telegram ~30/сек на бота).
Прогресс отдаётся через callback каждые `report_every` отправок.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

from core.logger import get_logger


log = get_logger(__name__)
_broadcast_lock = asyncio.Lock()

ProgressCb = Callable[[int, int], Awaitable[None]]  # (done, total)


@dataclass(frozen=True)
class BroadcastResult:
    total: int
    sent: int
    failed: int  # заблокировали бота / удалили аккаунт / прочие ошибки


class BroadcastBusyError(RuntimeError):
    """В процессе уже есть другая рассылка."""


async def _send_one(bot: Bot, tg_id: int, text: str, *, retries: int = 3) -> bool:
    for attempt in range(retries + 1):
        try:
            await bot.send_message(tg_id, text)
            return True
        except TelegramRetryAfter as exc:
            if attempt >= retries:
                log.warning(
                    "broadcast_retry_exhausted",
                    tg_id=tg_id,
                    retry_after=exc.retry_after,
                )
                return False
            await asyncio.sleep(max(0.0, float(exc.retry_after)) + 0.1)
        except TelegramAPIError as exc:
            log.info("broadcast_delivery_failed", tg_id=tg_id, error=str(exc))
            return False
    return False  # pragma: no cover


async def run_broadcast(
    bot: Bot,
    tg_ids: list[int],
    text: str,
    *,
    delay_sec: float = 0.04,
    report_every: int = 25,
    progress_cb: ProgressCb | None = None,
) -> BroadcastResult:
    if _broadcast_lock.locked():
        raise BroadcastBusyError("broadcast is already running")

    async with _broadcast_lock:
        total = len(tg_ids)
        sent = 0
        failed = 0
        for i, tg_id in enumerate(tg_ids, start=1):
            if await _send_one(bot, tg_id, text):
                sent += 1
            else:
                failed += 1
            if progress_cb is not None and (i % max(1, report_every) == 0 or i == total):
                try:
                    await progress_cb(i, total)
                except TelegramAPIError as exc:
                    log.info("broadcast_progress_failed", error=str(exc))
            if delay_sec > 0:
                await asyncio.sleep(delay_sec)
        log.info("broadcast_done", total=total, sent=sent, failed=failed)
        return BroadcastResult(total=total, sent=sent, failed=failed)
