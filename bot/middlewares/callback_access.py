"""Only the actor's accessible private chat can enter the bot's UI pipelines."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from locales.ru import T


class CallbackAccessMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject, data: dict[str, Any]) -> Any:
        # At Update level this runs before FSM storage. Observer registrations
        # retain the same boundary for direct Message/CallbackQuery dispatch.
        source = (event.message or event.callback_query) if isinstance(event, Update) else event
        if isinstance(source, CallbackQuery):
            message = source.message
            if not isinstance(message, Message) or message.date.timestamp() <= 0:
                await source.answer(T.stale_screen_alert, show_alert=True)
                return None
            if not self._private_actor_chat(message, source.from_user):
                await source.answer(T.private_chat_only, show_alert=True)
                return None
        elif isinstance(source, Message):
            if not self._private_actor_chat(source, source.from_user):
                return None
        return await handler(event, data)

    @staticmethod
    def _private_actor_chat(message: Message, actor: Any) -> bool:
        return actor is not None and not actor.is_bot and message.chat.type == ChatType.PRIVATE and message.chat.id == actor.id
