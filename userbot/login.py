"""Одноразовый интерактивный логин userbot.

Запуск (интерактивно, в терминале):
    docker compose run --rm bot python -m userbot.login

Спросит код из Telegram (и пароль 2FA, если включён), создаст StringSession,
зашифрует её Fernet-ключом и положит в БД (userbot_sessions). После этого бот
сам поднимет сессию при старте/первом обращении.

Требует заранее: миграции применены, в .env заданы TG_API_ID / TG_API_HASH /
USERBOT_PHONE.
"""

from __future__ import annotations

import asyncio
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession

from core.config import settings
from core.crypto import encrypt
from db.repositories.userbot_session import UserbotSessionRepo
from db.session import SessionLocal, dispose_engine
from userbot.client import (
    APP_VERSION,
    DEVICE_MODEL,
    LANG_CODE,
    SYSTEM_LANG_CODE,
    SYSTEM_VERSION,
)


async def _run() -> int:
    if not (settings.tg_api_id and settings.tg_api_hash):
        print("✗ TG_API_ID / TG_API_HASH не заданы в .env", file=sys.stderr)
        return 1
    phone = settings.userbot_phone
    if not phone:
        print("✗ USERBOT_PHONE не задан в .env", file=sys.stderr)
        return 1

    client = TelegramClient(
        StringSession(),
        settings.tg_api_id,
        settings.tg_api_hash,
        device_model=DEVICE_MODEL,
        system_version=SYSTEM_VERSION,
        app_version=APP_VERSION,
        lang_code=LANG_CODE,
        system_lang_code=SYSTEM_LANG_CODE,
    )

    print(f"→ Логиним userbot {phone}. Жди код в Telegram…")
    await client.start(phone=lambda: phone)

    me = await client.get_me()
    session_str = client.session.save()
    await client.disconnect()

    async with SessionLocal() as session:
        await UserbotSessionRepo(session).upsert(
            phone=phone, session_enc=encrypt(session_str), label="main"
        )
        await session.commit()

    await dispose_engine()
    uname = getattr(me, "username", None)
    print(f"✓ Готово. userbot: id={me.id} @{uname}. Сессия сохранена в БД.")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
