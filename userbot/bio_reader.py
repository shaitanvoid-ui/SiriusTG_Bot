"""Чтение bio (about) юзера через userbot и проверка наличия его рефки.

Используется ежедневным бонусом: бонус выдаётся, если в bio юзера стоит его
реферальная ссылка. Все вызовы userbot сериализованы и слегка троттлятся —
Telethon-клиент не любит параллельных запросов, а Telegram — частых.
"""

from __future__ import annotations

import asyncio
import re
import time

from telethon.tl import functions

from core.logger import get_logger
from userbot.client import TELETHON_OPERATION_ERRORS, get_client


log = get_logger(__name__)


_MIN_INTERVAL_S: float = 1.0
_throttle_lock = asyncio.Lock()
_last_call: float = 0.0
_USER_LOOKUP_ERRORS: tuple[type[Exception], ...] = (
    *TELETHON_OPERATION_ERRORS,
    ValueError,
)


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
        try:
            entity = await client.get_entity(key)
            break
        except _USER_LOOKUP_ERRORS as exc:
            log.info(
                "userbot_resolve_candidate_failed",
                candidate="username" if isinstance(key, str) else "tg_id",
                error_type=type(exc).__name__,
            )
    if entity is None:
        log.info("userbot_resolve_failed")
        return None, False

    try:
        full = await client(functions.users.GetFullUserRequest(id=entity))
        about = getattr(full.full_user, "about", None) or ""
        return about, True
    except _USER_LOOKUP_ERRORS as exc:
        log.warning("userbot_getfull_failed", error_type=type(exc).__name__)
        return None, False


def bio_contains_ref(about: str, *, payload: str, bot_username: str) -> bool:
    """Есть ли в bio рефка юзера.

    Принимаем как полноценный deep-link (?start=r<id>), так и упоминание бота
    рядом с payload — чтобы юзеру было проще оформить bio.
    """
    text = about or ""
    payload_value = payload.strip()
    if not payload_value:
        return False

    bot_token_left = r"(?<![\w@])"
    bot_token_right = r"(?!\w)"
    payload_token_left = r"(?<![\w-])"
    payload_token_right = r"(?![\w-])"
    payload_pattern = (
        rf"{payload_token_left}{re.escape(payload_value)}{payload_token_right}"
    )
    bot_value = (bot_username or "").strip().lstrip("@")
    if not bot_value:
        return False
    bot_pattern = (
        rf"{bot_token_left}@?{re.escape(bot_value)}{bot_token_right}"
    )
    return bool(
        re.search(bot_pattern, text, flags=re.IGNORECASE)
        and re.search(payload_pattern, text, flags=re.IGNORECASE)
    )


async def check_ref_in_bio(
    *, tg_id: int, username: str | None, payload: str, bot_username: str
) -> tuple[bool, bool]:
    """(available, has_ref)."""
    about, available = await fetch_about(tg_id=tg_id, username=username)
    if not available:
        return False, False
    return True, bio_contains_ref(about or "", payload=payload, bot_username=bot_username)
