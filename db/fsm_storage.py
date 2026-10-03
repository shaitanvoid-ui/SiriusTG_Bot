"""Персистентное SQLite-хранилище FSM для aiogram.

Состояния диалогов больше не исчезают при перезапуске контейнера. Отдельный
небольшой файл снижает конкуренцию с основной экономической БД.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import aiosqlite
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

from core.logger import get_logger


log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS fsm_states (
    bot_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    thread_id INTEGER NOT NULL,
    business_connection_id TEXT NOT NULL,
    destiny TEXT NOT NULL,
    state TEXT,
    data TEXT NOT NULL DEFAULT '{}',
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (
        bot_id, chat_id, user_id, thread_id, business_connection_id, destiny
    )
)
"""


class SQLiteFSMStorage(BaseStorage):
    """Минимальное надёжное FSM-хранилище без внешнего Redis."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._connection: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(key: StorageKey) -> tuple[int, int, int, int, str, str]:
        return (
            key.bot_id,
            key.chat_id,
            key.user_id,
            key.thread_id if key.thread_id is not None else -1,
            key.business_connection_id or "",
            key.destiny,
        )

    async def _connect_unlocked(self) -> aiosqlite.Connection:
        if self._connection is not None:
            return self._connection
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = await aiosqlite.connect(self.path)
        await connection.execute("PRAGMA journal_mode=WAL")
        await connection.execute("PRAGMA synchronous=NORMAL")
        await connection.execute("PRAGMA busy_timeout=5000")
        await connection.execute(_SCHEMA)
        # Пустые состояния и забытые незавершённые флоу старше 30 дней не
        # должны бесконечно раздувать служебную БД.
        cutoff = int(time.time()) - 30 * 24 * 60 * 60
        await connection.execute(
            "DELETE FROM fsm_states WHERE updated_at < ?", (cutoff,)
        )
        await connection.commit()
        self._connection = connection
        return connection

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        state_value = state.state if isinstance(state, State) else state
        async with self._lock:
            connection = await self._connect_unlocked()
            await connection.execute(
                """
                INSERT INTO fsm_states
                    (bot_id, chat_id, user_id, thread_id, business_connection_id,
                     destiny, state, data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, '{}', ?)
                ON CONFLICT (
                    bot_id, chat_id, user_id, thread_id,
                    business_connection_id, destiny
                ) DO UPDATE SET state = excluded.state, updated_at = excluded.updated_at
                """,
                (*self._key(key), state_value, int(time.time())),
            )
            await connection.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        async with self._lock:
            connection = await self._connect_unlocked()
            cursor = await connection.execute(
                """
                SELECT state FROM fsm_states
                WHERE bot_id=? AND chat_id=? AND user_id=? AND thread_id=?
                  AND business_connection_id=? AND destiny=?
                """,
                self._key(key),
            )
            row = await cursor.fetchone()
            await cursor.close()
            return str(row[0]) if row and row[0] is not None else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        async with self._lock:
            connection = await self._connect_unlocked()
            await connection.execute(
                """
                INSERT INTO fsm_states
                    (bot_id, chat_id, user_id, thread_id, business_connection_id,
                     destiny, state, data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
                ON CONFLICT (
                    bot_id, chat_id, user_id, thread_id,
                    business_connection_id, destiny
                ) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at
                """,
                (*self._key(key), payload, int(time.time())),
            )
            await connection.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        async with self._lock:
            connection = await self._connect_unlocked()
            cursor = await connection.execute(
                """
                SELECT data FROM fsm_states
                WHERE bot_id=? AND chat_id=? AND user_id=? AND thread_id=?
                  AND business_connection_id=? AND destiny=?
                """,
                self._key(key),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return {}
        try:
            value = json.loads(row[0])
        except (TypeError, json.JSONDecodeError) as exc:
            log.warning("fsm_data_decode_failed", error=str(exc))
            return {}
        return dict(value) if isinstance(value, dict) else {}

    async def update_data(
        self, key: StorageKey, data: dict[str, Any]
    ) -> dict[str, Any]:
        async with self._lock:
            connection = await self._connect_unlocked()
            cursor = await connection.execute(
                """
                SELECT data FROM fsm_states
                WHERE bot_id=? AND chat_id=? AND user_id=? AND thread_id=?
                  AND business_connection_id=? AND destiny=?
                """,
                self._key(key),
            )
            row = await cursor.fetchone()
            await cursor.close()
            current: dict[str, Any] = {}
            if row:
                try:
                    decoded = json.loads(row[0])
                    if isinstance(decoded, dict):
                        current = decoded
                except (TypeError, json.JSONDecodeError):
                    current = {}
            current.update(data)
            payload = json.dumps(current, ensure_ascii=False, separators=(",", ":"))
            await connection.execute(
                """
                INSERT INTO fsm_states
                    (bot_id, chat_id, user_id, thread_id, business_connection_id,
                     destiny, state, data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
                ON CONFLICT (
                    bot_id, chat_id, user_id, thread_id,
                    business_connection_id, destiny
                ) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at
                """,
                (*self._key(key), payload, int(time.time())),
            )
            await connection.commit()
            return current.copy()

    async def close(self) -> None:
        async with self._lock:
            if self._connection is not None:
                await self._connection.close()
                self._connection = None


__all__ = ["SQLiteFSMStorage"]
