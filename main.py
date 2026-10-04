from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher, html
from aiogram.exceptions import TelegramAPIError
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiohttp import web
from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers import SchedulerNotRunningError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers import get_root_router
from bot.handlers.admin.broadcast import shutdown_active_broadcast
from bot.middlewares.ban import BanCheckMiddleware
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.user import UserUpsertMiddleware
from bot.middlewares.presentation import PresentationMiddleware
from bot.middlewares.callback_access import CallbackAccessMiddleware
from bot.middlewares.antifraud import AntifraudMiddleware
from core.config import settings
from core.health import set_runtime_ready, start_health_server, stop_health_server
from core.logger import get_logger, setup_logging
from db.session import SessionLocal, dispose_engine
from db.fsm_storage import SQLiteFSMStorage
from locales.ru import T
from services.settings import SettingsService, seed_defaults
from services.gifts import GiftService
from workers.gifts import GiftWorker
from services.instructions import seed_instructions
from services.partner import encrypt_legacy_payout_requisites
from userbot import client as userbot_client
from workers.daily_digest import register_jobs as register_daily_digest_jobs
from workers.daily_reminder import register_jobs as register_daily_reminder_jobs
from workers.db_backup import register_jobs as register_db_backup_jobs
from workers.leaderboard_payout import register_jobs as register_leaderboard_payout_jobs
from workers.sub_rechecker import register_jobs as register_subrechecker_jobs
from workers.support_autoclose import register_jobs as register_support_autoclose_jobs
from workers.tasks_rechecker import register_jobs as register_tasks_rechecker_jobs


log = get_logger(__name__)


async def _on_startup(bot: Bot) -> None:
    await bot.get_me()
    # Readiness включаем только после успешного рукопожатия с Telegram и
    # запуска dispatcher: до этого контейнер жив, но принимать трафик не готов.
    set_runtime_ready(True)
    log.info("bot_started")
    log.info("userbot_status", configured=userbot_client.is_configured())


def _build_shutdown(health_runner: web.AppRunner, scheduler: AsyncIOScheduler, gift_worker=None):
    async def _on_shutdown(bot: Bot) -> None:
        log.info("bot_shutting_down")
        set_runtime_ready(False)
        if gift_worker is not None:
            await gift_worker.stop()
        broadcast_result = (
            await asyncio.gather(shutdown_active_broadcast(), return_exceptions=True)
        )[0]
        if isinstance(broadcast_result, asyncio.CancelledError):
            raise broadcast_result
        if isinstance(broadcast_result, BaseException):
            log.warning(
                "shutdown_step_failed",
                step="active_broadcast",
                error_type=type(broadcast_result).__name__,
            )

        async def stop_scheduler() -> None:
            # AsyncIOScheduler.shutdown() only schedules its implementation via
            # call_soon_threadsafe, which would make failures unobservable here.
            # Execute the wrapped implementation while already on its event loop.
            shutdown_impl = getattr(type(scheduler).shutdown, "__wrapped__", None)
            if shutdown_impl is None:
                scheduler.shutdown(wait=False)
            else:
                shutdown_impl(scheduler, wait=False)

        scheduler_result = (
            await asyncio.gather(stop_scheduler(), return_exceptions=True)
        )[0]
        if isinstance(scheduler_result, asyncio.CancelledError):
            raise scheduler_result
        if isinstance(scheduler_result, SchedulerNotRunningError):
            log.info("scheduler_already_stopped")
        elif isinstance(scheduler_result, BaseException):
            log.warning(
                "shutdown_step_failed",
                step="scheduler",
                error_type=type(scheduler_result).__name__,
            )

        steps = (
            ("userbot", userbot_client.disconnect()),
            ("health", stop_health_server(health_runner)),
            ("bot_session", bot.session.close()),
        )
        results = await asyncio.gather(
            *(operation for _, operation in steps),
            return_exceptions=True,
        )
        for (step, _), result in zip(steps, results, strict=True):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                log.warning(
                    "shutdown_step_failed",
                    step=step,
                    error_type=type(result).__name__,
                )

        engine_result = (await asyncio.gather(dispose_engine(), return_exceptions=True))[0]
        if isinstance(engine_result, asyncio.CancelledError):
            raise engine_result
        if isinstance(engine_result, BaseException):
            log.warning(
                "shutdown_step_failed",
                step="database_engine",
                error_type=type(engine_result).__name__,
            )
        log.info("bot_shutdown_complete")
    return _on_shutdown


