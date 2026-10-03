from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytest

from db.base import utcnow
from services.notifications import NotificationService
from services.settings import SettingsService
from services.settings_validation import validate_setting_value
from tests.helpers import create_user
from utils.tz import MSK, today_msk
from workers import daily_reminder as worker


def _configure(monkeypatch, session_factory, hour=20):
    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    monkeypatch.setattr(worker, "is_configured", lambda: True)
    monkeypatch.setattr(worker, "now_msk", lambda: datetime(2026, 10, 1, hour, tzinfo=MSK))


async def _eligible_user(session, tg_id, **kwargs):
    values = dict(accepted_terms_at=utcnow(), captcha_passed_at=utcnow(), subs_passed_at=utcnow(),
                  last_seen_at=utcnow() - timedelta(hours=3), notify_prefs=json.dumps({"daily": True}))
    values.update(kwargs)
    return await create_user(session, tg_id=tg_id, **values)


async def test_reminders_require_explicit_opt_in_and_survive_worker_restart(session, session_factory, monkeypatch):
    _configure(monkeypatch, session_factory)
    opted_in = await _eligible_user(session, 777201)
    opted_out = await _eligible_user(session, 777202, notify_prefs=None)
    assert NotificationService.prefs_of(opted_out)["daily"] is False
    await session.commit()
    bot = AsyncMock()
    await worker.run_daily_reminders(bot)
    await worker.run_daily_reminders(bot)
    bot.send_message.assert_awaited_once()
    assert bot.send_message.call_args.args[0] == opted_in.tg_id
    assert bot.send_message.call_args.kwargs["disable_notification"] is True
    await session.refresh(opted_in)
    assert opted_in.last_daily_reminder_date == today_msk()


async def test_reminders_skip_active_banned_claimed_and_corrupt_preferences(session, session_factory, monkeypatch):
    _configure(monkeypatch, session_factory)
    cases = [dict(last_seen_at=utcnow()), dict(is_banned=True), dict(is_deleted=True),
             dict(last_bonus_date=today_msk()), dict(notify_prefs="broken json"),
             dict(accepted_terms_at=None), dict(subs_passed_at=None),
             dict(notify_prefs=json.dumps({"daily":1})), dict(notify_prefs=json.dumps({"daily":"true"}))]
    for index, values in enumerate(cases):
        await _eligible_user(session, 777210 + index, **values)
    await session.commit()
    bot = AsyncMock()
    await worker.run_daily_reminders(bot)
    bot.send_message.assert_not_called()


async def test_quiet_hours_and_disabled_reminders_send_nothing(session, session_factory, monkeypatch):
    _configure(monkeypatch, session_factory, hour=3)
    await _eligible_user(session, 777220)
    await session.commit()
    bot = AsyncMock()
    await worker.run_daily_reminders(bot)
    bot.send_message.assert_not_called()
    _configure(monkeypatch, session_factory)
    await SettingsService(session).set("daily.reminders_enabled", False)
    await session.commit()
    await worker.run_daily_reminders(bot)
    bot.send_message.assert_not_called()


def test_scheduler_does_not_run_reminders_at_startup():
    scheduler = AsyncIOScheduler(timezone="UTC")
    worker.register_jobs(scheduler, AsyncMock(), hour_msk=20)
    job = scheduler.get_job("daily_reminder")
    assert str(job.trigger.timezone) == "Europe/Moscow"
    assert job.trigger.get_next_fire_time(None, datetime(2026, 10, 1, 12, tzinfo=MSK)).hour == 20
    assert job.max_instances == 1


@pytest.mark.parametrize("key,value", [("daily.reminder_hour_msk", 3), ("daily.reminder_hour_msk", 23),
                                      ("daily.reminder_batch_size", 0), ("daily.reminder_batch_size", 1001)])
def test_reminder_settings_are_bounded(key, value):
    with pytest.raises(ValueError):
        validate_setting_value(key, value)
