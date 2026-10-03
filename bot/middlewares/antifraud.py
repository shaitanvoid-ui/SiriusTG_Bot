"""Global durable limit precedes handler/database middleware and any network I/O."""
from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from core.config import settings
from bot.middlewares import db as middleware_db
from locales.ru import T
from services.antifraud import AntifraudService


class AntifraudMiddleware(BaseMiddleware):
    def __init__(self, session_factory=None):
        self.session_factory = session_factory

    async def __call__(self, handler, event, data):
        actor = event.from_user if isinstance(event, (Message, CallbackQuery)) else None
        if actor is None or actor.is_bot or actor.id in settings.all_admin_ids:
            return await handler(event, data)
        async with (self.session_factory or middleware_db.SessionLocal)() as session:
            admission = await AntifraudService(session).observe(
                actor_tg_id=actor.id, click=isinstance(event, CallbackQuery) and event.data == "clk:tap",
            )
            await session.commit()
        if not admission.allowed:
            text = T.antifraud_rate_limited.format(seconds=admission.retry_seconds)
            if isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
            elif admission.first_notice:
                await event.answer(text)
            return None
        return await handler(event, data)
