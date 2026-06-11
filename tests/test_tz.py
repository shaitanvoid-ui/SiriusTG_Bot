"""Московское время (utils/tz): конвертация, границы суток, час дайджеста."""

from __future__ import annotations

from datetime import date, datetime, timezone

from utils.tz import (
    MSK,
    MSK_OFFSET_HOURS,
    fmt_date,
    fmt_dt,
    msk_day_start_utc,
    to_msk,
    today_msk,
)


def test_to_msk_shifts_aware_utc():
    dt = datetime(2026, 6, 11, 21, 30, tzinfo=timezone.utc)
    local = to_msk(dt)
    assert (local.day, local.hour, local.minute) == (12, 0, 30)  # перевалили полночь МСК


def test_to_msk_treats_naive_as_utc():
    naive = datetime(2026, 6, 11, 10, 0)  # так SQLite отдаёт хранимые UTC-даты
    assert to_msk(naive).hour == 13


def test_fmt_helpers():
    dt = datetime(2026, 6, 11, 21, 30, tzinfo=timezone.utc)
    assert fmt_dt(dt) == "12.06 00:30"
    assert fmt_date(dt) == "12.06.2026"


def test_msk_day_start_utc_is_2100_prev_day():
    start = msk_day_start_utc(date(2026, 6, 12))
    assert start == datetime(2026, 6, 11, 21, 0, tzinfo=timezone.utc)


def test_today_msk_matches_now_in_msk():
    assert today_msk() == datetime.now(tz=MSK).date()


def test_digest_hour_conversion():
    # 09:00 МСК → 06:00 UTC (формула из workers/daily_digest.register_jobs)
    assert (9 - MSK_OFFSET_HOURS) % 24 == 6
    # полночь МСК → 21:00 UTC предыдущего дня
    assert (0 - MSK_OFFSET_HOURS) % 24 == 21
