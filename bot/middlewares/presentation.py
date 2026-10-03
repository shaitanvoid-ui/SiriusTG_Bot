"""Native rich presentation at the aiogram session boundary."""

from __future__ import annotations

from typing import Any

from aiogram import Bot
from aiogram.client.default import Default
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.exceptions import TelegramBadRequest, TelegramNotFound
from aiogram.methods import EditMessageText, SendMessage, SendRichMessage
from aiogram.types import InlineKeyboardMarkup, InputRichMessage

from core.logger import get_logger
from utils.rich import is_card, render_rich_html


log = get_logger(__name__)


class PresentationMiddleware(BaseRequestMiddleware):
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    async def __call__(self, make_request: Any, bot: Bot, method: Any) -> Any:
        if not self.enabled or not isinstance(method, (SendMessage, EditMessageText)):
            return await make_request(bot, method)
        text = method.text
        mode = bot.default.parse_mode if isinstance(method.parse_mode, Default) else method.parse_mode
        if (
            not text or not is_card(text) or mode != "HTML" or method.entities
            or not isinstance(method.chat_id, int) or method.chat_id <= 0
            or not isinstance(method.reply_markup, InlineKeyboardMarkup)
        ):
            return await make_request(bot, method)

        rich = InputRichMessage(html=render_rich_html(text))
        if isinstance(method, SendMessage):
            # Preserve threads, replies, notification and business routing options.
            values = {name: getattr(method, name) for name in SendRichMessage.model_fields
                      if name != "rich_message" and hasattr(method, name)}
            outgoing = SendRichMessage(rich_message=rich, **values)
        else:
            outgoing = method.model_copy(update={
                "text": None, "parse_mode": None, "entities": None,
                "link_preview_options": None, "rich_message": rich,
            })
        try:
            return await make_request(bot, outgoing)
        except (TelegramBadRequest, TelegramNotFound) as exc:
            description = exc.message.lower()
            unsupported = "method not found" in description or "unknown method" in description
            rich_rejected = "rich" in description and any(
                part in description for part in ("unsupported", "not supported", "can't parse", "cannot parse")
            )
            if not (unsupported or rich_rejected):
                raise
            if unsupported:
                self.enabled = False
            log.warning("rich_presentation_fallback", reason="unsupported" if unsupported else "rejected")
            return await make_request(bot, method)
