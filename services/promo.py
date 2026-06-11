"""Промокоды: redeem, honeypot-ban, базовая админ-логика.

Структура `Promo`: code, reward, max_activations (0 = безлимит), used_count,
expires_at, is_honeypot, is_active.

Honeypot: юзер, активировавший такой промокод, получает soft-ban
(`User.is_banned = True`), без начисления награды.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Promo, User
from db.repositories.action_log import ActionLogRepo
from db.repositories.promo import PromoRepo
from db.repositories.promo_activation import PromoActivationRepo
from db.repositories.user import UserRepo
from services.settings import SettingsService


class PromoStatus(StrEnum):
    OK = "ok"
    HONEYPOT_BANNED = "honeypot_banned"
    NOT_FOUND = "not_found"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"
    INACTIVE = "inactive"
    ALREADY_USED = "already_used"
    TOO_LONG = "too_long"
    EMPTY = "empty"


@dataclass(frozen=True)
class RedeemResult:
    status: PromoStatus
    reward: float = 0.0
    balance: float = 0.0
    code: str = ""


def normalize_code(raw: str) -> str:
    return raw.strip().upper().replace(" ", "")


class PromoService:
    def __init__(self, session: AsyncSession, settings_svc: SettingsService) -> None:
        self.session = session
        self.settings = settings_svc

    async def max_code_length(self) -> int:
        return await self.settings.get_int("promo.max_code_length", 32)

    async def redeem(self, *, user: User, raw_code: str) -> RedeemResult:
        code = normalize_code(raw_code)
        if not code:
            return RedeemResult(status=PromoStatus.EMPTY)
        max_len = await self.max_code_length()
        if len(code) > max_len:
            return RedeemResult(status=PromoStatus.TOO_LONG, code=code[:64])

        promo_repo = PromoRepo(self.session)
        promo = await promo_repo.get_by_code(code)
        if promo is None:
            return RedeemResult(status=PromoStatus.NOT_FOUND, code=code)

        activation_repo = PromoActivationRepo(self.session)
        existing = await activation_repo.get(promo.id, user.id)

        # honeypot — фиксируем активацию, баним юзера, никакой награды.
        if promo.is_honeypot:
            if existing is None:
                await activation_repo.create(
                    promo_id=promo.id,
                    user_id=user.id,
                    reward=0.0,
                    is_honeypot_hit=True,
                )
                await promo_repo.inc_used(promo.id, 1)
            await self._ban_user(user)
            await ActionLogRepo(self.session).log(
                user_tg_id=user.tg_id,
                action="promo_honeypot",
                payload={"promo_id": promo.id, "code": promo.code},
            )
            return RedeemResult(
                status=PromoStatus.HONEYPOT_BANNED,
                code=promo.code,
            )

        if not promo.is_active:
            return RedeemResult(status=PromoStatus.INACTIVE, code=promo.code)
        if existing is not None:
            return RedeemResult(status=PromoStatus.ALREADY_USED, code=promo.code)
        if _expired(promo):
            return RedeemResult(status=PromoStatus.EXPIRED, code=promo.code)
        if promo.max_activations > 0 and promo.used_count >= promo.max_activations:
            await promo_repo.set_active(promo.id, False)
            return RedeemResult(status=PromoStatus.EXHAUSTED, code=promo.code)

        # начисляем
        await activation_repo.create(
            promo_id=promo.id,
            user_id=user.id,
            reward=promo.reward,
            is_honeypot_hit=False,
        )
        await promo_repo.inc_used(promo.id, 1)
        await UserRepo(self.session).add_balance(user.id, promo.reward)

        # пере-проверим лимит после инкремента
        refreshed = await promo_repo.get(promo.id)
        if refreshed and refreshed.max_activations > 0 and refreshed.used_count >= refreshed.max_activations:
            await promo_repo.set_active(promo.id, False)

        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id,
            action="promo_redeem",
            payload={"promo_id": promo.id, "code": promo.code, "reward": promo.reward},
        )

        fresh_user = await UserRepo(self.session).get_by_id(user.id)
        balance = round(fresh_user.balance, 2) if fresh_user else round(user.balance + promo.reward, 2)

        return RedeemResult(
            status=PromoStatus.OK,
            reward=round(promo.reward, 2),
            balance=balance,
            code=promo.code,
        )

    async def _ban_user(self, user: User) -> None:
        from sqlalchemy import update

        await self.session.execute(
            update(User).where(User.id == user.id).values(is_banned=True)
        )


def _expired(promo: Promo) -> bool:
    if promo.expires_at is None:
        return False
    exp = promo.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp <= datetime.now(tz=timezone.utc)
