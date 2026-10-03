"""Inaccessible/inline-origin messages cannot operate a private chat screen."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from locales.ru import T


class CallbackAccessMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject, data: dict[str, Any]) -> Any:
        if isinstance(event, CallbackQuery) and not isinstance(event.message, Message):
            await event.answer(T.stale_screen_alert, show_alert=True)
            return None
        return await handler(event, data)
