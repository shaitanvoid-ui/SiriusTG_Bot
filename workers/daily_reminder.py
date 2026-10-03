"""Opt-in, quiet evening reminders; at most one attempt per user/MSK day.

The slot is committed before the API request so a restart cannot flood users.
A failed/ambiguous delivery is not retried that day (Telegram has no send dedup key).
"""

from __future__ import annotations

from datetime import timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import case, func, or_, select, update

from core.logger import get_logger
from db.base import utcnow
from db.models import User
from db.session import SessionLocal
from locales.ru import T
from services.settings import SettingsService
from userbot.client import is_configured
from utils.keyboards import SiriusKeyboardBuilder
from utils.tz import now_msk, today_msk


log = get_logger(__name__)


def _eligible(today):
    valid_prefs = case((func.json_valid(User.notify_prefs) == 1, User.notify_prefs), else_="{}")
    return (
        func.json_type(valid_prefs, "$.daily") == "true",
        User.is_banned.is_(False), User.is_deleted.is_(False),
        User.accepted_terms_at.is_not(None), User.captcha_passed_at.is_not(None),
        User.subs_passed_at.is_not(None),
        or_(User.last_bonus_date.is_(None), User.last_bonus_date < today),
        or_(User.last_daily_reminder_date.is_(None), User.last_daily_reminder_date < today),
        User.last_seen_at >= utcnow() - timedelta(days=30),
        User.last_seen_at <= utcnow() - timedelta(hours=2),
    )


async def run_daily_reminders(bot: Bot) -> None:
    # Defense in depth against manual/misfired jobs during quiet hours.
    if not 10 <= now_msk().hour <= 21:
        return
    async with SessionLocal() as session:
        settings = SettingsService(session)
        if not await settings.get_bool("daily.reminders_enabled", True):
            return
        if await settings.get_bool("bonus.bio_required", True) and not is_configured():
            return
        limit = max(1, min(1000, await settings.get_int("daily.reminder_batch_size", 100)))
        today = today_msk()
        ids = list((await session.scalars(select(User.id).where(*_eligible(today)).order_by(User.id).limit(limit))).all())
    keyboard = SiriusKeyboardBuilder()
    keyboard.button(text=T.btn_menu_daily, callback_data="day:open", style="primary")
    keyboard.button(text=T.btn_profile_notifications, callback_data="ntf:open")
    keyboard.adjust(1, 1)
    for user_id in ids:
        async with SessionLocal() as session:
            claimed = await session.execute(update(User).where(User.id == user_id, *_eligible(today)).values(
                last_daily_reminder_date=today,
            ).returning(User.tg_id))
            tg_id = claimed.scalar_one_or_none()
            await session.commit()
        if tg_id is None:
            continue
        try:
            await bot.send_message(tg_id, T.daily_reminder, reply_markup=keyboard.as_markup(), disable_notification=True)
        except TelegramRetryAfter:
            # Never sleep while holding a DB transaction or continue a flood-limited batch.
            log.warning("daily_reminder_rate_limited")
            break
        except TelegramAPIError as exc:
            log.warning("daily_reminder_failed", error_type=type(exc).__name__)


def register_jobs(scheduler: AsyncIOScheduler, bot: Bot, *, hour_msk: int) -> None:
    scheduler.add_job(run_daily_reminders, trigger=CronTrigger(hour=hour_msk, minute=0, timezone="Europe/Moscow"),
                      args=[bot], id="daily_reminder", replace_existing=True, coalesce=True,
                      max_instances=1, misfire_grace_time=900)
