"""Этап 13: авто-бэкап БД, ежедневный дайджест, рендер алертов."""

from __future__ import annotations

import os
import sqlite3

import workers.daily_digest as digest_mod
import workers.db_backup as backup_mod
from services.admin_stats import DashboardStats
from services.settings import SettingsService
from tests.helpers import create_user


class FakeBot:
    def __init__(self) -> None:
        self.documents: list[tuple[int, str, str]] = []  # (chat_id, filename, caption)
        self.messages: list[tuple[int, str]] = []

    async def send_document(self, chat_id, document, caption=None, **kw):
        self.documents.append((chat_id, document.filename, caption or ""))

    async def send_message(self, chat_id, text, **kw):
        self.messages.append((chat_id, text))


# ---------- бэкап ----------

def _make_src_db(tmp_path) -> str:
    src = str(tmp_path / "src.db")
    conn = sqlite3.connect(src)
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("INSERT INTO t VALUES (42)")
    conn.commit()
    conn.close()
    return src


async def test_make_backup_file_is_consistent_copy(tmp_path):
    src = _make_src_db(tmp_path)
    dst = await backup_mod.make_backup_file(src)
    try:
        conn = sqlite3.connect(dst)
        row = conn.execute("SELECT x FROM t").fetchone()
        conn.close()
        assert row == (42,)
    finally:
        os.remove(dst)


async def test_make_backup_file_removes_partial_copy(tmp_path, monkeypatch):
    src = _make_src_db(tmp_path)

    def fail_copy(_src: str, _dst: str) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr(backup_mod, "_copy_sqlite", fail_copy)
    try:
        await backup_mod.make_backup_file(src, temp_dir=str(tmp_path))
    except OSError:
        pass
    else:
        raise AssertionError("backup failure was not propagated")

    assert list(tmp_path.glob("bot_backup_*.db")) == []


async def test_run_db_backup_sends_document(tmp_path, session, session_factory, monkeypatch):
    src = _make_src_db(tmp_path)
    monkeypatch.setattr(backup_mod, "SessionLocal", session_factory)
    monkeypatch.setattr(backup_mod, "db_file_path", lambda: src)
    monkeypatch.setattr(backup_mod.app_settings, "log_channel_id", -100123)

    bot = FakeBot()
    await backup_mod.run_db_backup(bot)

    assert len(bot.documents) == 1
    chat_id, filename, caption = bot.documents[0]
    assert chat_id == -100123
    assert filename.startswith("bot_") and filename.endswith(".db.fernet")
    assert "Бэкап" in caption


async def test_run_db_backup_respects_disabled(tmp_path, session, session_factory, monkeypatch):
    src = _make_src_db(tmp_path)
    await SettingsService(session).set("backup.enabled", False)
    await session.commit()
    monkeypatch.setattr(backup_mod, "SessionLocal", session_factory)
    monkeypatch.setattr(backup_mod, "db_file_path", lambda: src)
    monkeypatch.setattr(backup_mod.app_settings, "log_channel_id", -100123)

    bot = FakeBot()
    await backup_mod.run_db_backup(bot)
    assert bot.documents == []


def test_db_file_path_parses_sqlite_url(monkeypatch):
    monkeypatch.setattr(
        backup_mod.app_settings, "database_url", "sqlite+aiosqlite:///./data/bot.db"
    )
    assert backup_mod.db_file_path() == "./data/bot.db"


# ---------- дайджест ----------

def _stats(**kw) -> DashboardStats:
    base = dict(
        users_total=10, users_passed=7, users_banned=1, users_shadow=0,
        users_new_today=3, balance_total=55.5, debt_total=1.25,
        clicks_today=140, bonuses_today=4, spins_today=9, tasks_today=2,
        refs_today=5, reviews_pending=1,
    )
    base.update(kw)
    return DashboardStats(**base)


def test_render_digest_contains_metrics():
    text = digest_mod.render_digest(_stats())
    assert "10" in text and "55.50" in text and "140" in text
    assert "Обзор за сутки" in text


async def test_run_daily_digest_sends_message(session, session_factory, monkeypatch):
    await create_user(session, tg_id=999001101, balance=5.0)
    await session.commit()
    monkeypatch.setattr(digest_mod, "SessionLocal", session_factory)
    monkeypatch.setattr(digest_mod.app_settings, "log_channel_id", -100123)

    bot = FakeBot()
    await digest_mod.run_daily_digest(bot)
    assert len(bot.messages) == 1
    assert bot.messages[0][0] == -100123


async def test_run_daily_digest_respects_disabled(session, session_factory, monkeypatch):
    await SettingsService(session).set("digest.enabled", False)
    await session.commit()
    monkeypatch.setattr(digest_mod, "SessionLocal", session_factory)
    monkeypatch.setattr(digest_mod.app_settings, "log_channel_id", -100123)

    bot = FakeBot()
    await digest_mod.run_daily_digest(bot)
    assert bot.messages == []
