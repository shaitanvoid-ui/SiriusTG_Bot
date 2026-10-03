"""Read-only daily dashboard: honest availability, goals and next action."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ClickerDay, Sponsor, User, UserTaskCompletion, WheelSpin
from locales.ru import T
from services.bonus import BonusService
from services.level import LevelInfo, LevelService
from services.settings import SettingsService
from utils.tz import MSK, now_msk, today_msk
from userbot.client import is_configured


@dataclass(frozen=True)
class DailyAction:
    label: str
    callback: str
    detail: str
    complete: bool = False
    ready: bool = True


@dataclass(frozen=True)
class DashboardView:
    level: LevelInfo
    bonus_amount: float
    streak: int
    actions: tuple[DailyAction, ...]
    next_reset: datetime

    @property
    def next_action(self) -> DailyAction:
        return next((action for action in self.actions if not action.complete and action.ready), self.actions[-1])


class DashboardService:
    def __init__(self, session: AsyncSession, settings: SettingsService) -> None:
        self.session = session
        self.settings = settings

    async def get_view(self, user: User) -> DashboardView:
        await self.settings.preload()
        today = today_msk()
        level = await LevelService(self.settings).compute(user.confirmed_ref_count)
        bonus = await BonusService(self.session, self.settings).get_view(user)
        day = (await self.session.execute(select(ClickerDay).where(
            ClickerDay.user_id == user.id, ClickerDay.day == today,
        ))).scalar_one_or_none()
        free_used = select(func.count(WheelSpin.id)).where(
            WheelSpin.user_id == user.id, WheelSpin.day == today, WheelSpin.is_free.is_(True),
        ).scalar_subquery()
        done = select(UserTaskCompletion.sponsor_id).where(UserTaskCompletion.user_id == user.id)
        available_tasks = select(func.count(Sponsor.id)).where(
            Sponsor.is_active.is_(True), Sponsor.is_required.is_(False), Sponsor.reward > 0,
            (Sponsor.subs_limit == 0) | (Sponsor.subs_counter < Sponsor.subs_limit),
            Sponsor.id.not_in(done),
        ).scalar_subquery()
        free_count, task_count = (await self.session.execute(select(free_used, available_tasks))).one()
        clicks = day.clicks if day else 0
        cooldown = max(0, (day.last_click_ms if day else 0) +
                       await self.settings.get_int("click.min_interval_ms", 300000) -
                       int(now_msk().timestamp() * 1000)) if day and day.last_click_ms else 0
        actions: list[DailyAction] = []
        bonus_ready = not bonus.bio_required or is_configured()
        actions.append(DailyAction(
            T.daily_bonus_label, "bns:open",
            T.daily_done if bonus.claimed_today else (
                T.daily_bonus_available.format(amount=bonus.today_amount) if bonus_ready else T.daily_bonus_unavailable
            ),
            bonus.claimed_today, bonus_ready,
        ))
        if await self.settings.get_bool("wheel.enabled", True):
            free_limit = await self.settings.get_int("wheel.free_per_day", 1)
            if free_limit > 0:
                actions.append(DailyAction(
                    T.daily_wheel_label, "whl:open",
                    T.daily_done if free_count >= free_limit else T.daily_wheel_available,
                    free_count >= free_limit,
                ))
        click_detail = T.daily_clicks.format(current=clicks, total=level.click_daily_limit)
        if cooldown and clicks < level.click_daily_limit:
            click_detail += T.daily_cooldown.format(minutes=max(1, (cooldown + 59999) // 60000))
        actions.append(DailyAction(T.daily_clicker_label, "clk:open", click_detail,
                                   clicks >= level.click_daily_limit, cooldown == 0))
        if task_count and await self.settings.get_bool("tasks.enabled", True):
            actions.append(DailyAction(T.daily_tasks_label, "tsk:list", T.daily_tasks_available.format(count=task_count)))
        actions.append(DailyAction(T.daily_team_label, "ref:open", T.daily_team_hint))
        reset = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=MSK)
        return DashboardView(level, bonus.today_amount, bonus.streak, tuple(actions), reset)
