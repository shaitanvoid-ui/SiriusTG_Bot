"""Колесо фортуны.

  - 1 бесплатное вращение в сутки (UTC-день), лимит из settings.
  - Платное вращение: списываем `wheel.cost`, крутим, начисляем приз.
  - Секторы и веса — в `wheel.prizes` (матожидание держим < cost).

Все цифры — из settings, не хардкодом.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.models import User
from db.repositories.action_log import ActionLogRepo
from db.repositories.user import UserRepo
from db.repositories.wheel_spin import WheelSpinRepo
from services.settings import SettingsService


log = get_logger(__name__)

_DEFAULT_PRIZES: list[dict] = [
    {"value": 0.0, "weight": 30},
    {"value": 0.01, "weight": 25},
    {"value": 0.05, "weight": 20},
    {"value": 0.1, "weight": 15},
    {"value": 0.5, "weight": 7},
    {"value": 1.0, "weight": 3},
]


class SpinStatus(StrEnum):
    OK = "ok"
    NO_FREE = "no_free"          # бесплатное на сегодня уже потрачено
    NOT_ENOUGH = "not_enough"    # не хватает баланса на платное
    DISABLED = "disabled"


@dataclass(frozen=True)
class WheelView:
    free_available: bool
    cost: float
    balance: float
    can_pay: bool
    sectors: tuple[float, ...]   # значения секторов для превью (по убыванию веса/значения)


@dataclass(frozen=True)
class WheelResult:
    status: SpinStatus
    prize: float = 0.0
    balance: float = 0.0
    was_free: bool = False
    free_available: bool = False
    can_pay: bool = False


def _today() -> date:
    return datetime.now(tz=timezone.utc).date()


class WheelService:
    def __init__(self, session: AsyncSession, settings_svc: SettingsService) -> None:
        self.session = session
        self.settings = settings_svc
        self.repo = WheelSpinRepo(session)
        self.user_repo = UserRepo(session)

    async def _prizes(self) -> list[tuple[float, float]]:
        raw = await self.settings.get_list("wheel.prizes", _DEFAULT_PRIZES)
        out: list[tuple[float, float]] = []
        for p in raw:
            try:
                value = float(p["value"])
                weight = float(p["weight"])
            except (TypeError, ValueError, KeyError):
                continue
            if weight > 0:
                out.append((value, weight))
        if not out:
            return [(float(p["value"]), float(p["weight"])) for p in _DEFAULT_PRIZES]
        return out

    def _roll(self, prizes: list[tuple[float, float]]) -> float:
        total = sum(w for _, w in prizes)
        r = random.SystemRandom().uniform(0, total)
        upto = 0.0
        for value, weight in prizes:
            upto += weight
            if r <= upto:
                return value
        return prizes[-1][0]

    async def get_view(self, user: User) -> WheelView:
        cost = await self.settings.get_float("wheel.cost", 1.0)
        free_per_day = await self.settings.get_int("wheel.free_per_day", 1)
        used = await self.repo.count_free_today(user.id, _today())
        prizes = await self._prizes()
        sectors = tuple(
            sorted({round(v, 2) for v, _ in prizes if v > 0}, reverse=True)
        )
        return WheelView(
            free_available=used < free_per_day,
            cost=round(cost, 2),
            balance=round(user.balance, 2),
            can_pay=user.balance >= cost,
            sectors=sectors,
        )

    async def spin(self, user: User, *, paid: bool) -> WheelResult:
        if not await self.settings.get_bool("wheel.enabled", True):
            return WheelResult(status=SpinStatus.DISABLED, balance=round(user.balance, 2))

        cost = await self.settings.get_float("wheel.cost", 1.0)
        free_per_day = await self.settings.get_int("wheel.free_per_day", 1)
        today = _today()

        spent = 0.0
        if paid:
            if user.balance < cost:
                return WheelResult(
                    status=SpinStatus.NOT_ENOUGH,
                    balance=round(user.balance, 2),
                    free_available=await self._free_left(user, today, free_per_day),
                    can_pay=False,
                )
            await self.user_repo.subtract_with_debt(user.id, cost)
            spent = round(cost, 2)
            was_free = False
        else:
            used = await self.repo.count_free_today(user.id, today)
            if used >= free_per_day:
                return WheelResult(
                    status=SpinStatus.NO_FREE,
                    balance=round(user.balance, 2),
                    free_available=False,
                    can_pay=user.balance >= cost,
                )
            was_free = True

        prize = round(self._roll(await self._prizes()), 2)
        if prize > 0:
            await self.user_repo.add_balance(user.id, prize)

        await self.repo.create(
            user_id=user.id, day=today, prize=prize, cost=spent, is_free=was_free
        )
        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id,
            action="wheel_spin",
            payload={"prize": prize, "free": was_free, "cost": spent},
        )

        fresh = await self.user_repo.get_by_id(user.id)
        balance = round(fresh.balance, 2) if fresh else round(user.balance, 2)
        free_available = await self._free_left(user, today, free_per_day)
        log.info("wheel_spin", user_tg_id=user.tg_id, prize=prize, free=was_free)
        return WheelResult(
            status=SpinStatus.OK,
            prize=prize,
            balance=balance,
            was_free=was_free,
            free_available=free_available,
            can_pay=balance >= cost,
        )

    async def _free_left(self, user: User, today: date, free_per_day: int) -> bool:
        used = await self.repo.count_free_today(user.id, today)
        return used < free_per_day
