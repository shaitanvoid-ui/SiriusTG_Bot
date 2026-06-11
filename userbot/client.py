"""Telethon userbot: ленивый singleton-клиент.

Сессия (StringSession) хранится зашифрованной в БД (таблица userbot_sessions),
не на диске. Подключаемся лениво — при первом обращении (bio-чекер, Этап 7 —
вывод подарков). Если api-креды/сессия не настроены или аккаунт разлогинен —
возвращаем None, фичи деградируют мягко (бот не падает).

Стабильность сессии: явно задаём device_model / system_version / app_version /
lang, чтобы Telegram считал клиента постоянным устройством и не сбрасывал
авторизацию (иначе userbot периодически «вылетает»).
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

from telethon import TelegramClient
from telethon.sessions import StringSession

from core.config import settings
from core.crypto import CryptoError, decrypt
from core.logger import get_logger
from db.repositories.userbot_session import UserbotSessionRepo
from db.session import SessionLocal


log = get_logger(__name__)


# Параметры «устройства» — мимикрия под Telegram Desktop ради стабильной сессии.
# Меняешь значения — старая сессия может слететь, поэтому фиксируем их жёстко.
DEVICE_MODEL: str = "Sirius Desktop"
SYSTEM_VERSION: str = "Windows 10"
APP_VERSION: str = "4.16.8 x64"
LANG_CODE: str = "ru"
SYSTEM_LANG_CODE: str = "ru"


_client: TelegramClient | None = None
_lock = asyncio.Lock()


def _build_client(session_str: str) -> TelegramClient:
    """Создаёт TelegramClient со стабилизирующими параметрами."""
    return TelegramClient(
        StringSession(session_str),
        settings.tg_api_id,
        settings.tg_api_hash,
        device_model=DEVICE_MODEL,
        system_version=SYSTEM_VERSION,
        app_version=APP_VERSION,
        lang_code=LANG_CODE,
        system_lang_code=SYSTEM_LANG_CODE,
        # сглаживает флуд-вейты вместо падений — пер-сессии до 60 сек ждём сами
        flood_sleep_threshold=60,
    )


def is_configured() -> bool:
    """Заданы ли api_id/api_hash. Без них userbot бесполезен."""
    return bool(settings.tg_api_id and settings.tg_api_hash)


async def _load_session_str() -> str | None:
    async with SessionLocal() as session:
        row = await UserbotSessionRepo(session).get_active()
    if row is None:
        return None
    try:
        return decrypt(row.session_enc)
    except CryptoError:
        log.error("userbot_session_decrypt_failed", phone=row.phone)
        return None


async def get_client() -> TelegramClient | None:
    """Подключённый авторизованный клиент или None (мягкая деградация)."""
    global _client
    if not is_configured():
        return None

    async with _lock:
        if _client is not None and _client.is_connected():
            return _client

        session_str = await _load_session_str()
        if not session_str:
            log.warning("userbot_no_session")
            return None

        client = _build_client(session_str)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                log.warning("userbot_not_authorized")
                with suppress(Exception):
                    await client.disconnect()
                return None
        except Exception:
            log.exception("userbot_connect_failed")
            with suppress(Exception):
                await client.disconnect()
            return None

        _client = client
        me = await client.get_me()
        log.info("userbot_connected", user_id=getattr(me, "id", None))
        return _client


async def disconnect() -> None:
    """Graceful-отключение (хук shutdown)."""
    global _client
    if _client is not None:
        with suppress(Exception):
            await _client.disconnect()
        _client = None
        log.info("userbot_disconnected")
