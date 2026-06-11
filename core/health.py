from __future__ import annotations

from aiohttp import web

from core.config import settings
from core.logger import get_logger


log = get_logger(__name__)


async def _health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", _health)
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
