"""Explicitly update public bot copy; never runs automatically at startup."""

from __future__ import annotations

import asyncio
import json

from aiogram import Bot

from core.config import settings
from locales.ru import T


async def main() -> None:
    async with Bot(settings.bot_token) as bot:
        await bot.set_my_name(T.bot_public_name)
        await bot.set_my_description(T.bot_public_description)
        await bot.set_my_short_description(T.bot_public_short)
        name = await bot.get_my_name()
        description = await bot.get_my_description()
        short = await bot.get_my_short_description()
        assert name.name == T.bot_public_name
        assert description.description == T.bot_public_description
        assert short.short_description == T.bot_public_short
        print(json.dumps({"public_name": name.name, "description_verified": True,
                          "short_description_verified": True}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        raise SystemExit(f"Public profile update failed: {type(error).__name__}") from None
