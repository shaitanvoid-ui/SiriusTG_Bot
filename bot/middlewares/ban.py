from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from db.models import User
from locales.ru import T
from core.config import settings


class BanCheckMiddleware(BaseMiddleware):
    """Блокирует апдейты от забаненных. Shadow-ban проходит дальше (но без наград — на уровне сервисов)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db_user: User | None = data.get("db_user")
        # Владелец не должен потерять доступ к аварийному управлению даже при
        # ошибочном флаге в БД или неудачном административном действии.
        actor = getattr(event, "from_user", None)
        if actor is not None and actor.id == settings.owner_id:
            return await handler(event, data)
        if db_user is not None and db_user.is_banned:
            if isinstance(event, Message):
                await event.answer(T.banned)
            elif isinstance(event, CallbackQuery):
                await event.answer(T.banned, show_alert=True)
            return None
        return await handler(event, data)
