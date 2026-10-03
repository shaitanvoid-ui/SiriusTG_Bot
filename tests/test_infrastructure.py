from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from aiohttp.test_utils import TestClient, TestServer
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy.exc import IntegrityError

from core.health import (
    build_app,
    check_application_readiness,
    set_runtime_ready,
)
from db.engine import SQLITE_BUSY_TIMEOUT_MS, create_app_engine
from db.models import Base


PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def _request(path: str, *, ready: bool | Exception) -> tuple[int, dict[str, str]]:
    async def readiness_check() -> bool:
        if isinstance(ready, Exception):
            raise ready
        return ready

    client = TestClient(TestServer(build_app(readiness_check=readiness_check)))
    await client.start_server()
    try:
        response = await client.get(path)
        return response.status, await response.json()
    finally:
        await client.close()


async def test_health_is_liveness_only() -> None:
    status, payload = await _request("/health", ready=False)
    assert status == 200
    assert payload == {"status": "ok"}


async def test_readiness_reports_database_state_without_details() -> None:
    status, payload = await _request("/ready", ready=True)
    assert status == 200
    assert payload == {"status": "ready"}

    status, payload = await _request("/ready", ready=RuntimeError("sensitive DB detail"))
    assert status == 503
    assert payload == {"status": "unavailable"}
    assert "sensitive" not in str(payload)


async def test_application_readiness_requires_started_runtime(monkeypatch) -> None:
    async def database_ready() -> bool:
        return True

    monkeypatch.setattr("core.health.check_database_readiness", database_ready)
    set_runtime_ready(False)
    assert await check_application_readiness() is False

    set_runtime_ready(True)
    try:
        assert await check_application_readiness() is True
    finally:
        # Не переносим глобальный runtime-флаг в следующие тесты.
        set_runtime_ready(False)


async def test_sqlite_pragmas_and_foreign_keys(tmp_path: Path) -> None:
    db_file = tmp_path / "pragmas.db"
    engine = create_app_engine(f"sqlite+aiosqlite:///{db_file}")
    try:
        async with engine.connect() as connection:
            foreign_keys = await connection.exec_driver_sql("PRAGMA foreign_keys")
            busy_timeout = await connection.exec_driver_sql("PRAGMA busy_timeout")
            journal_mode = await connection.exec_driver_sql("PRAGMA journal_mode")
            assert foreign_keys.scalar_one() == 1
            assert busy_timeout.scalar_one() == SQLITE_BUSY_TIMEOUT_MS
            assert str(journal_mode.scalar_one()).lower() == "wal"

            await connection.exec_driver_sql("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
            await connection.exec_driver_sql(
                "CREATE TABLE child (parent_id INTEGER REFERENCES parent(id))"
            )
            await connection.commit()

            with pytest.raises(IntegrityError):
                await connection.exec_driver_sql("INSERT INTO child(parent_id) VALUES (404)")
            await connection.rollback()
    finally:
        await engine.dispose()


def test_alembic_upgrade_head_on_empty_database(tmp_path: Path) -> None:
    db_file = (tmp_path / "alembic.db").resolve()
    env = os.environ.copy()
    env.update(
        {
            "ENV": "test",
            "BOT_TOKEN": "1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE",
            "OWNER_ID": "1",
            "ADMIN_IDS": "",
            "LOG_CHANNEL_ID": "",
            "FERNET_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_file.as_posix()}",
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    expected_heads = set(ScriptDirectory.from_config(config).get_heads())

    with sqlite3.connect(db_file) as connection:
        current_heads = {
            str(row[0]) for row in connection.execute("SELECT version_num FROM alembic_version")
        }
        table_names = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert current_heads == expected_heads
    assert set(Base.metadata.tables).issubset(table_names)


async def test_shutdown_attempts_every_cleanup_step(monkeypatch) -> None:
    import main as app_main

    calls: list[str] = []

    async def fail_broadcast() -> None:
        calls.append("broadcast")
        raise RuntimeError("broadcast cleanup failed")

    async def disconnect_userbot() -> None:
        calls.append("userbot")

    async def stop_health(_runner: object) -> None:
        calls.append("health")

    async def dispose_database() -> None:
        calls.append("database")

    class FakeScheduler:
        def shutdown(self, *, wait: bool) -> None:
            assert wait is False
            calls.append("scheduler")
            raise RuntimeError("scheduler cleanup failed")

    class FakeSession:
        async def close(self) -> None:
            calls.append("bot_session")

    class FakeBot:
        session = FakeSession()

    monkeypatch.setattr(app_main, "shutdown_active_broadcast", fail_broadcast)
    monkeypatch.setattr(app_main.userbot_client, "disconnect", disconnect_userbot)
    monkeypatch.setattr(app_main, "stop_health_server", stop_health)
    monkeypatch.setattr(app_main, "dispose_engine", dispose_database)

    shutdown = app_main._build_shutdown(object(), FakeScheduler())
    await shutdown(FakeBot())

    assert set(calls) == {
        "broadcast",
        "scheduler",
        "userbot",
        "health",
        "bot_session",
        "database",
    }
