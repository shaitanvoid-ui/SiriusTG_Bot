from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services.scheduler_runtime import apply_scheduler_setting


def test_scheduler_intervals_are_rescheduled_live() -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(lambda: None, "interval", hours=6, id="sub_rechecker")
    assert apply_scheduler_setting(scheduler, "subrecheck.interval_hours", 2)
    trigger = scheduler.get_job("sub_rechecker").trigger
    assert int(trigger.interval.total_seconds()) == 2 * 60 * 60


def test_non_schedule_setting_is_ignored() -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    assert not apply_scheduler_setting(scheduler, "wheel.cost", 2.0)
