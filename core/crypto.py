"""Шифрование чувствительных данных (Telethon-сессии) через Fernet.

Ключ берётся из settings.fernet_key (.env). Без ключа — явная ошибка,
чтобы не записать сессию в открытом виде.
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


def decrypt(token: str) -> str:
    """Расшифровывает токен. При повреждении/неверном ключе — CryptoError."""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError) as exc:
        raise CryptoError("Не удалось расшифровать данные") from exc
