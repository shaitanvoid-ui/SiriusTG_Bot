from __future__ import annotations

import time
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

from core.logger import get_logger
from db.models import Sponsor, SponsorKind, SubscriptionStatus
from db.repositories.sponsor import SponsorRepo
from db.repositories.user_subscription import UserSubscriptionRepo


log = get_logger(__name__)

_SUBSCRIBED_MEMBER_STATES: frozenset[str] = frozenset(
    {"member", "administrator", "creator", "restricted"}
)

# простой in-memory кэш проверки подписки на 60 сек
_CHECK_CACHE_TTL_SEC: float = 60.0


@dataclass
class SponsorCheckResult:
    sponsor: Sponsor
    is_subscribed: bool


class SponsorService:
    def __init__(
        self,
        sponsor_repo: SponsorRepo,
        sub_repo: UserSubscriptionRepo,
    ) -> None:
        self.sponsor_repo = sponsor_repo
        self.sub_repo = sub_repo
        self._cache: dict[tuple[int, int], tuple[float, bool]] = {}

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
                is_sub = cached[1]
            else:
                is_sub = await self.check_one(bot, sponsor=sponsor, tg_id=tg_id)
                self._cache[cache_key] = (now, is_sub)
                await self.sub_repo.upsert_status(
                    user_id=user_id,
                    sponsor_id=sponsor.id,
                    status=(
                        SubscriptionStatus.SUBSCRIBED
                        if is_sub
                        else SubscriptionStatus.NOT_SUBSCRIBED
                    ),
                )
            if not is_sub:
                all_ok = False
            results.append(SponsorCheckResult(sponsor=sponsor, is_subscribed=is_sub))
        return all_ok, results

    async def check_one(self, bot: Bot, *, sponsor: Sponsor, tg_id: int) -> bool:
        """Точечная проверка подписки на одного спонсора (зовут tasks/воркеры)."""
        chat_ref: int | str | None = None
        if sponsor.chat_id is not None:
            chat_ref = sponsor.chat_id
        elif sponsor.username:
            chat_ref = f"@{sponsor.username.lstrip('@')}"
        if chat_ref is None:
            log.warning("sponsor_no_chat_ref", sponsor_id=sponsor.id)
            return False
        try:
            member = await bot.get_chat_member(chat_id=chat_ref, user_id=tg_id)
            return member.status in _SUBSCRIBED_MEMBER_STATES
        except TelegramForbiddenError:
            log.warning(
                "sponsor_bot_not_admin", sponsor_id=sponsor.id, chat_ref=str(chat_ref)
            )
            return False
        except TelegramBadRequest as e:
            log.warning(
                "sponsor_check_bad_request",
                sponsor_id=sponsor.id,
                chat_ref=str(chat_ref),
                err=str(e),
            )
            return False
        except TelegramAPIError as e:
            log.warning(
                "sponsor_check_api_error",
                sponsor_id=sponsor.id,
                chat_ref=str(chat_ref),
                err=str(e),
            )
            return False

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
