"""Ignore only a harmless identical edit; report real Telegram failures."""

from contextlib import contextmanager
from collections.abc import Iterator

from aiogram.exceptions import TelegramBadRequest


@contextmanager
def ignore_unchanged() -> Iterator[None]:
    try:
        yield
    except TelegramBadRequest as exc:
        if "message is not modified" not in exc.message.lower():
            raise
