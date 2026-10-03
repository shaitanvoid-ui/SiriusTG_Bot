from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from db.session import SessionLocal
from services.settings import SettingsService


class DbSessionMiddleware(BaseMiddleware):
    """Открывает AsyncSession на каждый апдейт и кладёт в data['session']."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with SessionLocal() as session:
            data["session"] = session
            data["db_session"] = session  # alias
            try:
                await SettingsService(session).preload()
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
