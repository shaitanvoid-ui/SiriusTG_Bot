"""Расчёт уровня юзера и прогресса до следующего. Конфиг — из settings."""

from __future__ import annotations

from dataclasses import dataclass

from services.settings import SettingsService


_FALLBACK_LEVELS: list[dict] = [
    {"level": 1, "name": "Бронза",  "emoji": "🥉", "required_refs": 0,   "click_mult": 1.0,  "click_daily_limit": 100},
    {"level": 2, "name": "Серебро", "emoji": "🥈", "required_refs": 5,   "click_mult": 1.1,  "click_daily_limit": 120},
    {"level": 3, "name": "Золото",  "emoji": "🥇", "required_refs": 15,  "click_mult": 1.25, "click_daily_limit": 150},
    {"level": 4, "name": "Платина", "emoji": "💠", "required_refs": 50,  "click_mult": 1.5,  "click_daily_limit": 200},
    {"level": 5, "name": "Алмаз",   "emoji": "💎", "required_refs": 150, "click_mult": 2.0,  "click_daily_limit": 300},
]


@dataclass(frozen=True)
class LevelInfo:
    level: int
    name: str
    emoji: str
    required_refs: int
    click_mult: float
    click_daily_limit: int
    # производное
    next_name: str | None
    next_emoji: str | None
    next_required: int | None
    progress_current: int  # сколько рефов внутри текущего уровня
    progress_total: int    # «расстояние» до следующего уровня (для прогресс-бара)
    to_next: int           # сколько ещё рефов до следующего уровня (0 — макс)
    is_max: bool


class LevelService:
    def __init__(self, settings_service: SettingsService) -> None:
        self.settings = settings_service

    async def _config(self) -> list[dict]:
        raw = await self.settings.get_list("levels.config", _FALLBACK_LEVELS)
        if not raw:
            return _FALLBACK_LEVELS
        return sorted(raw, key=lambda x: int(x["required_refs"]))

    async def compute(self, confirmed_refs: int) -> LevelInfo:
        cfg = await self._config()
        current = cfg[0]
        next_lvl: dict | None = None
        for i, lvl in enumerate(cfg):
            if confirmed_refs >= int(lvl["required_refs"]):
                current = lvl
                next_lvl = cfg[i + 1] if i + 1 < len(cfg) else None
        if next_lvl is None:
            return LevelInfo(
                level=int(current["level"]),
                name=str(current["name"]),
                emoji=str(current["emoji"]),
                required_refs=int(current["required_refs"]),
                click_mult=float(current["click_mult"]),
                click_daily_limit=int(current["click_daily_limit"]),
                next_name=None,
                next_emoji=None,
                next_required=None,
                progress_current=1,
                progress_total=1,
                to_next=0,
                is_max=True,
            )
        cur_req = int(current["required_refs"])
        next_req = int(next_lvl["required_refs"])
        span = max(next_req - cur_req, 1)
        progress = max(0, min(confirmed_refs - cur_req, span))
        return LevelInfo(
            level=int(current["level"]),
            name=str(current["name"]),
            emoji=str(current["emoji"]),
            required_refs=cur_req,
            click_mult=float(current["click_mult"]),
            click_daily_limit=int(current["click_daily_limit"]),
            next_name=str(next_lvl["name"]),
            next_emoji=str(next_lvl["emoji"]),
            next_required=next_req,
            progress_current=progress,
            progress_total=span,
            to_next=max(next_req - confirmed_refs, 0),
            is_max=False,
        )
