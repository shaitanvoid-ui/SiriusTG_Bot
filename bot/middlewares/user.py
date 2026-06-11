from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from db.repositories.user import UserRepo
from services.user import UserService


class UserUpsertMiddleware(BaseMiddleware):
    """Гарантирует, что юзер записан в БД и добавляет его в data['db_user']."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = None
        if isinstance(event, (Message, CallbackQuery)):
            tg_user = event.from_user
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        session = data.get("session")
        if session is None:
            return await handler(event, data)

        service = UserService(UserRepo(session))
        db_user, _created = await service.upsert_from_tg(tg_user)
        data["db_user"] = db_user
        return await handler(event, data)
