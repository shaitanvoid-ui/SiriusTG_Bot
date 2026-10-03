"""Применение изменяемых расписаний без перезапуска бота."""
from __future__ import annotations

from typing import Any

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core.logger import get_logger
from utils.tz import MSK_OFFSET_HOURS


log = get_logger(__name__)


def apply_scheduler_setting(
    scheduler: AsyncIOScheduler | None, key: str, value: Any
) -> bool:
    """Перенастраивает соответствующую job; ``False`` — ключ не расписания."""
    if scheduler is None:
        return False

    if key == "subrecheck.interval_hours":
        job_id = "sub_rechecker"
        trigger = IntervalTrigger(hours=max(1, int(value)))
    elif key == "tasks_recheck.interval_min":
        job_id = "tasks_rechecker"
        trigger = IntervalTrigger(minutes=max(1, int(value)))
    elif key == "backup.interval_hours":
        job_id = "db_backup"
        trigger = IntervalTrigger(hours=max(1, int(value)))
    elif key == "support.autoclose_check_hours":
        job_id = "support_autoclose"
        trigger = IntervalTrigger(hours=max(1, int(value)))
    elif key == "digest.hour_msk":
        job_id = "daily_digest"
        hour_utc = (int(value) - MSK_OFFSET_HOURS) % 24
        trigger = CronTrigger(hour=hour_utc, minute=0, timezone="UTC")
    elif key == "daily.reminder_hour_msk":
        job_id = "daily_reminder"
        trigger = CronTrigger(hour=int(value), minute=0, timezone="Europe/Moscow")
    else:
        return False

    try:
        scheduler.reschedule_job(job_id, trigger=trigger)
    except JobLookupError:
        log.warning("scheduler_job_not_found", job_id=job_id, setting_key=key)
        return False
    log.info("scheduler_job_rescheduled", job_id=job_id, setting_key=key)
    return True


__all__ = ["apply_scheduler_setting"]
