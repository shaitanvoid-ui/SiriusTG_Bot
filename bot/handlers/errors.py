"""Последний рубеж обработки неожиданных ошибок апдейтов."""
from __future__ import annotations

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

from core.logger import get_logger
from locales.ru import T


router = Router(name="errors")
log = get_logger(__name__)


@router.error()
async def on_unhandled_error(event: ErrorEvent) -> bool:
    exc = event.exception
    log.error(
        "update_unhandled_error",
        update_id=event.update.update_id,
        error_type=type(exc).__name__,
        error=str(exc),
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    callback = event.update.callback_query
    message = event.update.message
    try:
        if callback is not None:
            await callback.answer(T.error_generic, show_alert=True)
        elif message is not None:
            await message.answer(T.error_generic)
    except TelegramAPIError as notify_error:
        log.warning(
            "update_error_notification_failed",
            update_id=event.update.update_id,
            error=str(notify_error),
        )
    return True


__all__ = ["router"]
