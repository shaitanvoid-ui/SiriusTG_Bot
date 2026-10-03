"""Interactive login with an encrypted StringSession and hidden code/2FA.

Stop the bot first, then run ``docker compose run --rm bot python -m
userbot.login`` in an interactive terminal. Runtime and CLI hold the same OS
lock. Phone/API values come from ignored .env, never from chat.
"""

from __future__ import annotations

import asyncio
import getpass
import sys
import warnings

from telethon import errors

from core.config import settings
from core.crypto import CryptoError, encrypt
from db.repositories.userbot_session import UserbotSessionRepo
from db.session import SessionLocal, dispose_engine
from userbot.client import (
    TELETHON_OPERATION_ERRORS, SessionInUse, SessionProcessLock,
    _build_client, account_matches,
)


def _hidden_input(prompt: str) -> str:
    # Fail closed instead of getpass's visible-input fallback on a bad PTY.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt)


async def _authorize(client, phone: str) -> None:
    """Use explicit auth calls; Telethon.start prints account display names."""
    await client.connect()
    await client.send_code_request(phone)
    for _ in range(3):
        try:
            await client.sign_in(phone=phone, code=_hidden_input("Код Telegram: "))
            return
        except errors.SessionPasswordNeededError:
            for _ in range(3):
                try:
                    await client.sign_in(password=_hidden_input("Пароль 2FA: "))
                    return
                except errors.PasswordHashInvalidError:
                    print("Пароль не принят. Повторите ввод в терминале.", file=sys.stderr)
            raise errors.PasswordHashInvalidError(request=None)
        except (errors.PhoneCodeEmptyError, errors.PhoneCodeExpiredError,
                errors.PhoneCodeHashEmptyError, errors.PhoneCodeInvalidError):
            print("Код не принят. Повторите ввод в терминале.", file=sys.stderr)
    raise errors.PhoneCodeInvalidError(request=None)


async def _run() -> int:
    if not (settings.tg_api_id and settings.tg_api_hash):
        print("✗ TG_API_ID / TG_API_HASH не заданы в .env", file=sys.stderr)
        return 1
    phone = settings.userbot_phone
    if not phone:
        print("✗ USERBOT_PHONE не задан в .env", file=sys.stderr)
        return 1
    if not sys.stdin.isatty():
        print("✗ Запустите вход в интерактивном терминале.", file=sys.stderr)
        return 1
    try:
        encrypt("userbot-login-encryption-check")
    except CryptoError:
        print("✗ Шифрование сессии недоступно. Проверьте FERNET_KEY.", file=sys.stderr)
        return 1
    process_lock = SessionProcessLock()
    try:
        process_lock.acquire()
    except SessionInUse:
        print("✗ Аккаунт занят другим процессом. Остановите бот перед входом.",
              file=sys.stderr)
        return 1

    client = _build_client("")
    try:
        print("→ Вход в основной аккаунт. Код вводится скрыто в этом терминале.")
        await _authorize(client, phone)
        if not await client.is_user_authorized():
            print("✗ Telegram не подтвердил авторизацию.", file=sys.stderr)
            return 1
        me = await client.get_me()
        if not account_matches(me, phone):
            print("✗ Аккаунт не соответствует USERBOT_PHONE / USERBOT_ACCOUNT_ID. Сессия не сохранена.",
                  file=sys.stderr)
            return 1
        session_enc = encrypt(client.session.save())
        await client.disconnect()
        async with SessionLocal() as session:
            await UserbotSessionRepo(session).upsert(
                phone=phone, session_enc=session_enc, label="main",
            )
            await session.commit()
        print(f"✓ Авторизация проверена: аккаунт отправителя id={me.id}. Сессия зашифрована.")
        return 0
    except (*TELETHON_OPERATION_ERRORS, CryptoError, getpass.GetPassWarning, EOFError) as exc:
        print(f"✗ Вход не завершён ({type(exc).__name__}). Секретные данные не сохранены.",
              file=sys.stderr)
        return 1
    finally:
        try:
            await client.disconnect()
        except TELETHON_OPERATION_ERRORS:
            pass
        process_lock.release()
        await dispose_engine()


def main() -> None:
    try:
        raise SystemExit(asyncio.run(_run()))
    except KeyboardInterrupt:
        print("Вход отменён.", file=sys.stderr)
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
