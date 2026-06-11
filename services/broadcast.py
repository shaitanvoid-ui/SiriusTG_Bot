"""Рассылка по всем юзерам (Этап 9).

Throttle ~25 сообщений/сек (лимит Telegram ~30/сек на бота).
Прогресс отдаётся через callback каждые `report_every` отправок.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from core.logger import get_logger


log = get_logger(__name__)

ProgressCb = Callable[[int, int], Awaitable[None]]  # (done, total)


@dataclass(frozen=True)
class BroadcastResult:
    total: int
    sent: int
    failed: int  # заблокировали бота / удалили аккаунт / прочие ошибки


async def run_broadcast(
    bot: Bot,
    tg_ids: list[int],
    text: str,
    *,
    delay_sec: float = 0.04,
    report_every: int = 25,
    progress_cb: ProgressCb | None = None,
) -> BroadcastResult:
    total = len(tg_ids)
    sent = 0
    failed = 0
    for i, tg_id in enumerate(tg_ids, start=1):
        try:
            await bot.send_message(tg_id, text)
            sent += 1
        except TelegramAPIError:
            failed += 1
        if progress_cb is not None and (i % report_every == 0 or i == total):
            try:
                await progress_cb(i, total)
            except Exception:  # прогресс не должен ронять рассылку
                pass
        await asyncio.sleep(delay_sec)
    log.info("broadcast_done", total=total, sent=sent, failed=failed)
    return BroadcastResult(total=total, sent=sent, failed=failed)
