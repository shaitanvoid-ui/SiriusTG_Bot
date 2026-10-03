"""Leaving a dialogue clears its pending input/confirmation data."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject


ROOT_SCREENS = frozenset({
    "nav:menu", "sec:earn", "sec:help", "prof:open", "day:open", "ref:open",
    "bns:open", "clk:open", "whl:open", "tsk:list", "ach:open", "top:open",
    "sup:open", "promo:open", "ins:open", "rev:intro", "ntf:open", "hist:open", "pa:open",
    "gift:open", "gift:history",
})


class NavigationStateMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject, data: dict[str, Any]) -> Any:
        if isinstance(event, CallbackQuery) and event.data in ROOT_SCREENS and data.get("state") is not None:
            await data["state"].clear()
            data["raw_state"] = None
        return await handler(event, data)
