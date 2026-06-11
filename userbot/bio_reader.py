"""Чтение bio (about) юзера через userbot и проверка наличия его рефки.

Используется ежедневным бонусом: бонус выдаётся, если в bio юзера стоит его
реферальная ссылка. Все вызовы userbot сериализованы и слегка троттлятся —
Telethon-клиент не любит параллельных запросов, а Telegram — частых.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import suppress

from telethon.tl import functions

from core.logger import get_logger
from userbot.client import get_client


log = get_logger(__name__)


_MIN_INTERVAL_S: float = 1.0
_throttle_lock = asyncio.Lock()
_last_call: float = 0.0


async def _throttle() -> None:
    global _last_call
    async with _throttle_lock:
        wait = _MIN_INTERVAL_S - (time.monotonic() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call = time.monotonic()


async def fetch_about(*, tg_id: int, username: str | None) -> tuple[str | None, bool]:
    """Возвращает (about, available).

    available=False означает «userbot недоступен / не смог разрешить юзера» —
    это НЕ то же самое, что «bio пустое». Бонус в этом случае не списывает попытку.
    """
    client = await get_client()
    if client is None:
        return None, False

    await _throttle()

    entity = None
    # Сначала по username (надёжнее), потом по tg_id.
    for key in (f"@{username}" if username else None, tg_id):
        if key is None:
            continue
        with suppress(Exception):
            entity = await client.get_entity(key)
            break
    if entity is None:
        log.info("userbot_resolve_failed", tg_id=tg_id)
        return None, False

    try:
        full = await client(functions.users.GetFullUserRequest(id=entity))
        about = getattr(full.full_user, "about", None) or ""
        return about, True
    except Exception:
        log.exception("userbot_getfull_failed", tg_id=tg_id)
        return None, False


def bio_contains_ref(about: str, *, payload: str, bot_username: str) -> bool:
    """Есть ли в bio рефка юзера.

    Принимаем как полноценный deep-link (?start=r<id>), так и упоминание бота
    рядом с payload — чтобы юзеру было проще оформить bio.
    """
    text = (about or "").lower()
    payload_l = payload.lower()
    if f"start={payload_l}" in text:
        return True
    bot_l = (bot_username or "").lower()
    return bool(bot_l) and bot_l in text and payload_l in text


async def check_ref_in_bio(
    *, tg_id: int, username: str | None, payload: str, bot_username: str
) -> tuple[bool, bool]:
    """(available, has_ref)."""
    about, available = await fetch_about(tg_id=tg_id, username=username)
    if not available:
        return False, False
    return True, bio_contains_ref(about or "", payload=payload, bot_username=bot_username)
