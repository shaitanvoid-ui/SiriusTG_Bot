"""Settings isolation across defaults, databases, commits and rollbacks."""

from __future__ import annotations

from sqlalchemy import event

from services.settings import SettingsService


async def test_missing_setting_does_not_cache_callers_default(session) -> None:
    svc = SettingsService(session)
    assert await svc.get("missing.key", 1) == 1
    assert await svc.get("missing.key", 2) == 2


async def test_uncommitted_settings_are_visible_only_in_the_writer_session(session, session_factory) -> None:
    writer = SettingsService(session)
    await writer.set("brand.name", "NEW")
    assert await SettingsService(session).get("brand.name") == "NEW"
    async with session_factory() as reader:
        assert await SettingsService(reader).get("brand.name") == "SIRIUS"
    await session.rollback()
    assert await writer.get("brand.name") == "SIRIUS"


async def test_commit_invalidates_old_committed_values(session, session_factory) -> None:
    await SettingsService(session).get("brand.name")
    await SettingsService(session).set("brand.name", "NEW")
    async with session_factory() as reader:
        assert await SettingsService(reader).get("brand.name") == "SIRIUS"
    await session.commit()
    async with session_factory() as reader:
        assert await SettingsService(reader).get("brand.name") == "NEW"


async def test_cold_preload_uses_one_select_and_warm_reads_use_none(session, engine) -> None:
    queries = []
    def record(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)
    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        svc = SettingsService(session)
        await svc.preload()
        assert len(queries) == 1
        await svc.get("brand.name")
        await svc.get("click.base_reward")
        await svc.get("bonus.streak")
        assert len(queries) == 1
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)


async def test_savepoint_commit_does_not_publish_uncommitted_settings(session, session_factory) -> None:
    # Begin a real outer transaction before SQLite's SAVEPOINT.
    await SettingsService(session).set("brand.tagline", "OUTER")
    async with session.begin_nested():
        await SettingsService(session).set("brand.name", "INNER")
    assert await SettingsService(session).get("brand.name") == "INNER"
    async with session_factory() as reader:
        assert await SettingsService(reader).get("brand.name") == "SIRIUS"
    await session.rollback()
    assert await SettingsService(session).get("brand.name") == "SIRIUS"


async def test_savepoint_rollback_restores_outer_pending_setting(session) -> None:
    await SettingsService(session).set("brand.name", "OUTER")
    savepoint = await session.begin_nested()
    await SettingsService(session).set("brand.name", "INNER")
    await savepoint.rollback()
    assert await SettingsService(session).get("brand.name") == "OUTER"
    await session.commit()
    assert await SettingsService(session).get("brand.name") == "OUTER"
