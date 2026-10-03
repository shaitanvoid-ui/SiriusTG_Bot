"""Tri-state проверки подписок и безопасное поведение rechecker'ов."""

from __future__ import annotations

from types import SimpleNamespace

from aiogram.exceptions import TelegramAPIError

import workers.sub_rechecker as subwork
from db.base import utcnow
from db.models import SubscriptionStatus
from db.repositories.sponsor import SponsorRepo
from db.repositories.user import UserRepo
from db.repositories.user_subscription import UserSubscriptionRepo
from services.sponsor import SponsorService, SubscriptionCheckStatus
from tests.helpers import create_sponsor, create_user


class _ApiErrorBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def get_chat_member(self, **kwargs):  # noqa: ARG002
        raise TelegramAPIError(method=None, message="temporary Telegram error")  # type: ignore[arg-type]

    async def send_message(self, chat_id: int, text: str, **kwargs) -> None:  # noqa: ARG002
        self.sent.append((chat_id, text))


class _MemberBot:
    def __init__(self, status: str, *, is_member: bool | None = None) -> None:
        self.status = status
        self.is_member = is_member

    async def get_chat_member(self, **kwargs):  # noqa: ARG002
        values = {"status": self.status}
        if self.is_member is not None:
            values["is_member"] = self.is_member
        return SimpleNamespace(**values)


async def test_sponsor_service_records_api_error_as_unknown(session):
    user = await create_user(session, tg_id=999000060)
    sponsor = await create_sponsor(
        session,
        title="Required",
        username="required-api-error",
        is_required=True,
    )
    service = SponsorService(SponsorRepo(session), UserSubscriptionRepo(session))

    all_ok, results = await service.check_user(
        _ApiErrorBot(), tg_id=user.tg_id, user_id=user.id, force=True
    )

    assert all_ok is False
    assert results[0].status == SubscriptionCheckStatus.UNAVAILABLE
    rows = await UserSubscriptionRepo(session).list_for_user(user.id)
    assert len(rows) == 1
    assert rows[0].sponsor_id == sponsor.id
    assert rows[0].status == SubscriptionStatus.UNKNOWN.value


async def test_restricted_member_uses_is_member_flag(session):
    sponsor = await create_sponsor(session, username="restricted-check")
    service = SponsorService(SponsorRepo(session), UserSubscriptionRepo(session))

    subscribed = await service.check_one(
        _MemberBot("restricted", is_member=True), sponsor=sponsor, tg_id=1
    )
    left = await service.check_one(
        _MemberBot("restricted", is_member=False), sponsor=sponsor, tg_id=1
    )

    assert subscribed == SubscriptionCheckStatus.SUBSCRIBED
    assert left == SubscriptionCheckStatus.NOT_SUBSCRIBED


async def test_sub_rechecker_api_error_does_not_revoke_gate(
    session, session_factory, monkeypatch
):
    user = await create_user(
        session, tg_id=999000061, subs_passed_at=utcnow(), balance=3.0
    )
    await create_sponsor(
        session,
        title="Required",
        username="required-recheck",
        is_required=True,
    )
    await session.commit()
    user_id = user.id
    tg_id = user.tg_id
    monkeypatch.setattr(subwork, "SessionLocal", session_factory)

    bot = _ApiErrorBot()
    lost = await subwork._recheck_one(bot, tg_id=tg_id, user_id=user_id)

    session.expire_all()
    fresh = await UserRepo(session).get_by_id(user_id)
    assert lost is False
    assert fresh.subs_passed_at is not None
    assert fresh.balance == 3.0
    assert bot.sent == []


async def test_sub_rechecker_confirmed_left_revokes_gate(
    session, session_factory, monkeypatch
):
    user = await create_user(session, tg_id=999000062, subs_passed_at=utcnow())
    await create_sponsor(
        session,
        title="Required",
        username="required-confirmed-left",
        is_required=True,
    )
    await session.commit()
    user_id = user.id
    tg_id = user.tg_id
    monkeypatch.setattr(subwork, "SessionLocal", session_factory)

    bot = _MemberBot("left")
    bot.sent = []

    async def send_message(chat_id: int, text: str, **kwargs) -> None:  # noqa: ARG001
        bot.sent.append((chat_id, text))

    bot.send_message = send_message
    lost = await subwork._recheck_one(bot, tg_id=tg_id, user_id=user_id)

    session.expire_all()
    fresh = await UserRepo(session).get_by_id(user_id)
    assert lost is True
    assert fresh.subs_passed_at is None
    assert any(chat_id == tg_id for chat_id, _ in bot.sent)
