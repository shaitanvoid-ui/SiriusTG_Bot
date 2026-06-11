"""Реферальная бизнес-логика.

Жизненный цикл реферала:
  attach (пришёл по /start r<id>) → confirm (прошёл гейт подписок впервые)
    → matured (через N дней) | lost (отвалился до созревания)

Награды и лимиты — из settings, не хардкодом.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.logger import get_logger
from db.models import ReferralSource, User
from db.repositories.action_log import ActionLogRepo
from db.repositories.referral import ReferralRepo
from db.repositories.user import UserRepo
from services.notifications import NotificationService
from services.settings import SettingsService


log = get_logger(__name__)


@dataclass(frozen=True)
class AttachResult:
    attached: bool
    reason: str  # "ok" | "self" | "already_attached" | "no_referrer" | "limit" | "bad_referrer"


@dataclass(frozen=True)
class RewardEvent:
    referrer_user_id: int
    referrer_tg_id: int
    amount: float
    # выключил ли реферер DM-уведомления категории «refs» (Этап 11)
    notify_allowed: bool = True


@dataclass(frozen=True)
class RollbackEvent:
    referrer_user_id: int
    referrer_tg_id: int
    amount: float
    debt: float
    notify_allowed: bool = True


class ReferralService:
    def __init__(self, session, settings_service: SettingsService) -> None:
        self.session = session
        self.settings = settings_service
        self.user_repo = UserRepo(session)
        self.ref_repo = ReferralRepo(session)
        self.log_repo = ActionLogRepo(session)

    # ---------- attach ----------

    async def try_attach_referrer(
        self,
        *,
        user: User,
        referrer_tg_id: int,
        source: ReferralSource = ReferralSource.DIRECT,
    ) -> AttachResult:
        if referrer_tg_id == user.tg_id:
            return AttachResult(False, "self")
        if user.referrer_tg_id is not None:
            return AttachResult(False, "already_attached")
        existing = await self.ref_repo.get_by_referred(user.id)
        if existing is not None:
            return AttachResult(False, "already_attached")

        referrer = await self.user_repo.get_by_tg_id(referrer_tg_id)
        if referrer is None or referrer.is_banned or referrer.is_deleted:
            return AttachResult(False, "bad_referrer")

        daily_limit = await self.settings.get_int("ref.daily_limit", 0)
        if daily_limit > 0:
            today_count = await self.ref_repo.count_today_by_referrer(referrer.id)
            if today_count >= daily_limit:
                return AttachResult(False, "limit")

        await self.ref_repo.create(
            referrer_user_id=referrer.id,
            referred_user_id=user.id,
            source=source,
        )
        await self.user_repo.set_referrer(user.tg_id, referrer_tg_id)
        user.referrer_tg_id = referrer_tg_id
        await self.user_repo.inc_ref_count(referrer.id, +1)
        await self.log_repo.log(
            user_tg_id=user.tg_id,
            action="ref_attached",
            payload={"referrer_tg_id": referrer_tg_id, "source": source.value},
        )
        log.info("ref_attached", user_tg_id=user.tg_id, referrer_tg_id=referrer_tg_id)
        return AttachResult(True, "ok")

    # ---------- confirm (юзер прошёл гейт впервые) ----------

    async def on_user_passed_subs(self, *, user: User) -> RewardEvent | None:
        ref = await self.ref_repo.get_by_referred(user.id)
        if ref is None or ref.is_confirmed:
            return None
        reward = await self.settings.get_float("ref.reward", 3.0)
        await self.ref_repo.confirm(ref.id, reward=reward)
        await self.user_repo.add_balance(ref.referrer_user_id, reward)
        await self.user_repo.inc_confirmed_ref_count(ref.referrer_user_id, +1)
        referrer = await self.user_repo.get_by_id(ref.referrer_user_id)
        if referrer is None:
            return None
        await self.log_repo.log(
            user_tg_id=user.tg_id,
            action="ref_confirmed",
            payload={"referrer_tg_id": referrer.tg_id, "reward": reward},
        )
        # вторая запись — от лица реферера: его денежный поток для «📜 Истории»
        await self.log_repo.log(
            user_tg_id=referrer.tg_id,
            action="ref_reward",
            payload={"referred_tg_id": user.tg_id, "reward": reward},
        )
        log.info(
            "ref_confirmed",
            user_tg_id=user.tg_id,
            referrer_tg_id=referrer.tg_id,
            reward=reward,
        )
        return RewardEvent(
            referrer_user_id=referrer.id,
            referrer_tg_id=referrer.tg_id,
            amount=reward,
            notify_allowed=NotificationService.is_enabled(referrer, "refs"),
        )

    # ---------- rollback (юзер отвалился до созревания) ----------

    async def on_user_lost_subs(self, *, user: User) -> RollbackEvent | None:
        ref = await self.ref_repo.get_by_referred(user.id)
        if ref is None or not ref.is_confirmed or ref.is_matured:
            return None
        amount = ref.reward_amount
        debt = await self.user_repo.subtract_with_debt(ref.referrer_user_id, amount)
        await self.user_repo.inc_confirmed_ref_count(ref.referrer_user_id, -1)
        await self.ref_repo.mark_lost(ref.id, debt=debt)
        referrer = await self.user_repo.get_by_id(ref.referrer_user_id)
        if referrer is None:
            return None
        await self.log_repo.log(
            user_tg_id=user.tg_id,
            action="ref_lost",
            payload={"referrer_tg_id": referrer.tg_id, "amount": amount, "debt": debt},
        )
        # вторая запись — от лица реферера: его денежный поток для «📜 Истории»
        await self.log_repo.log(
            user_tg_id=referrer.tg_id,
            action="ref_reward_lost",
            payload={"referred_tg_id": user.tg_id, "amount": amount, "debt": debt},
        )
        log.info(
            "ref_lost",
            user_tg_id=user.tg_id,
            referrer_tg_id=referrer.tg_id,
            amount=amount,
            debt=debt,
        )
        return RollbackEvent(
            referrer_user_id=referrer.id,
            referrer_tg_id=referrer.tg_id,
            amount=amount,
            debt=debt,
            notify_allowed=NotificationService.is_enabled(referrer, "refs"),
        )

    # ---------- maturation (воркер) ----------

    async def process_maturation(self) -> int:
        days = await self.settings.get_int("ref.maturation_days", 7)
        items = await self.ref_repo.list_for_maturation(maturation_days=days, limit=500)
        matured = 0
        for ref in items:
            await self.ref_repo.mark_matured(ref.id)
            matured += 1
        if matured:
            log.info("ref_matured_batch", count=matured)
        return matured

    # ---------- статистика ----------

    async def stats(self, user_id: int) -> dict[str, float]:
        return await self.ref_repo.stats_for_referrer(user_id)
