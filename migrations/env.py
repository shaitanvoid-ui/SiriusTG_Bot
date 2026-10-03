from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from core.config import settings
from db.models import Base
from db.engine import configure_sqlite_engine


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    is_sqlite = connection.dialect.name == "sqlite"
    if is_sqlite:
        # SQLite batch migrations recreate a table via DROP/RENAME. With FK enabled,
        # DROP users fires real ON DELETE cascades into partners/referrals before the
        # replacement table is renamed. Disable enforcement outside the migration
        # transaction, then validate the complete graph before enabling it again.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()  # finish SQLAlchemy autobegin; PRAGMA must precede DDL txn

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
    )
    try:
        with context.begin_transaction():
            context.run_migrations()

        if is_sqlite:
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            if violations:
                sample = ", ".join(
                    f"{row[0]}(rowid={row[1]}, parent={row[2]})"
                    for row in violations[:5]
                )
                raise RuntimeError(
                    "Alembic migration left SQLite foreign-key violations: " + sample
                )
    finally:
        if is_sqlite:
            # foreign_key_check/failed DDL may leave an implicit transaction open;
            # FK mode can only be changed when no transaction is active.
            if connection.in_transaction():
                connection.rollback()
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


async def run_async_migrations() -> None:
    connectable = configure_sqlite_engine(
        async_engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
