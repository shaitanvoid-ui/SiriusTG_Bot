"""Московское время — единая точка истины (по требованию владельца).

Хранение в БД — всегда UTC (db.base.utcnow). Всё видимое людям — даты на
карточках, приветствие, дневные границы бонуса/кликера/колеса/статистики —
считается по МСК (UTC+3, без перехода на летнее время).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

MSK_OFFSET_HOURS = 3
MSK = timezone(timedelta(hours=MSK_OFFSET_HOURS), name="MSK")

FMT_DT = "%d.%m %H:%M"
FMT_DATE = "%d.%m.%Y"
FMT_DATE_TIME = "%d.%m.%Y %H:%M"


def now_msk() -> datetime:
    return datetime.now(tz=MSK)


def today_msk() -> date:
    """Московская дата — граница «нового дня» для бонуса/кликера/колеса."""
    return now_msk().date()


def to_msk(dt: datetime) -> datetime:
    """UTC-datetime (наивный из SQLite или aware) → московское время."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MSK)


def msk_day_start_utc(day: date | None = None) -> datetime:
    """Полночь МСК указанного дня как UTC-момент — для SQL-сравнений."""
    d = day or today_msk()
    return datetime(d.year, d.month, d.day, tzinfo=MSK).astimezone(timezone.utc)


def fmt_dt(dt: datetime, fmt: str = FMT_DT) -> str:
    """«11.06 14:32» по Москве."""
    return to_msk(dt).strftime(fmt)


def fmt_date(dt: datetime) -> str:
    """«11.06.2026» по Москве."""
    return to_msk(dt).strftime(FMT_DATE)
