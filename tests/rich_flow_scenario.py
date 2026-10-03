"""Isolated Dispatcher integration scenario with a recording Telegram session."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageText, GetMe, SendMessage, SendRichMessage
from aiogram.types import Chat, Message, RichMessage, User as TelegramUser
from sqlalchemy.ext.asyncio import async_sessionmaker

import bot.middlewares.db as middleware_db
from bot.handlers import get_root_router
from bot.handlers import wheel
from bot.middlewares.presentation import PresentationMiddleware
from db.base import Base, utcnow
from db.engine import create_app_engine
from db.fsm_storage import SQLiteFSMStorage
from db.repositories.setting import SettingRepo
from db.repositories.user import UserRepo
from main import _setup_middlewares
from services.settings import DEFAULTS
from tests.helpers import create_user


class RecordingSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.message = None

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        raise AssertionError("External media requests are forbidden in this scenario")
        yield b""  # pragma: no cover - defines the asynchronous iterator protocol

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, GetMe):
            return TelegramUser(id=1234567890, is_bot=True, first_name="SIRIUS", username="sirius_test_bot")
        if isinstance(method, AnswerCallbackQuery):
            return True
        assert isinstance(method, (SendMessage, SendRichMessage, EditMessageText)), type(method)
        rich = getattr(method, "rich_message", None)
        blocks = []
        assert not rich or rich.media is None
        self.message = Message(message_id=getattr(method, "message_id", None) or 1,
                               date=datetime.now(timezone.utc), chat=Chat(id=777301, type="private"),
                               text=getattr(method, "text", None),
                               rich_message=RichMessage(blocks=blocks) if rich else None,
                               reply_markup=method.reply_markup).as_(bot)
        return self.message


async def run(folder: Path):
    folder.mkdir(exist_ok=True)
    engine = create_app_engine(f"sqlite+aiosqlite:///{folder / 'flow.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        for key, (value, description) in DEFAULTS.items():
            await SettingRepo(session).set(key, value, description)
        await SettingRepo(session).set("bonus.bio_required", False)
        await create_user(session, tg_id=777301, balance=10, first_name="<Анна>", accepted_terms_at=utcnow(),
                          captcha_passed_at=utcnow(), subs_passed_at=utcnow())
        await session.commit()
    middleware_db.SessionLocal = factory
    async def no_animation(callback):
        pass
    wheel._play_spin_animation = no_animation
    session_api = RecordingSession()
    session_api.middleware(PresentationMiddleware())
    bot = Bot("1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE", session=session_api,
              default=DefaultBotProperties(parse_mode="HTML"))
    dispatcher = Dispatcher(storage=SQLiteFSMStorage(str(folder / "fsm.db")))
    _setup_middlewares(dispatcher)
    dispatcher.include_router(get_root_router())
    actor = {"id": 777301, "is_bot": False, "first_name": "<Анна>"}
    update_id = 1
    async def start():
        nonlocal update_id
        await dispatcher.feed_raw_update(bot, {"update_id": update_id, "message": {
            "message_id": update_id + 10, "date": int(datetime.now(timezone.utc).timestamp()),
            "chat": {"id": 777301, "type": "private"}, "from": actor,
            "text": "/start", "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
        }})
        update_id += 1
    async def tap(data):
        nonlocal update_id
        await dispatcher.feed_raw_update(bot, {"update_id": update_id, "callback_query": {
            "id": f"callback_{update_id}", "from": actor, "chat_instance": "flow",
            "message": session_api.message.model_dump(mode="json", exclude_none=True), "data": data,
        }})
        update_id += 1
    try:
        await start()
        assert isinstance(session_api.calls[-1], SendRichMessage)
        assert "&lt;Анна&gt;" in session_api.calls[-1].rich_message.html
        await tap("day:open")
        assert session_api.calls[-1].rich_message is not None
        await tap("bns:claim")
        await tap("bns:claim")
        async with factory() as session:
            user = await UserRepo(session).get_by_tg_id(777301)
            assert round(user.balance, 2) == 10.5
            assert user.bonus_streak == 1
        await tap("whl:spin:free")
        async with factory() as session:
            user = await UserRepo(session).get_by_tg_id(777301)
            balance = user.balance
        await tap("whl:spin:free")
        async with factory() as session:
            user = await UserRepo(session).get_by_tg_id(777301)
            assert user.balance == balance
        await tap("whl:confirm")
        confirmation = session_api.message.reply_markup.inline_keyboard[0][0].callback_data
        assert confirmation.startswith("whl:paid:")
        await tap(confirmation)
        async with factory() as session:
            paid_balance = (await UserRepo(session).get_by_tg_id(777301)).balance
        await tap(confirmation)
        async with factory() as session:
            assert (await UserRepo(session).get_by_tg_id(777301)).balance == paid_balance
        await tap("prof:open")
        await tap("ref:open")
        assert session_api.message.reply_markup.inline_keyboard[0][0].copy_text.text.endswith("?start=r777301")
        await tap("unknown:stale")
        assert isinstance(session_api.calls[-1], AnswerCallbackQuery)
        await start()
        assert session_api.calls[-1].rich_message.media is None
        assert "<img" not in session_api.calls[-1].rich_message.html
        print(f"Dispatcher flow passed: {update_id-1} updates, {len(session_api.calls)} mocked API requests, no network")
    finally:
        await dispatcher.storage.close()
        await engine.dispose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run(Path(sys.argv[1])))
