"""Достижения.

Реестр достижений — в settings `achievements.config` (метрика, порог, награда).
Метрики берём из текущего состояния юзера и агрегатов БД:
    confirmed_refs, clicks_total, bonus_streak, tasks_done

Награда выдаётся единоразово (UQ user+code). `sync` начисляет всё свежезаработанное
и возвращает список новых достижений для уведомления. Точка вызова — открытие
экрана достижений (ленивое начисление: награда не теряется).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.models import User
from db.money import from_units, settlement_units
from db.repositories.action_log import ActionLogRepo
from db.repositories.clicker_day import ClickerDayRepo
from db.repositories.user import UserRepo
from db.repositories.user_achievement import UserAchievementRepo
from db.repositories.user_task_completion import UserTaskCompletionRepo
from services.settings import SettingsService


log = get_logger(__name__)

_DEFAULT_CONFIG: list[dict] = [
    {"code": "ref10", "name": "Командор", "emoji": "🎖", "metric": "confirmed_refs", "threshold": 10, "reward": 5.0},
]

# человекочитаемая единица метрики (для прогресс-строк)
METRIC_UNIT: dict[str, str] = {
    "confirmed_refs": "реф.",
    "clicks_total": "тапов",
    "bonus_streak": "дн. стрика",
    "tasks_done": "заданий",
}


@dataclass(frozen=True)
class AwardedAchievement:
    code: str
    name: str
    emoji: str
    reward: float


@dataclass(frozen=True)
class AchievementView:
    code: str
    name: str
    emoji: str
    metric: str
    threshold: int
    reward: float
    current: int
    unlocked: bool


class AchievementsService:
    def __init__(self, session: AsyncSession, settings_svc: SettingsService) -> None:
        self.session = session
        self.settings = settings_svc
        self.user_repo = UserRepo(session)
        self.ach_repo = UserAchievementRepo(session)

    async def enabled(self) -> bool:
        return await self.settings.get_bool("achievements.enabled", True)

    async def _config(self) -> list[dict]:
        raw = await self.settings.get_list("achievements.config", _DEFAULT_CONFIG)
        return raw or _DEFAULT_CONFIG

    async def _metrics(self, user: User) -> dict[str, int]:
        clicks = await ClickerDayRepo(self.session).total_clicks(user.id)
        tasks = await UserTaskCompletionRepo(self.session).count_for_user(user.id)
        return {
            "confirmed_refs": int(user.confirmed_ref_count),
            "clicks_total": int(clicks),
            "bonus_streak": int(user.bonus_streak),
            "tasks_done": int(tasks),
        }

    async def sync(self, user: User) -> list[AwardedAchievement]:
        """Начисляет все свежезаработанные достижения. Возвращает новые."""
        if not await self.user_repo.lock_rewards_allowed(user.id):
            return []
        if not await self.enabled():
            return []
        cfg = await self._config()
        metrics = await self._metrics(user)
        have = await self.ach_repo.get_codes(user.id)

        awarded: list[AwardedAchievement] = []
        for a in cfg:
            code = str(a["code"])
            if code in have:
                continue
            metric = str(a["metric"])
            try:
                threshold = float(a["threshold"])
            except (TypeError, ValueError, KeyError):
                continue
            reward = float(from_units(settlement_units(a.get("reward", 0.0))))
            if metrics.get(metric, 0) < threshold:
                continue
            if not await self.ach_repo.create_if_absent(
                user_id=user.id, code=code, reward=reward
            ):
                continue
            if reward > 0:
                await self.user_repo.add_balance(user.id, reward, reason="achievement_reward")
            await ActionLogRepo(self.session).log(
                user_tg_id=user.tg_id,
                action="achievement",
                payload={"code": code, "reward": reward},
            )
            awarded.append(
                AwardedAchievement(
                    code=code,
                    name=str(a["name"]),
                    emoji=str(a.get("emoji", "🏅")),
                    reward=round(reward, 2),
                )
            )
        if awarded:
            log.info("achievements_awarded", user_tg_id=user.tg_id, count=len(awarded))
        return awarded

    async def list_for_user(self, user: User) -> list[AchievementView]:
        cfg = await self._config()
        metrics = await self._metrics(user)
        have = await self.ach_repo.get_codes(user.id)
        out: list[AchievementView] = []
        for a in cfg:
            code = str(a["code"])
            metric = str(a["metric"])
            try:
                threshold = int(a["threshold"])
            except (TypeError, ValueError, KeyError):
                continue
            unlocked = code in have
            current = int(metrics.get(metric, 0))
            out.append(
                AchievementView(
                    code=code,
                    name=str(a["name"]),
                    emoji=str(a.get("emoji", "🏅")),
                    metric=metric,
                    threshold=threshold,
                    reward=round(float(a.get("reward", 0.0)), 2),
                    current=min(current, threshold),
                    unlocked=unlocked,
                )
            )
        return out
