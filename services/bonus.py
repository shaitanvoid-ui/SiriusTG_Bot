"""Ежедневный бонус + streak.

Правила (всё из settings, не хардкодом):
  - 1 бонус в сутки (московский день). Повтор — ALREADY.
  - Размер = ступень streak из `bonus.streak` (день→⭐), пол = `bonus.base`.
  - Пропустил день — streak сбрасывается на 1.
  - Бонус требует рефку в bio (`bonus.bio_required`, по умолчанию вкл).
    Проверка bio — через инъекцию bio_checker (Telethon). Если userbot
    недоступен — UNAVAILABLE, попытка не «сгорает».
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.models import User
from db.repositories.action_log import ActionLogRepo
from db.repositories.daily_bonus_log import DailyBonusLogRepo
from db.repositories.user import UserRepo
from services.settings import SettingsService
from utils.tz import today_msk


log = get_logger(__name__)

_DEFAULT_STREAK = {"1": 0.5, "3": 0.7, "7": 1.0, "14": 1.5, "30": 2.0}


class BonusStatus(StrEnum):
    OK = "ok"
    ALREADY = "already"            # уже получал сегодня
    BIO_MISSING = "bio_missing"    # bio без рефки
    UNAVAILABLE = "unavailable"    # userbot offline / не настроен


class BioOutcome(StrEnum):
    OK = "ok"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"


BioChecker = Callable[[], Awaitable[BioOutcome]]


@dataclass(frozen=True)
class BonusView:
    streak: int               # сколько дней подряд (с учётом сегодняшнего, если получен)
    today_amount: float       # сколько дадут/дали сегодня
    claimed_today: bool
    balance: float
    bio_required: bool
    next_threshold: int | None  # ближайшая ступень впереди
    next_amount: float | None


@dataclass(frozen=True)
class BonusResult:
    status: BonusStatus
    amount: float = 0.0
    streak: int = 0
    balance: float = 0.0


def _today() -> date:
    """День бонуса — московские сутки (хранение в БД остаётся UTC)."""
    return today_msk()


class BonusService:
    def __init__(self, session: AsyncSession, settings_svc: SettingsService) -> None:
        self.session = session
        self.settings = settings_svc
        self.user_repo = UserRepo(session)
        self.log_repo = DailyBonusLogRepo(session)

    async def tiers(self) -> dict[int, float]:
        """Ступени стрика (день → ⭐) — для отрисовки лесенки на карточке."""
        return await self._tiers()

    async def _tiers(self) -> dict[int, float]:
        raw = await self.settings.get_dict("bonus.streak", _DEFAULT_STREAK)
        out: dict[int, float] = {}
        for k, v in raw.items():
            try:
                out[int(k)] = float(v)
            except (TypeError, ValueError):
                continue
        return out or {int(k): float(v) for k, v in _DEFAULT_STREAK.items()}

    async def _amount_for_streak(self, streak: int) -> float:
        base = await self.settings.get_float("bonus.base", 0.5)
        tiers = await self._tiers()
        amount = base
        for threshold in sorted(tiers):
            if streak >= threshold:
                amount = tiers[threshold]
        return round(amount, 2)

    async def _next_tier(self, streak: int) -> tuple[int | None, float | None]:
        tiers = await self._tiers()
        ahead = sorted(t for t in tiers if t > streak)
        if not ahead:
            return None, None
        nxt = ahead[0]
        return nxt, round(tiers[nxt], 2)

    @staticmethod
    def _prospective_streak(user: User, today: date) -> int:
        """Каким станет streak, если получить бонус сегодня."""
        last = user.last_bonus_date
        if last is not None and (today - last).days == 1:
            return user.bonus_streak + 1
        return 1

    async def get_view(self, user: User) -> BonusView:
        today = _today()
        claimed = user.last_bonus_date == today
        streak = user.bonus_streak if claimed else self._prospective_streak(user, today)
        amount = await self._amount_for_streak(streak)
        nxt, nxt_amount = await self._next_tier(streak)
        bio_required = await self.settings.get_bool("bonus.bio_required", True)
        return BonusView(
            streak=streak,
            today_amount=amount,
            claimed_today=claimed,
            balance=round(user.balance, 2),
            bio_required=bio_required,
            next_threshold=nxt,
            next_amount=nxt_amount,
        )

    async def claim(self, user: User, *, bio_checker: BioChecker) -> BonusResult:
        today = _today()

        if user.last_bonus_date == today or await self.log_repo.get(user.id, today):
            return BonusResult(
                status=BonusStatus.ALREADY,
                streak=user.bonus_streak,
                balance=round(user.balance, 2),
            )

        bio_required = await self.settings.get_bool("bonus.bio_required", True)
        bio_ok = False
        if bio_required:
            outcome = await bio_checker()
            if outcome == BioOutcome.UNAVAILABLE:
                return BonusResult(
                    status=BonusStatus.UNAVAILABLE,
                    streak=user.bonus_streak,
                    balance=round(user.balance, 2),
                )
            if outcome == BioOutcome.MISSING:
                return BonusResult(
                    status=BonusStatus.BIO_MISSING,
                    streak=user.bonus_streak,
                    balance=round(user.balance, 2),
                )
            bio_ok = True

        streak = self._prospective_streak(user, today)
        amount = await self._amount_for_streak(streak)

        await self.user_repo.add_balance(user.id, amount)
        user.bonus_streak = streak
        user.last_bonus_date = today
        await self.log_repo.create(
            user_id=user.id, day=today, amount=amount, streak=streak, bio_ok=bio_ok
        )
        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id,
            action="bonus_claimed",
            payload={"amount": amount, "streak": streak, "bio_ok": bio_ok},
        )

        fresh = await self.user_repo.get_by_id(user.id)
        balance = round(fresh.balance, 2) if fresh else round(user.balance, 2)
        log.info("bonus_claimed", user_tg_id=user.tg_id, amount=amount, streak=streak)
        return BonusResult(
            status=BonusStatus.OK, amount=amount, streak=streak, balance=balance
        )
