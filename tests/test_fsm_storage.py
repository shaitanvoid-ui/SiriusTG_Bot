from __future__ import annotations

from aiogram.fsm.storage.base import StorageKey

from db.fsm_storage import SQLiteFSMStorage


async def test_sqlite_fsm_survives_reopen(tmp_path) -> None:
    path = tmp_path / "fsm.db"
    key = StorageKey(bot_id=1, chat_id=2, user_id=3, destiny="default")

    first = SQLiteFSMStorage(path)
    await first.set_state(key, "ReviewStates:text")
    await first.set_data(key, {"rating": 5, "text": "Очень хорошо"})
    await first.close()

    reopened = SQLiteFSMStorage(path)
    assert await reopened.get_state(key) == "ReviewStates:text"
    assert await reopened.get_data(key) == {"rating": 5, "text": "Очень хорошо"}
    await reopened.close()


async def test_sqlite_fsm_update_data_is_merged(tmp_path) -> None:
    storage = SQLiteFSMStorage(tmp_path / "fsm.db")
    key = StorageKey(bot_id=1, chat_id=2, user_id=3, destiny="default")
    await storage.set_data(key, {"a": 1})
    assert await storage.update_data(key, {"b": 2}) == {"a": 1, "b": 2}
    assert await storage.get_data(key) == {"a": 1, "b": 2}
    await storage.close()
