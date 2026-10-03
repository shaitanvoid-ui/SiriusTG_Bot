"""Gate-middlewares (terms / captcha / subs) для ready-пользовательских роутеров.

Onboarding и административные роутеры подключены вне ready и не блокируются.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from db.models import User
from locales.ru import T


class TermsGateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db_user: User | None = data.get("db_user")
        if db_user is not None and db_user.accepted_terms_at is None:
            await _reject(event, T.gate_terms_required)
            return None
        return await handler(event, data)


class CaptchaGateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db_user: User | None = data.get("db_user")
        if db_user is not None and db_user.captcha_passed_at is None:
            await _reject(event, T.gate_captcha_required)
            return None
        return await handler(event, data)


class SubGateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db_user: User | None = data.get("db_user")
        if db_user is not None and db_user.subs_passed_at is None:
            await _reject(event, T.gate_subs_required)
            return None
        return await handler(event, data)


async def _reject(event: TelegramObject, text: str) -> None:
    if isinstance(event, Message):
        await event.answer(text)
    elif isinstance(event, CallbackQuery):
        await event.answer(text, show_alert=True)
