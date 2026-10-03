"""Промокоды: redeem, auditable honeypot evidence, базовая админ-логика.

Структура `Promo`: code, reward, max_activations (0 = безлимит), used_count,
expires_at, is_honeypot, is_active.

Honeypot не начисляет награду и создаёт объяснимый сигнал антифрода.
При настроенном пороге ограничиваются награды через is_shadow_banned.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Promo, User
from db.money import from_units, settlement_units
from db.repositories.action_log import ActionLogRepo
from db.repositories.promo import PromoRepo
from db.repositories.promo_activation import PromoActivationRepo
from db.repositories.user import UserRepo
from services.settings import SettingsService


class PromoStatus(StrEnum):
    BLOCKED = "blocked"
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
        if not await UserRepo(self.session).lock_rewards_allowed(user.id):
            return RedeemResult(status=PromoStatus.BLOCKED, balance=round(user.balance, 2))
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

        if not promo.is_active:
            return RedeemResult(status=PromoStatus.INACTIVE, code=promo.code)
        if existing is not None:
            return RedeemResult(status=PromoStatus.ALREADY_USED, code=promo.code)
        if _expired(promo):
            return RedeemResult(status=PromoStatus.EXPIRED, code=promo.code)
        if promo.max_activations > 0 and promo.used_count >= promo.max_activations:
            await promo_repo.set_active(promo.id, False)
            return RedeemResult(status=PromoStatus.EXHAUSTED, code=promo.code)

        # Слот и активация резервируются атомарно. Это закрывает двойное
        # начисление при быстрых callback'ах и превышение общего лимита.
        if not await promo_repo.try_reserve_use(promo.id):
            if await activation_repo.get(promo.id, user.id) is not None:
                return RedeemResult(status=PromoStatus.ALREADY_USED, code=promo.code)
            # Статус мог измениться между предварительной проверкой и
            # атомарным UPDATE: возвращаем точную причину, а не всегда exhausted.
            await self.session.refresh(promo)
            if _expired(promo):
                return RedeemResult(status=PromoStatus.EXPIRED, code=promo.code)
            if not promo.is_active and not (
                promo.max_activations > 0
                and promo.used_count >= promo.max_activations
            ):
                return RedeemResult(status=PromoStatus.INACTIVE, code=promo.code)
            return RedeemResult(status=PromoStatus.EXHAUSTED, code=promo.code)

        reward = from_units(settlement_units(promo.reward))
        created = await activation_repo.create_if_absent(
            promo_id=promo.id,
            user_id=user.id,
            reward=0.0 if promo.is_honeypot else reward,
            is_honeypot_hit=promo.is_honeypot,
        )
        if not created:
            await promo_repo.release_use(promo.id)
            return RedeemResult(status=PromoStatus.ALREADY_USED, code=promo.code)

        # Honeypot учитывает те же active/expiry/limit правила, без награды.
        if promo.is_honeypot:
            from services.antifraud import AntifraudService
            await AntifraudService(self.session, self.settings).honeypot_hit(
                user=user, kind="promo", source_id=promo.id,
            )
            await ActionLogRepo(self.session).log(
                user_tg_id=user.tg_id,
                action="promo_honeypot",
                payload={"promo_id": promo.id, "code": promo.code},
            )
            return RedeemResult(
                status=PromoStatus.HONEYPOT_BANNED,
                code=promo.code,
            )

        # начисляем
        await UserRepo(self.session).add_balance(user.id, reward, reason="promo_reward")

        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id,
            action="promo_redeem",
            payload={"promo_id": promo.id, "code": promo.code, "reward": reward},
        )

        fresh_user = await UserRepo(self.session).get_by_id(user.id)
        balance = round(fresh_user.balance, 2) if fresh_user else round(user.balance + reward, 2)

        return RedeemResult(
            status=PromoStatus.OK,
            reward=float(reward),
            balance=balance,
            code=promo.code,
        )

def _expired(promo: Promo) -> bool:
    if promo.expires_at is None:
        return False
    exp = promo.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp <= datetime.now(tz=timezone.utc)
