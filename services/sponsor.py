from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

from core.logger import get_logger
from db.models import Sponsor, SponsorKind, SubscriptionStatus
from db.repositories.sponsor import SponsorRepo
from db.repositories.user_subscription import UserSubscriptionRepo


log = get_logger(__name__)

_SUBSCRIBED_MEMBER_STATES: frozenset[str] = frozenset(
    {"member", "administrator", "creator"}
)
_NOT_SUBSCRIBED_MEMBER_STATES: frozenset[str] = frozenset({"left", "kicked"})

# простой in-memory кэш проверки подписки на 60 сек
_CHECK_CACHE_TTL_SEC: float = 60.0


class SubscriptionCheckStatus(StrEnum):
    SUBSCRIBED = "subscribed"
    NOT_SUBSCRIBED = "not_subscribed"
    UNAVAILABLE = "unavailable"


def normalize_check_status(
    value: SubscriptionCheckStatus | bool | str,
) -> SubscriptionCheckStatus:
    """Нормализует результат и сохраняет совместимость с тестовыми bool-заглушками."""
    if isinstance(value, bool):
        return (
            SubscriptionCheckStatus.SUBSCRIBED
            if value
            else SubscriptionCheckStatus.NOT_SUBSCRIBED
        )
    try:
        return SubscriptionCheckStatus(value)
    except (TypeError, ValueError):
        return SubscriptionCheckStatus.UNAVAILABLE


def _to_persisted_status(status: SubscriptionCheckStatus) -> SubscriptionStatus:
    if status == SubscriptionCheckStatus.SUBSCRIBED:
        return SubscriptionStatus.SUBSCRIBED
    if status == SubscriptionCheckStatus.NOT_SUBSCRIBED:
        return SubscriptionStatus.NOT_SUBSCRIBED
    return SubscriptionStatus.UNKNOWN


@dataclass(frozen=True)
class SponsorCheckResult:
    sponsor: Sponsor
    status: SubscriptionCheckStatus

    @property
    def is_subscribed(self) -> bool:
        return self.status == SubscriptionCheckStatus.SUBSCRIBED

    @property
    def is_definitively_not_subscribed(self) -> bool:
        return self.status == SubscriptionCheckStatus.NOT_SUBSCRIBED

    @property
    def is_unavailable(self) -> bool:
        return self.status == SubscriptionCheckStatus.UNAVAILABLE


class SponsorService:
    def __init__(
        self,
        sponsor_repo: SponsorRepo,
        sub_repo: UserSubscriptionRepo,
    ) -> None:
        self.sponsor_repo = sponsor_repo
        self.sub_repo = sub_repo
        self._cache: dict[
            tuple[int, int], tuple[float, SubscriptionCheckStatus]
        ] = {}

    async def list_required_active(self) -> list[Sponsor]:
        return await self.sponsor_repo.list_required_active()

    async def check_user(
        self,
        bot: Bot,
        *,
        tg_id: int,
        user_id: int,
        force: bool = False,
    ) -> tuple[bool, list[SponsorCheckResult]]:
        sponsors = await self.list_required_active()
        if not sponsors:
            return True, []

        results: list[SponsorCheckResult] = []
        all_ok = True
        now = time.monotonic()

        for sponsor in sponsors:
            cache_key = (tg_id, sponsor.id)
            cached = self._cache.get(cache_key)
            if not force and cached and (now - cached[0]) < _CHECK_CACHE_TTL_SEC:
                status = cached[1]
            else:
                status = normalize_check_status(
                    await self.check_one(bot, sponsor=sponsor, tg_id=tg_id)
                )
                if status != SubscriptionCheckStatus.UNAVAILABLE:
                    self._cache[cache_key] = (now, status)
                await self.sub_repo.upsert_status(
                    user_id=user_id,
                    sponsor_id=sponsor.id,
                    status=_to_persisted_status(status),
                )
            if status != SubscriptionCheckStatus.SUBSCRIBED:
                all_ok = False
            results.append(SponsorCheckResult(sponsor=sponsor, status=status))
        return all_ok, results

    async def check_one(
        self, bot: Bot, *, sponsor: Sponsor, tg_id: int
    ) -> SubscriptionCheckStatus:
        """Точечная проверка подписки на одного спонсора (зовут tasks/воркеры)."""
        chat_ref: int | str | None = None
        if sponsor.chat_id is not None:
            chat_ref = sponsor.chat_id
        elif sponsor.username:
            chat_ref = f"@{sponsor.username.lstrip('@')}"
        if chat_ref is None:
            log.warning("sponsor_no_chat_ref", sponsor_id=sponsor.id)
            return SubscriptionCheckStatus.UNAVAILABLE
        try:
            member = await bot.get_chat_member(chat_id=chat_ref, user_id=tg_id)
            member_status = str(getattr(member.status, "value", member.status)).lower()
            if member_status in _SUBSCRIBED_MEMBER_STATES:
                return SubscriptionCheckStatus.SUBSCRIBED
            if member_status == "restricted":
                return (
                    SubscriptionCheckStatus.SUBSCRIBED
                    if bool(getattr(member, "is_member", False))
                    else SubscriptionCheckStatus.NOT_SUBSCRIBED
                )
            if member_status in _NOT_SUBSCRIBED_MEMBER_STATES:
                return SubscriptionCheckStatus.NOT_SUBSCRIBED
            log.warning(
                "sponsor_unknown_member_status",
                sponsor_id=sponsor.id,
                status=member_status,
            )
            return SubscriptionCheckStatus.UNAVAILABLE
        except TelegramForbiddenError:
            log.warning(
                "sponsor_bot_not_admin", sponsor_id=sponsor.id, chat_ref=str(chat_ref)
            )
            return SubscriptionCheckStatus.UNAVAILABLE
        except TelegramBadRequest as e:
            log.warning(
                "sponsor_check_bad_request",
                sponsor_id=sponsor.id,
                chat_ref=str(chat_ref),
                err=str(e),
            )
            return SubscriptionCheckStatus.UNAVAILABLE
        except TelegramAPIError as e:
            log.warning(
                "sponsor_check_api_error",
                sponsor_id=sponsor.id,
                chat_ref=str(chat_ref),
                err=str(e),
            )
            return SubscriptionCheckStatus.UNAVAILABLE

    # обратная совместимость: метод был приватным до ревизии 2026-06-10
    _check_one = check_one

    def invalidate_cache(self, tg_id: int) -> None:
        keys = [k for k in self._cache if k[0] == tg_id]
        for k in keys:
            self._cache.pop(k, None)

    @staticmethod
    def display_link(sponsor: Sponsor) -> str:
        if sponsor.kind == SponsorKind.PUBLIC.value and sponsor.username:
            return f"https://t.me/{sponsor.username.lstrip('@')}"
        if sponsor.invite_link:
            return sponsor.invite_link
        if sponsor.username:
            return f"https://t.me/{sponsor.username.lstrip('@')}"
        return ""
