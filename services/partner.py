"""Партнёрская система (Этап 10).

Экономика (всё в settings, ставки переопределяются персонально в карточке партнёра):
  - источник «юзеры»: за каждого приведённого по UTM-ссылке юзера, прошедшего
    онбординг-гейт, партнёру начисляется `partner.reward_per_passed_user` ⭐
    (точка вызова — flow.finalize_subs_passed, идемпотентная);
  - источник «спонсоры»: с каждого выполненного задания по спонсору партнёра
    партнёру идёт `partner.percent_sponsor_reward`% от награды задания
    (точка вызова — TasksService.claim).

Выплаты: заявка на ВЕСЬ баланс, минимум `partner.min_payout_stars`, курс
`partner.rub_per_star` фиксируется в заявке. Звёзды резервируются сразу
(idempotency: одна pending-заявка на партнёра). Отклонение возвращает резерв.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case, func, select

from core.logger import get_logger
from core.crypto import CryptoError, decrypt_field, encrypt_field
from db.models import (
    ActionLog,
    Partner,
    PartnerLink,
    PartnerPayout,
    PartnerStatus,
    PayoutMethod,
    PayoutStatus,
    Sponsor,
    User,
)
from db.repositories.action_log import ActionLogRepo
from db.repositories.partner import PartnerLinkRepo, PartnerPayoutRepo, PartnerRepo
from db.repositories.user import UserRepo
from db.money import decimal_amount, from_units, settlement_units
from services.settings import SettingsService


log = get_logger(__name__)

_CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
_CODE_LEN = 8


class PayoutRequestStatus(StrEnum):
    OK = "ok"
    TOO_SMALL = "too_small"          # баланс меньше минимума
    ALREADY_PENDING = "already_pending"
    NOT_ACTIVE = "not_active"
    SECURE_STORAGE_UNAVAILABLE = "secure_storage_unavailable"


@dataclass(frozen=True)
class PartnerStats:
    balance: float
    total_earned: float
    links_count: int
    clicks: int
    joins: int
    passed: int


@dataclass(frozen=True)
class PayoutRequestResult:
    status: PayoutRequestStatus
    payout: PartnerPayout | None = None
    min_amount: float = 0.0


def _gen_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LEN))


class PartnerService:
    def __init__(self, session: AsyncSession, settings_svc: SettingsService) -> None:
        self.session = session
        self.settings = settings_svc
        self.repo = PartnerRepo(session)
        self.links = PartnerLinkRepo(session)
        self.payouts = PartnerPayoutRepo(session)

    # ---------- роль ----------

    async def get_for_user(self, user: User) -> Partner | None:
        """Партнёрская запись юзера (включая paused). None — не партнёр."""
        partner = await self.repo.get_by_user_id(user.id)
        if partner is None or partner.is_deleted:
            return None
        return partner

    async def assign(self, user: User) -> Partner:
        """Назначить юзера партнёром (или реактивировать)."""
        partner = await self.repo.get_by_user_id(user.id)
        if partner is None:
            partner = await self.repo.create(user.id)
        else:
            partner.is_deleted = False
            partner.status = PartnerStatus.ACTIVE.value
        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id, action="partner_assigned", payload={"partner_id": partner.id}
        )
        return partner

    # ---------- ставки ----------

    async def reward_per_user(self, partner: Partner) -> float:
        if partner.reward_per_user is not None:
            return float(partner.reward_per_user)
        return await self.settings.get_float("partner.reward_per_passed_user", 1.0)

    async def percent_sponsor(self, partner: Partner) -> float:
        if partner.percent_sponsor is not None:
            return float(partner.percent_sponsor)
        return await self.settings.get_float("partner.percent_sponsor_reward", 50.0)

    # ---------- атрибуция и начисления ----------

    async def track_start(self, user: User, code: str) -> None:
        """/start с payload p<code>: клик всегда, привязка — один раз до гейта."""
        link = await self.links.get_by_code(code)
        if link is None:
            return
        await self.links.inc_clicks(link.id)
        if user.partner_id is not None or user.subs_passed_at is not None:
            return
        partner = await self.repo.get(link.partner_id)
        if partner is None or partner.is_deleted:
            return
        # своя же ссылка — не атрибуцируем
        if partner.user_id == user.id:
            return
        if not await UserRepo(self.session).try_set_partner_attribution(
            user.id,
            partner_id=partner.id,
            partner_link_id=link.id,
        ):
            return
        await self.session.refresh(user)
        await self.links.inc_joins(link.id)
        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id,
            action="partner_join",
            payload={"partner_id": partner.id, "link_id": link.id},
        )

    async def accrue_passed_user(self, user: User) -> float:
        """CPA-начисление за прошедшего гейт юзера. Возвращает сумму (0 — не начислено).

        Идемпотентность обеспечивает вызывающий finalize_subs_passed
        (он срабатывает один раз на юзера).
        """
        if not await self.settings.get_bool("partner.enabled", True):
            return 0.0
        if user.partner_id is None or not await UserRepo(self.session).lock_rewards_allowed(user.id):
            return 0.0
        partner = await self.repo.get(user.partner_id)
        if partner is None or partner.is_deleted or partner.status != PartnerStatus.ACTIVE.value:
            return 0.0
        if not await UserRepo(self.session).lock_rewards_allowed(partner.user_id):
            return 0.0
        amount = float(from_units(settlement_units(await self.reward_per_user(partner))))
        if not await UserRepo(self.session).claim_partner_reward(user.id):
            return 0.0
        if user.partner_link_id is not None:
            await self.links.inc_passed(user.partner_link_id)
        if amount > 0:
            await self.repo.add_earning(partner.id, amount, reason="partner_commission")
            await ActionLogRepo(self.session).log(
                user_tg_id=user.tg_id,
                action="partner_cpa",
                payload={"partner_id": partner.id, "amount": amount},
            )
        return amount

    async def accrue_sponsor_share(self, sponsor: Sponsor, reward: float, *, task_user: User) -> float:
        """One commission per user/campaign, including after task revocation."""
        if not await self.settings.get_bool("partner.enabled", True):
            return 0.0
        if sponsor.partner_id is None or reward <= 0:
            return 0.0
        if not await UserRepo(self.session).lock_rewards_allowed(task_user.id):
            return 0.0
        # Legacy credits lack a user reference. A prior successful task is enough
        # to deny retroactive/repeated commission, even if its completion was
        # deleted. Malformed historical audit payloads must not abort a claim.
        prior_task = await self.session.scalar(select(ActionLog.id).where(
            ActionLog.user_tg_id == task_user.tg_id,
            ActionLog.action == "task_done",
            case((func.json_valid(ActionLog.payload) == 1,
                  func.json_extract(ActionLog.payload, "$.sponsor_id")), else_=None) == sponsor.id,
        ).limit(1))
        if prior_task is not None:
            return 0.0
        partner = await self.repo.get(sponsor.partner_id)
        if partner is None or partner.is_deleted or partner.status != PartnerStatus.ACTIVE.value:
            return 0.0
        percent = await self.percent_sponsor(partner)
        if not await UserRepo(self.session).lock_rewards_allowed(partner.user_id):
            return 0.0
        amount = float(from_units(settlement_units(decimal_amount(reward) * decimal_amount(percent) / 100)))
        if amount > 0:
            credited = await self.repo.add_earning(partner.id, amount, reason="partner_commission",
                reference=f"task-share:{task_user.id}:{sponsor.id}")
            if not credited:
                return 0.0
            await ActionLogRepo(self.session).log(
                user_tg_id=None,
                action="partner_share",
                payload={"partner_id": partner.id, "sponsor_id": sponsor.id,
                         "task_user_id": task_user.id, "amount": amount},
            )
        return amount

    # ---------- UTM-ссылки ----------

    async def create_link(self, partner: Partner, title: str) -> PartnerLink | None:
        """None — достигнут лимит ссылок."""
        max_links = await self.settings.get_int("partner.max_links", 10)
        for _ in range(5):  # коллизия 8-символьного code крайне маловероятна
            code = _gen_code()
            link = await self.links.create_if_below_limit(
                partner_id=partner.id,
                code=code,
                title=title[:64],
                limit=max_links,
            )
            if link is not None:
                return link
            if await self.links.count_for_partner(partner.id) >= max_links:
                return None
        return None  # pragma: no cover - только при пяти коллизиях code подряд

    # ---------- статистика ----------

    async def stats(self, partner: Partner) -> PartnerStats:
        totals = await self.links.totals_for_partner(partner.id)
        return PartnerStats(
            balance=round(partner.balance, 2),
            total_earned=round(partner.total_earned, 2),
            links_count=await self.links.count_for_partner(partner.id),
            clicks=totals["clicks"],
            joins=totals["joins"],
            passed=totals["passed"],
        )

    # ---------- выплаты ----------

    async def request_payout(
        self, partner: Partner, *, method: PayoutMethod, requisites: str
    ) -> PayoutRequestResult:
        """Заявка на выплату всего баланса. Резервирует звёзды сразу."""
        min_amount = await self.settings.get_float("partner.min_payout_stars", 50.0)
        if not await UserRepo(self.session).lock_rewards_allowed(partner.user_id) or partner.status != PartnerStatus.ACTIVE.value or partner.is_deleted:
            return PayoutRequestResult(status=PayoutRequestStatus.NOT_ACTIVE, min_amount=min_amount)
        if await self.payouts.get_pending_for_partner(partner.id) is not None:
            return PayoutRequestResult(
                status=PayoutRequestStatus.ALREADY_PENDING, min_amount=min_amount
            )
        amount = round(partner.balance, 2)
        if amount < min_amount:
            return PayoutRequestResult(status=PayoutRequestStatus.TOO_SMALL, min_amount=min_amount)
        try:
            encrypted_requisites = encrypt_field(requisites[:255])
        except CryptoError:
            log.exception("partner_payout_encryption_unavailable", partner_id=partner.id)
            return PayoutRequestResult(
                status=PayoutRequestStatus.SECURE_STORAGE_UNAVAILABLE,
                min_amount=min_amount,
            )
        if not await self.repo.reserve_payout_balance(partner.id, amount):
            if await self.payouts.get_pending_for_partner(partner.id) is not None:
                return PayoutRequestResult(
                    status=PayoutRequestStatus.ALREADY_PENDING,
                    min_amount=min_amount,
                )
            return PayoutRequestResult(
                status=PayoutRequestStatus.TOO_SMALL,
                min_amount=min_amount,
            )

        rate = await self.settings.get_float("partner.rub_per_star", 1.5)
        payout = await self.payouts.create(
            partner_id=partner.id,
            amount_stars=amount,
            rate_rub=rate,
            method=method.value,
            requisites=encrypted_requisites,
        )
        user = await UserRepo(self.session).get_by_id(partner.user_id)
        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id if user else None,
            action="partner_payout_requested",
            payload={"payout_id": payout.id, "stars": amount, "rub": payout.amount_rub},
        )
        log.info("partner_payout_requested", partner_id=partner.id, stars=amount)
        return PayoutRequestResult(status=PayoutRequestStatus.OK, payout=payout, min_amount=min_amount)

    @staticmethod
    def payout_requisites(payout: PartnerPayout) -> str:
        """Расшифровывает реквизиты только в момент показа уполномоченному админу."""
        return decrypt_field(payout.requisites)

    async def mark_payout_paid(self, payout_id: int) -> PartnerPayout | None:
        payout = await self.payouts.get(payout_id)
        if payout is None or payout.status != PayoutStatus.PENDING.value:
            return None
        if not await self.payouts.set_status(payout_id, PayoutStatus.PAID):
            return None
        if not await self.repo.consume_payout_reserve(payout.partner_id, payout.amount_stars, reference=f"partner:payout:consume:{payout.id}"):
            raise RuntimeError("partner payout reserve invariant failed")
        await ActionLogRepo(self.session).log(
            user_tg_id=None, action="partner_payout_paid", payload={"payout_id": payout_id}
        )
        return payout

    async def reject_payout(self, payout_id: int, note: str | None = None) -> PartnerPayout | None:
        """Отклонение заявки: резерв возвращается на баланс партнёра."""
        payout = await self.payouts.get(payout_id)
        if payout is None or payout.status != PayoutStatus.PENDING.value:
            return None
        if not await self.payouts.set_status(payout_id, PayoutStatus.REJECTED, note):
            return None
        if not await self.repo.refund_balance(payout.partner_id, payout.amount_stars, reference=f"partner:payout:release:{payout.id}"):
            raise RuntimeError("partner payout reserve invariant failed")
        await ActionLogRepo(self.session).log(
            user_tg_id=None, action="partner_payout_rejected", payload={"payout_id": payout_id}
        )
        return payout


async def encrypt_legacy_payout_requisites(session: AsyncSession) -> int:
    """Одноразово шифрует реквизиты, созданные до защищённого хранения."""
    rows = list(
        (
            await session.execute(
                select(PartnerPayout).where(
                    ~PartnerPayout.requisites.startswith("enc:v1:")
                )
            )
        ).scalars()
    )
    for payout in rows:
        payout.requisites = encrypt_field(payout.requisites)
    if rows:
        log.info("partner_requisites_encrypted", count=len(rows))
    return len(rows)
