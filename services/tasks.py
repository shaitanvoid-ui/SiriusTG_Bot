"""Задания спонсоров: подписался на опц.канал → получил награду.

Используем существующий SponsorService для проверки подписки.
Анти-дубль через UserTaskCompletion (UQ user_id + sponsor_id).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Sponsor, User
from db.repositories.action_log import ActionLogRepo
from db.repositories.sponsor import SponsorRepo
from db.repositories.user import UserRepo
from db.repositories.user_subscription import UserSubscriptionRepo
from db.repositories.user_task_completion import UserTaskCompletionRepo
from services.settings import SettingsService
from services.sponsor import SponsorService


class TaskStatus(StrEnum):
    OK = "ok"
    NOT_SUBSCRIBED = "not_subscribed"
    ALREADY_DONE = "already_done"
    NOT_FOUND = "not_found"
    INACTIVE = "inactive"
    LIMIT_REACHED = "limit_reached"
    NO_REWARD = "no_reward"
    DISABLED = "disabled"


@dataclass(frozen=True)
class TaskItem:
    sponsor: Sponsor
    is_completed: bool


@dataclass(frozen=True)
class ClaimResult:
    status: TaskStatus
    reward: float = 0.0
    balance: float = 0.0
    sponsor_title: str = ""


class TasksService:
    def __init__(self, session: AsyncSession, settings_svc: SettingsService) -> None:
        self.session = session
        self.settings = settings_svc

    async def enabled(self) -> bool:
        return await self.settings.get_bool("tasks.enabled", True)

    async def list_for_user(self, user: User) -> list[TaskItem]:
        sponsors = await SponsorRepo(self.session).list_optional_active()
        if not sponsors:
            return []
        done_ids = await UserTaskCompletionRepo(self.session).list_completed_ids(user.id)
        items: list[TaskItem] = []
        for s in sponsors:
            # лимит достигнут — скрываем
            if s.subs_limit > 0 and s.subs_counter >= s.subs_limit:
                continue
            items.append(TaskItem(sponsor=s, is_completed=s.id in done_ids))
        return items

    async def claim(
        self,
        bot: Bot,
        *,
        user: User,
        sponsor_id: int,
    ) -> ClaimResult:
        if not await self.enabled():
            return ClaimResult(status=TaskStatus.DISABLED)

        repo = SponsorRepo(self.session)
        sponsor = await repo.get(sponsor_id)
        if sponsor is None:
            return ClaimResult(status=TaskStatus.NOT_FOUND)
        if not sponsor.is_active or sponsor.is_required:
            return ClaimResult(status=TaskStatus.INACTIVE, sponsor_title=sponsor.title)
        if sponsor.reward <= 0:
            return ClaimResult(status=TaskStatus.NO_REWARD, sponsor_title=sponsor.title)
        if sponsor.subs_limit > 0 and sponsor.subs_counter >= sponsor.subs_limit:
            await repo.set_active(sponsor.id, False)
            return ClaimResult(status=TaskStatus.LIMIT_REACHED, sponsor_title=sponsor.title)

        completion_repo = UserTaskCompletionRepo(self.session)
        existing = await completion_repo.get(user.id, sponsor.id)
        if existing is not None:
            return ClaimResult(status=TaskStatus.ALREADY_DONE, sponsor_title=sponsor.title)

        # проверяем подписку точечно (используем SponsorService для одного канала)
        sponsor_svc = SponsorService(repo, UserSubscriptionRepo(self.session))
        is_sub = await sponsor_svc.check_one(bot, sponsor=sponsor, tg_id=user.tg_id)
        if not is_sub:
            return ClaimResult(status=TaskStatus.NOT_SUBSCRIBED, sponsor_title=sponsor.title)

        # начисляем
        await completion_repo.create(
            user_id=user.id, sponsor_id=sponsor.id, reward=sponsor.reward
        )
        await UserRepo(self.session).add_balance(user.id, sponsor.reward)
        await repo.inc_counter(sponsor.id, 1)

        # доля партнёра, если спонсор партнёрский (Этап 10)
        if sponsor.partner_id is not None:
            from services.partner import PartnerService

            await PartnerService(self.session, self.settings).accrue_sponsor_share(
                sponsor, sponsor.reward
            )

        # авто-выкл при достижении лимита (после инкремента)
        refreshed = await repo.get(sponsor.id)
        if refreshed and refreshed.subs_limit > 0 and refreshed.subs_counter >= refreshed.subs_limit:
            await repo.set_active(sponsor.id, False)

        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id,
            action="task_done",
            payload={"sponsor_id": sponsor.id, "reward": sponsor.reward},
        )

        fresh_user = await UserRepo(self.session).get_by_id(user.id)
        balance = round(fresh_user.balance, 2) if fresh_user else round(user.balance + sponsor.reward, 2)

        return ClaimResult(
            status=TaskStatus.OK,
            reward=round(sponsor.reward, 2),
            balance=balance,
            sponsor_title=sponsor.title,
        )
