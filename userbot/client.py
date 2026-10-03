"""One encrypted user-account session, one client and one process at a time.

Bio checks and gifts share this client. RPC retries, FloodWait sleeps and
reconnection replay are disabled: the durable queue decides safe retries.
No plaintext session file is created.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import BinaryIO

from telethon import TelegramClient
from telethon.errors import InvalidBufferError, RPCError, SecurityError
from telethon.sessions import StringSession

from core.config import settings
from core.crypto import CryptoError, decrypt
from core.logger import get_logger
from db.repositories.userbot_session import UserbotSessionRepo
from db.session import SessionLocal


log = get_logger(__name__)
DEVICE_MODEL: str = "Sirius Desktop"
SYSTEM_VERSION: str = "Windows 10"
APP_VERSION: str = "4.16.8 x64"
LANG_CODE: str = "ru"
SYSTEM_LANG_CODE: str = "ru"

_client: TelegramClient | None = None
_lock = asyncio.Lock()
_process_lock: SessionProcessLock | None = None
_status_reason: str = "not_connected"

TELETHON_OPERATION_ERRORS: tuple[type[Exception], ...] = (
    RPCError, InvalidBufferError, SecurityError, OSError, TimeoutError,
)


class SessionInUse(RuntimeError):
    """Another process owns the account session; do not connect in parallel."""


class SessionProcessLock:
    """OS lock shared by runtime/login; it contains no session or credentials."""

    def __init__(self, directory: Path | None = None) -> None:
        database = settings.database_url
        db_path = database.split("///", 1)[-1].split("?", 1)[0]
        self.directory = directory or Path(db_path).resolve().parent
        # Same DB expressed as a relative/absolute URL must share the lock.
        self.path = self.directory / ".userbot-primary.lock"
        self._file: BinaryIO | None = None

    def acquire(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                if not handle.read(1):
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                os.fchmod(handle.fileno(), 0o600)
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise SessionInUse("userbot_session_in_use") from None
        self._file = handle

    def release(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None


def normalized_phone(value: str | None) -> str:
    return "".join(char for char in (value or "") if char.isdecimal())


def account_matches(me: object, phone: str) -> bool:
    """Verify the selected personal sender; OWNER_ID governs bot administration.

    Phone is verified by getMe, not by the presence of configuration. After the
    first interactive login USERBOT_ACCOUNT_ID can pin the actual sender ID.
    """
    expected_id = getattr(settings, "userbot_account_id", None)
    return bool(
        not getattr(me, "bot", False)
        and isinstance(getattr(me, "id", None), int) and me.id > 0
        and (expected_id is None or me.id == expected_id)
        and normalized_phone(getattr(me, "phone", None)) == normalized_phone(phone)
        and normalized_phone(phone)
    )


def status_reason() -> str:
    """Safe code: never contains phone/session/raw RPC details."""
    return _status_reason


async def _disconnect_after_failure(client: TelegramClient, *, reason: str) -> None:
    try:
        await client.disconnect()
    except TELETHON_OPERATION_ERRORS as exc:
        log.warning("userbot_disconnect_failed", reason=reason,
                    error_type=type(exc).__name__)


def _build_client(session_str: str) -> TelegramClient:
    return TelegramClient(
        StringSession(session_str), settings.tg_api_id, settings.tg_api_hash,
        device_model=DEVICE_MODEL, system_version=SYSTEM_VERSION,
        app_version=APP_VERSION, lang_code=LANG_CODE,
        system_lang_code=SYSTEM_LANG_CODE,
        request_retries=0, flood_sleep_threshold=0,
        raise_last_call_error=True, auto_reconnect=False,
    )


def is_configured() -> bool:
    return bool(settings.tg_api_id and settings.tg_api_hash and settings.userbot_phone)


async def _load_session_str() -> str | None:
    # Never silently select the first active or a backup account.
    async with SessionLocal() as session:
        row = await UserbotSessionRepo(session).get_by_phone(settings.userbot_phone or "")
    if row is None or not row.is_active:
        return None
    try:
        return decrypt(row.session_enc)
    except CryptoError:
        log.error("userbot_session_decrypt_failed", session_id=row.id)
        return None


async def get_client() -> TelegramClient | None:
    global _client, _process_lock, _status_reason
    if not is_configured():
        _status_reason = "not_configured"
        return None
    async with _lock:
        if _client is not None and _client.is_connected():
            return _client
        if _client is not None:
            await _disconnect_after_failure(_client, reason="connection_lost")
            _client = None

        session_str = await _load_session_str()
        if not session_str:
            _status_reason = "no_session"
            return None
        if _process_lock is None:
            process_lock = SessionProcessLock()
            try:
                process_lock.acquire()
            except SessionInUse:
                _status_reason = "session_in_use"
                return None
            _process_lock = process_lock

        client = None
        accepted = False
        try:
            client = _build_client(session_str)
            await asyncio.wait_for(client.connect(), 30)
            if not await asyncio.wait_for(client.is_user_authorized(), 30):
                _status_reason = "not_authorized"
                return None
            me = await asyncio.wait_for(client.get_me(), 30)
            if not account_matches(me, settings.userbot_phone or ""):
                _status_reason = "account_mismatch"
                return None
            accepted = True
        except TELETHON_OPERATION_ERRORS as exc:
            _status_reason = "connection_failed"
            log.warning("userbot_connect_failed", error_type=type(exc).__name__)
            return None
        finally:
            if not accepted:
                if client is not None:
                    await _disconnect_after_failure(client, reason=_status_reason)
                if _process_lock is not None:
                    _process_lock.release()
                    _process_lock = None

        _client = client
        _status_reason = "available"
        log.info("userbot_connected")
        return client


async def disconnect() -> None:
    global _client, _process_lock, _status_reason
    async with _lock:
        try:
            if _client is not None:
                await _disconnect_after_failure(_client, reason="shutdown")
        finally:
            _client = None
            _status_reason = "not_connected"
            if _process_lock is not None:
                _process_lock.release()
                _process_lock = None
