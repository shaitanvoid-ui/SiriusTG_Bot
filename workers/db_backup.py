"""db_backup: авто-бэкап SQLite в LOG_CHANNEL_ID (Этап 13).

Каждые `backup.interval_hours` (default 6) снимаем консистентную копию БД
через sqlite3 backup API (безопасно при живых подключениях), отправляем
документом в лог-канал и удаляем временный файл.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import tempfile

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.config import settings as app_settings
from core.logger import get_logger
from db.session import SessionLocal
from locales.ru import T
from services.settings import SettingsService
from utils.tz import now_msk
from utils.backup_crypto import encrypt_file


log = get_logger(__name__)


def db_file_path() -> str | None:
    """Путь к файлу SQLite из DATABASE_URL (None — не sqlite)."""
    url = app_settings.database_url
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return None
    return url[len(prefix):]


def _copy_sqlite(src: str, dst: str) -> None:
    """Консистентная копия через backup API (блокирующая — звать в to_thread)."""
    src_conn = sqlite3.connect(src)
    try:
        dst_conn = sqlite3.connect(dst)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()


async def make_backup_file(src: str, *, temp_dir: str | None = None) -> str:
    """Снимает копию БД во временный файл, возвращает путь к нему."""
    fd, dst = tempfile.mkstemp(prefix="bot_backup_", suffix=".db", dir=temp_dir)
    os.close(fd)
    completed = False
    try:
        await asyncio.to_thread(_copy_sqlite, src, dst)
        completed = True
    finally:
        if not completed:
            _remove_quiet(dst)
    return dst


async def encrypt_backup_file(src: str, *, temp_dir: str | None = None) -> str:
    """Создаёт Fernet-зашифрованную копию перед отправкой во внешний канал."""
    fd, dst = tempfile.mkstemp(
        prefix="bot_backup_", suffix=".db.fernet", dir=temp_dir
    )
    os.close(fd)
    completed = False
    try:
        await asyncio.to_thread(encrypt_file, src, dst)
        completed = True
    finally:
        if not completed:
            _remove_quiet(dst)
    return dst


async def run_db_backup(bot: Bot) -> None:
    """Один прогон: копия БД → документ в лог-канал."""
    async with SessionLocal() as session:
        enabled = await SettingsService(session).get_bool("backup.enabled", True)
    if not enabled:
        return
    if app_settings.log_channel_id is None:
        log.warning("db_backup_skipped", reason="no_log_channel")
        return
    src = db_file_path()
    if src is None or not os.path.exists(src):
        log.warning("db_backup_skipped", reason="db_file_not_found", src=src)
        return

    plain = await make_backup_file(src)
    encrypted: str | None = None
    try:
        encrypted = await encrypt_backup_file(plain)
        stamp = now_msk().strftime("%Y-%m-%d_%H-%M")
        size_kb = os.path.getsize(encrypted) // 1024
        try:
            await bot.send_document(
                app_settings.log_channel_id,
                FSInputFile(encrypted, filename=f"bot_{stamp}.db.fernet"),
                caption=T.log_backup_caption.format(stamp=stamp, size_kb=size_kb),
            )
            log.info("db_backup_sent", size_kb=size_kb)
        except TelegramAPIError:
            log.exception("db_backup_send_failed")
            raise
    finally:
        _remove_quiet(plain)
        if encrypted is not None:
            _remove_quiet(encrypted)


def _remove_quiet(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def register_jobs(scheduler: AsyncIOScheduler, bot: Bot, *, interval_hours: int) -> None:
    scheduler.add_job(
        run_db_backup,
        IntervalTrigger(hours=max(1, interval_hours)),
        kwargs={"bot": bot},
        id="db_backup",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
