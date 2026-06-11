"""Задача 2: settings-дефолты кликера и пере-проверки заданий."""

from __future__ import annotations

from services.settings import SettingsService


async def test_clicker_economy_values(session):
    svc = SettingsService(session)
    assert await svc.get_float("click.base_reward", 0.0) == 0.1
    assert await svc.get_int("click.daily_base_limit", 0) == 70
    assert await svc.get_int("click.min_interval_ms", 0) == 300000


async def test_levels_clicker_ladder(session):
    svc = SettingsService(session)
    levels = await svc.get_list("levels.config", [])
    assert len(levels) == 5
    base = await svc.get_float("click.base_reward", 0.0)

    by_name = {lvl["name"]: lvl for lvl in levels}
    # множитель плоский — тап всегда 0.1⭐, прогресс задаётся лимитом
    for lvl in levels:
        assert float(lvl["click_mult"]) == 1.0
    # лесенка дневного лимита: 40→55→70→85→100
    assert int(by_name["Бронза"]["click_daily_limit"]) == 40
    assert int(by_name["Алмаз"]["click_daily_limit"]) == 100

    # дневной максимум монотонно растёт, Бронза=4⭐, Алмаз=10⭐, шаг 1.5⭐
    caps = [round(int(lvl["click_daily_limit"]) * base, 2) for lvl in levels]
    assert caps == [4.0, 5.5, 7.0, 8.5, 10.0]


async def test_tasks_recheck_defaults(session):
    svc = SettingsService(session)
    assert await svc.get_bool("tasks_recheck.enabled", False) is True
    assert await svc.get_int("tasks_recheck.interval_min", 0) == 5
    assert await svc.get_int("tasks_recheck.sample_size", 0) == 100
