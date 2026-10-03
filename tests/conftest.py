"""Тестовая инфраструктура: изолированная файловая async-SQLite на каждый тест.

Каждый тест получает свежую БД (tmp_path), накатанную через Base.metadata, с
засиженными settings-дефолтами. Class-level кэш SettingsService сбрасывается
вокруг каждого теста, чтобы значения из одной БД не протекали в другую.
"""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

import db.models  # noqa: F401  — регистрация всех таблиц в Base.metadata
from db.base import Base
from db.engine import create_app_engine
from db.repositories.setting import SettingRepo
from services.settings import DEFAULTS, SettingsService


@pytest_asyncio.fixture
async def engine(tmp_path):
    db_file = tmp_path / "test.db"
    eng = create_app_engine(f"sqlite+aiosqlite:///{db_file}")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
async def _clear_settings_cache():
    SettingsService.invalidate()
    yield
    SettingsService.invalidate()


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as s:
        repo = SettingRepo(s)
        for key, (value, desc) in DEFAULTS.items():
            await repo.set(key, value, desc)
        await s.commit()
        yield s
