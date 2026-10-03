"""Шифрование чувствительных данных через Fernet.

Ключ берётся из settings.fernet_key (.env) и защищает Telethon-сессии,
реквизиты выплат и резервные копии SQLite. Production-конфигурация проверяет
его до старта, а низкоуровневые функции всё равно не допускают plaintext fallback.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from core.config import settings


class CryptoError(RuntimeError):
    """Проблема шифрования/дешифрования или отсутствие ключа."""


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.fernet_key
    if not key:
        raise CryptoError("FERNET_KEY не задан — шифрование недоступно")
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise CryptoError("FERNET_KEY некорректен") from exc


def encrypt(plaintext: str) -> str:
    """Шифрует строку, возвращает urlsafe-base64 токен."""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def encrypt_bytes(plaintext: bytes) -> bytes:
    """Шифрует бинарные данные (например, резервную копию SQLite)."""
    return _fernet().encrypt(plaintext)


def decrypt(token: str) -> str:
    """Расшифровывает токен. При повреждении/неверном ключе — CryptoError."""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError) as exc:
        raise CryptoError("Не удалось расшифровать данные") from exc


def decrypt_bytes(token: bytes) -> bytes:
    """Расшифровывает бинарный Fernet-токен."""
    try:
        return _fernet().decrypt(token)
    except (InvalidToken, ValueError, TypeError) as exc:
        raise CryptoError("Не удалось расшифровать данные") from exc


_FIELD_PREFIX = "enc:v1:"


def encrypt_field(plaintext: str) -> str:
    """Версионированное шифрование строкового поля БД."""
    return _FIELD_PREFIX + encrypt(plaintext)


def decrypt_field(value: str) -> str:
    """Читает новое зашифрованное поле и совместим со старыми plaintext-строками."""
    if not value.startswith(_FIELD_PREFIX):
        return value
    return decrypt(value[len(_FIELD_PREFIX):])
