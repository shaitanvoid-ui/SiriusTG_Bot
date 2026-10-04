"""Reject public/foreign UI destinations before FSM, DB or sender access."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import AnswerCallbackQuery

import bot.middlewares.db as middleware_db
from locales.ru import T
from main import _setup_middlewares


def message(actor_id, chat_id, chat_type, *, text="/start", date=None, is_bot=False):
    return {
        "message_id": 1,
        "date": int(datetime.now(timezone.utc).timestamp()) if date is None else date,
        "chat": {"id": chat_id, "type": chat_type},
        "from": {"id": actor_id, "is_bot": is_bot, "first_name": "Test"},
        "text": text,
        "entities": [{"type": "bot_command", "offset": 0, "length": len(text)}],
    }


@pytest.mark.parametrize("chat_id,chat_type", [(-10077, "supergroup"), (-77, "group"), (78, "private")])
@pytest.mark.parametrize("command", ["/start", "/admin", "private FSM reply"])
async def test_rejected_messages_never_enter_fsm_or_database(monkeypatch, chat_id, chat_type, command):
    bot = Bot("1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE")
    api = AsyncMock(return_value=True)
    monkeypatch.setattr(bot.session, "make_request", api)
    database = Mock(side_effect=AssertionError("Rejected update entered database"))
    monkeypatch.setattr(middleware_db, "SessionLocal", database)
    storage = MemoryStorage()
    read_state = AsyncMock(side_effect=AssertionError("Rejected update entered FSM"))
    monkeypatch.setattr(storage, "get_state", read_state)
    dispatcher = Dispatcher(storage=storage)
    _setup_middlewares(dispatcher)
    try:
        await dispatcher.feed_raw_update(bot, {"update_id": 1, "message": message(77, chat_id, chat_type, text=command)})
        read_state.assert_not_awaited()
        database.assert_not_called()
        api.assert_not_awaited()
    finally:
        await storage.close()
        await bot.session.close()


@pytest.mark.parametrize("destination", ["group", "supergroup", "foreign_private", "inaccessible", "inline", "bot_actor"])
@pytest.mark.parametrize("action", ["prof:open", "gift:history", "adm:gift:account", "adm:root"])
async def test_rejected_callbacks_only_answer_an_alert(monkeypatch, destination, action):
    bot = Bot("1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE")
    api = AsyncMock(return_value=True)
    monkeypatch.setattr(bot.session, "make_request", api)
    database = Mock(side_effect=AssertionError("Rejected callback entered database"))
    monkeypatch.setattr(middleware_db, "SessionLocal", database)
    storage = MemoryStorage()
    read_state = AsyncMock(side_effect=AssertionError("Rejected callback entered FSM"))
    monkeypatch.setattr(storage, "get_state", read_state)
    dispatcher = Dispatcher(storage=storage)
    _setup_middlewares(dispatcher)
    callback = {
        "id": "test", "chat_instance": "test", "data": action,
        "from": {"id": 1, "is_bot": destination == "bot_actor", "first_name": "Owner"},
    }
    if destination == "inline":
        callback["inline_message_id"] = "inline"
    else:
        chat_type = destination if destination in {"group", "supergroup"} else "private"
        chat_id = -77 if chat_type != "private" else (2 if destination == "foreign_private" else 1)
        callback["message"] = message(1, chat_id, chat_type, date=0 if destination == "inaccessible" else None)
    try:
        await dispatcher.feed_raw_update(bot, {"update_id": 1, "callback_query": callback})
        read_state.assert_not_awaited()
        database.assert_not_called()
        api.assert_awaited_once()
        response = api.call_args.args[1]
        assert isinstance(response, AnswerCallbackQuery)
        assert response.show_alert is True
        assert response.text == (T.stale_screen_alert if destination in {"inaccessible", "inline"} else T.private_chat_only)
    finally:
        await storage.close()
        await bot.session.close()
