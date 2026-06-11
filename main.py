from __future__ import annotations

import asyncio
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers import get_root_router
from bot.middlewares.ban import BanCheckMiddleware
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.user import UserUpsertMiddleware
from core.config import settings
from core.health import start_health_server, stop_health_server
from core.logger import get_logger, setup_logging
from db.session import SessionLocal, dispose_engine
from locales.ru import T
from services.settings import SettingsService, seed_defaults
from services.instructions import seed_instructions
from userbot import client as userbot_client
from workers.daily_digest import register_jobs as register_daily_digest_jobs
from workers.db_backup import register_jobs as register_db_backup_jobs
from workers.leaderboard_payout import register_jobs as register_leaderboard_payout_jobs
from workers.sub_rechecker import register_jobs as register_subrechecker_jobs
from workers.support_autoclose import register_jobs as register_support_autoclose_jobs
from workers.tasks_rechecker import register_jobs as register_tasks_rechecker_jobs


log = get_logger(__name__)


async def _on_startup(bot: Bot) -> None:
    me = await bot.get_me()
    log.info("bot_started", username=me.username, id=me.id)
    log.info("userbot_status", configured=userbot_client.is_configured())


def _build_shutdown(health_runner: web.AppRunner, scheduler: AsyncIOScheduler):
    async def _on_shutdown(bot: Bot) -> None:
        log.info("bot_shutting_down")
        with suppress(Exception):
            scheduler.shutdown(wait=False)
        with suppress(Exception):
            await userbot_client.disconnect()
        with suppress(Exception):
            await stop_health_server(health_runner)
        with suppress(Exception):
            await bot.session.close()
        await dispose_engine()
        log.info("bot_shutdown_complete")
    return _on_shutdown


def _setup_middlewares(dp: Dispatcher) -> None:
    db_mw = DbSessionMiddleware()
    user_mw = UserUpsertMiddleware()
    ban_mw = BanCheckMiddleware()
    for observer in (dp.message, dp.callback_query):
        observer.middleware(db_mw)
        observer.middleware(user_mw)
        observer.middleware(ban_mw)


def _make_job_error_listener(bot: Bot):
    """Алерт в лог-канал при падении любой джобы APScheduler (Этап 13)."""

    def _listener(event) -> None:
        log.error("scheduler_job_error", job_id=event.job_id)
        if settings.log_channel_id is None:
            return

        async def _notify() -> None:
            with suppress(Exception):
                await bot.send_message(
                    settings.log_channel_id,
                    T.log_worker_error.format(
                        job_id=event.job_id, error=str(event.exception)[:300]
                    ),
                )

        with suppress(RuntimeError):
            asyncio.get_running_loop().create_task(_notify())

    return _listener


async def _start_scheduler(bot: Bot) -> AsyncIOScheduler:
    async with SessionLocal() as session:
        settings_svc = SettingsService(session)
        interval_hours = await settings_svc.get_int("subrecheck.interval_hours", 6)
        tasks_interval_min = await settings_svc.get_int("tasks_recheck.interval_min", 5)
        backup_hours = await settings_svc.get_int("backup.interval_hours", 6)
        digest_hour_msk = await settings_svc.get_int("digest.hour_msk", 9)
        support_check_hours = await settings_svc.get_int("support.autoclose_check_hours", 6)
    scheduler = AsyncIOScheduler(timezone="UTC")
    register_subrechecker_jobs(scheduler, bot, interval_hours=interval_hours)
    register_tasks_rechecker_jobs(scheduler, bot, interval_min=tasks_interval_min)
    register_leaderboard_payout_jobs(scheduler, bot)
    register_db_backup_jobs(scheduler, bot, interval_hours=backup_hours)
    register_daily_digest_jobs(scheduler, bot, hour_msk=digest_hour_msk)
    register_support_autoclose_jobs(scheduler, bot, interval_hours=support_check_hours)
    scheduler.add_listener(_make_job_error_listener(bot), EVENT_JOB_ERROR)
    scheduler.start()
    log.info(
        "scheduler_started",
        interval_hours=interval_hours,
        tasks_interval_min=tasks_interval_min,
        backup_hours=backup_hours,
        digest_hour_msk=digest_hour_msk,
    )
    return scheduler


async def run() -> None:
    setup_logging()
    log.info("startup", env=settings.env)

    await seed_defaults()

    async with SessionLocal() as session:
        await seed_instructions(session)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    _setup_middlewares(dp)
    dp.include_router(get_root_router())

    health_runner = await start_health_server()
    scheduler = await _start_scheduler(bot)

    dp.startup.register(_on_startup)
    dp.shutdown.register(_build_shutdown(health_runner, scheduler))

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
