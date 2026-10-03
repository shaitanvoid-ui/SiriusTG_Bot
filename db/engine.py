from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


SQLITE_BUSY_TIMEOUT_MS = 5_000


def _set_sqlite_pragmas(dbapi_connection: Any, _: Any) -> None:
    """Apply connection-local SQLite safety and contention settings."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


def configure_sqlite_engine(engine: AsyncEngine) -> AsyncEngine:
    """Attach SQLite pragmas to an async engine; leave other dialects intact."""
    if engine.url.get_backend_name() == "sqlite":
        event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
    return engine


def create_app_engine(database_url: str, **kwargs: Any) -> AsyncEngine:
    """Create the application/test engine with one shared configuration path."""
    options: dict[str, Any] = {
        "echo": False,
        "pool_pre_ping": True,
    }
    options.update(kwargs)
    return configure_sqlite_engine(create_async_engine(database_url, **options))
