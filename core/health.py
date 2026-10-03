from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import lru_cache

from aiohttp import web
from alembic.config import Config
from alembic.script import ScriptDirectory

from core.config import PROJECT_ROOT, settings
from core.logger import get_logger


log = get_logger(__name__)
ReadinessCheck = Callable[[], Awaitable[bool]]
_runtime_ready = False


def set_runtime_ready(ready: bool) -> None:
    global _runtime_ready
    _runtime_ready = ready


@lru_cache(maxsize=1)
def _expected_schema_heads() -> frozenset[str]:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    return frozenset(ScriptDirectory.from_config(config).get_heads())


async def check_database_readiness() -> bool:
    """Check DB connectivity and that all repository Alembic heads are applied."""
    from db.session import engine

    expected = _expected_schema_heads()
    if not expected:
        return False

    async with engine.connect() as connection:
        result = await connection.exec_driver_sql("SELECT version_num FROM alembic_version")
        current = frozenset(str(value) for value in result.scalars())
    return current == expected


async def check_application_readiness() -> bool:
    """Readiness означает не только живой HTTP, но и готовый runtime бота."""
    return _runtime_ready and await check_database_readiness()


async def _health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def _ready(check: ReadinessCheck) -> web.Response:
    try:
        is_ready = await check()
    except Exception as exc:  # boundary: readiness must return 503, never a traceback
        log.warning("readiness_check_failed", error_type=type(exc).__name__)
        is_ready = False

    if is_ready:
        return web.json_response({"status": "ready"})
    return web.json_response({"status": "unavailable"}, status=web.HTTPServiceUnavailable.status_code)


def build_app(*, readiness_check: ReadinessCheck | None = None) -> web.Application:
    check = readiness_check or check_application_readiness

    async def ready(_: web.Request) -> web.Response:
        return await _ready(check)

    app = web.Application()
    app.router.add_get("/health", _health)
    app.router.add_get("/ready", ready)
    return app


async def start_health_server() -> web.AppRunner:
    app = build_app()
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.health_host, port=settings.health_port)
    await site.start()
    log.info("health_server_started", host=settings.health_host, port=settings.health_port)
    return runner


async def stop_health_server(runner: web.AppRunner) -> None:
    await runner.cleanup()
    log.info("health_server_stopped")