def _setup_middlewares(dp: Dispatcher) -> None:
    access_mw = CallbackAccessMiddleware()
    # Dispatcher installs FSM on Update first. Place the shared access boundary
    # before it so rejected group/foreign-chat events never read or mutate FSM.
    fsm_registered = dp.fsm in dp.update.outer_middleware
    if fsm_registered:
        dp.update.outer_middleware.unregister(dp.fsm)
    dp.update.outer_middleware(access_mw)
    if fsm_registered:
        dp.update.outer_middleware(dp.fsm)
    dp.message.outer_middleware(access_mw)
    dp.callback_query.outer_middleware(access_mw)
    dp.message.outer_middleware(AntifraudMiddleware())
    dp.callback_query.outer_middleware(AntifraudMiddleware())
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
        exc = event.exception
        log.error(
            "scheduler_job_error",
            job_id=event.job_id,
            error=str(exc),
            exc_info=(type(exc), exc, exc.__traceback__) if exc else None,
        )
        if settings.log_channel_id is None:
            return

        async def _notify() -> None:
            try:
                await bot.send_message(
                    settings.log_channel_id,
                    T.log_worker_error.format(
                        job_id=html.quote(str(event.job_id)),
                        error=html.quote(str(event.exception)[:300]),
                    ),
                )
            except TelegramAPIError as notify_error:
                log.warning(
                    "scheduler_alert_failed",
                    job_id=event.job_id,
                    error=str(notify_error),
                )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            log.warning("scheduler_alert_skipped", reason="event_loop_unavailable")
        else:
            loop.create_task(_notify())

    return _listener


async def _start_scheduler(bot: Bot) -> AsyncIOScheduler:
    async with SessionLocal() as session:
        settings_svc = SettingsService(session)
        interval_hours = await settings_svc.get_int("subrecheck.interval_hours", 6)
        tasks_interval_min = await settings_svc.get_int("tasks_recheck.interval_min", 5)
        backup_hours = await settings_svc.get_int("backup.interval_hours", 6)
        digest_hour_msk = await settings_svc.get_int("digest.hour_msk", 9)
        support_check_hours = await settings_svc.get_int("support.autoclose_check_hours", 6)
        reminder_hour = await settings_svc.get_int("daily.reminder_hour_msk", 20)
    scheduler = AsyncIOScheduler(timezone="UTC")
    register_subrechecker_jobs(scheduler, bot, interval_hours=interval_hours)
    register_tasks_rechecker_jobs(scheduler, bot, interval_min=tasks_interval_min)
    register_leaderboard_payout_jobs(scheduler, bot)
    register_db_backup_jobs(scheduler, bot, interval_hours=backup_hours)
    register_daily_digest_jobs(scheduler, bot, hour_msk=digest_hour_msk)
    register_support_autoclose_jobs(scheduler, bot, interval_hours=support_check_hours)
    register_daily_reminder_jobs(scheduler, bot, hour_msk=reminder_hour)
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
    set_runtime_ready(False)

    await seed_defaults()

    async with SessionLocal() as session:
        await seed_instructions(session)
        await encrypt_legacy_payout_requisites(session)
        await session.commit()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    bot.session.middleware(PresentationMiddleware(enabled=settings.rich_messages))
    dp = Dispatcher(
        storage=SQLiteFSMStorage(settings.fsm_storage_path),
        events_isolation=SimpleEventIsolation(),
    )
    _setup_middlewares(dp)
    dp.include_router(get_root_router())
    gift_service = GiftService()
    gift_worker = GiftWorker(gift_service, bot)
    dp["gift_service"] = gift_service

    health_runner = await start_health_server()
    scheduler = await _start_scheduler(bot)
    gift_worker.start()
    dp["scheduler"] = scheduler

    dp.startup.register(_on_startup)
    dp.shutdown.register(_build_shutdown(health_runner, scheduler, gift_worker))

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        tasks_concurrency_limit=settings.polling_concurrency,
    )


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
