"""daily_digest: ежедневная сводка метрик в LOG_CHANNEL_ID (Этап 13).

Раз в сутки в `digest.hour_msk` (default 09:00 МСК) отправляем в лог-канал
короткий дайджест: юзеры, обязательства, активность за московские сутки.
Данные — из AdminStatsService (та же сводка, что в админ-дашборде).
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.config import settings as app_settings
from core.logger import get_logger
from db.session import SessionLocal
from locales.ru import T
from services.admin_stats import AdminStatsService, DashboardStats
from services.settings import SettingsService
from utils.tz import MSK_OFFSET_HOURS


log = get_logger(__name__)


def render_digest(s: DashboardStats) -> str:
    return T.log_daily_digest.format(
        users_total=s.users_total,
        users_new_today=s.users_new_today,
        users_passed=s.users_passed,
        balance_total=f"{s.balance_total:.2f}",
        debt_total=f"{s.debt_total:.2f}",
        clicks_today=s.clicks_today,
        bonuses_today=s.bonuses_today,
        spins_today=s.spins_today,
        tasks_today=s.tasks_today,
        refs_today=s.refs_today,
        reviews_pending=s.reviews_pending,
    )


async def run_daily_digest(bot: Bot) -> None:
    async with SessionLocal() as session:
        if not await SettingsService(session).get_bool("digest.enabled", True):
            return
        stats = await AdminStatsService(session).dashboard()
    if app_settings.log_channel_id is None:
        return
    try:
        await bot.send_message(app_settings.log_channel_id, render_digest(stats))
        log.info("daily_digest_sent")
    except TelegramAPIError:
        log.exception("daily_digest_send_failed")
        raise


def register_jobs(scheduler: AsyncIOScheduler, bot: Bot, *, hour_msk: int) -> None:
    # планировщик живёт в UTC — конвертируем московский час
    hour_utc = (max(0, min(23, hour_msk)) - MSK_OFFSET_HOURS) % 24
    scheduler.add_job(
        run_daily_digest,
        CronTrigger(hour=hour_utc, minute=0),
        kwargs={"bot": bot},
        id="daily_digest",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
