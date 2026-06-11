"""Утилиты для построения t.me-ссылок и кэша bot.username."""

from __future__ import annotations

import urllib.parse

from aiogram import Bot


_bot_username: str | None = None


async def get_bot_username(bot: Bot) -> str:
    """Кэшированный username бота — без префикса '@'."""
    global _bot_username
    if _bot_username is None:
        me = await bot.get_me()
        _bot_username = me.username or ""
    return _bot_username


async def build_referral_link(bot: Bot, tg_id: int) -> str:
    uname = await get_bot_username(bot)
    if not uname:
        return ""
    return f"https://t.me/{uname}?start=r{tg_id}"


def build_share_url(link: str, text: str) -> str:
    """Telegram share-URL: открывает выбор чата для пересылки."""
    return (
        "https://t.me/share/url?"
        + urllib.parse.urlencode({"url": link, "text": text})
    )
