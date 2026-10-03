"""Задача 3: воркер пере-проверки опц. заданий — списание при отписке."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

import workers.tasks_rechecker as twork
from db.models import ActionLog, UserTaskCompletion
from db.repositories.user import UserRepo
from db.repositories.user_task_completion import UserTaskCompletionRepo
from services.sponsor import SponsorService, SubscriptionCheckStatus
from tests.helpers import create_sponsor, create_user


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text, **kwargs):  # noqa: ARG002
        self.sent.append((chat_id, text))


async def _make_completion(session, *, tg_id, balance, reward, title="OptCh"):
    user = await create_user(session, tg_id=tg_id, balance=balance)
    sponsor = await create_sponsor(
        session, title=title, is_required=False, reward=reward, username=f"ch{tg_id}"
    )
    comp = UserTaskCompletion(user_id=user.id, sponsor_id=sponsor.id, reward=reward)
    session.add(comp)
    await session.commit()
    return user.id, user.tg_id, comp.id


async def test_unsubscribe_deducts_and_removes_completion(session, session_factory, monkeypatch):
    user_id, tg_id, comp_id = await _make_completion(
        session, tg_id=999000030, balance=2.0, reward=2.0
    )

    monkeypatch.setattr(twork, "SessionLocal", session_factory)

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        return False

    monkeypatch.setattr(SponsorService, "check_one", fake_check)

    bot = FakeBot()
    await twork.run_tasks_rechecker(bot)

    session.expire_all()
    fresh = await UserRepo(session).get_by_id(user_id)
    assert round(fresh.balance, 2) == 0.0
    assert round(fresh.debt, 2) == 0.0

    comp_after = await UserTaskCompletionRepo(session).get_by_id(comp_id)
    assert comp_after is None

    logs = await session.execute(select(ActionLog).where(ActionLog.action == "task_lost"))
    assert logs.scalars().first() is not None

    assert any(chat_id == tg_id for chat_id, _ in bot.sent), "юзеру должно уйти DM"


async def test_unsubscribe_with_low_balance_goes_to_debt(session, session_factory, monkeypatch):
    user_id, tg_id, comp_id = await _make_completion(
        session, tg_id=999000031, balance=0.5, reward=2.0
    )

    monkeypatch.setattr(twork, "SessionLocal", session_factory)

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        return False

    monkeypatch.setattr(SponsorService, "check_one", fake_check)

    await twork.run_tasks_rechecker(FakeBot())

    session.expire_all()
    fresh = await UserRepo(session).get_by_id(user_id)
    assert round(fresh.balance, 2) == 0.0
    assert round(fresh.debt, 2) == 1.5


async def test_lost_task_notification_escapes_sponsor_title(
    session, session_factory, monkeypatch
):
    _, tg_id, _ = await _make_completion(
        session,
        tg_id=999000036,
        balance=2.0,
        reward=2.0,
        title="<b>R&D</b>",
    )
    monkeypatch.setattr(twork, "SessionLocal", session_factory)

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        return SubscriptionCheckStatus.NOT_SUBSCRIBED

    monkeypatch.setattr(SponsorService, "check_one", fake_check)
    bot = FakeBot()
    await twork.run_tasks_rechecker(bot)

    user_messages = [text for chat_id, text in bot.sent if chat_id == tg_id]
    assert user_messages
    assert "&lt;b&gt;R&amp;D&lt;/b&gt;" in user_messages[0]
    assert "<b>R&D</b>" not in user_messages[0]


async def test_still_subscribed_keeps_completion(session, session_factory, monkeypatch):
    user_id, tg_id, comp_id = await _make_completion(
        session, tg_id=999000032, balance=2.0, reward=2.0
    )

    monkeypatch.setattr(twork, "SessionLocal", session_factory)

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        return True

    monkeypatch.setattr(SponsorService, "check_one", fake_check)

    bot = FakeBot()
    await twork.run_tasks_rechecker(bot)

    session.expire_all()
    fresh = await UserRepo(session).get_by_id(user_id)
    assert round(fresh.balance, 2) == 2.0

    comp_after = await UserTaskCompletionRepo(session).get_by_id(comp_id)
    assert comp_after is not None
    assert bot.sent == []


async def test_api_unavailable_keeps_balance_and_completion(
    session, session_factory, monkeypatch
):
    user_id, tg_id, comp_id = await _make_completion(
        session, tg_id=999000034, balance=2.0, reward=2.0
    )

    monkeypatch.setattr(twork, "SessionLocal", session_factory)

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        return SubscriptionCheckStatus.UNAVAILABLE

    monkeypatch.setattr(SponsorService, "check_one", fake_check)
    bot = FakeBot()
    await twork.run_tasks_rechecker(bot)

    session.expire_all()
    fresh = await UserRepo(session).get_by_id(user_id)
    assert round(fresh.balance, 2) == 2.0
    assert await UserTaskCompletionRepo(session).get_by_id(comp_id) is not None
    assert bot.sent == []


async def test_parallel_recheck_deducts_completion_only_once(
    session, session_factory, monkeypatch
):
    user_id, _, comp_id = await _make_completion(
        session, tg_id=999000035, balance=4.0, reward=2.0
    )
    monkeypatch.setattr(twork, "SessionLocal", session_factory)

    both_checks_started = asyncio.Event()
    check_count = 0

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        nonlocal check_count
        check_count += 1
        if check_count >= 2:
            both_checks_started.set()
        await both_checks_started.wait()
        return SubscriptionCheckStatus.NOT_SUBSCRIBED

    monkeypatch.setattr(SponsorService, "check_one", fake_check)

    results = await asyncio.gather(
        twork._recheck_one(FakeBot(), completion_id=comp_id),
        twork._recheck_one(FakeBot(), completion_id=comp_id),
    )
    assert sorted(results) == [False, True]

    session.expire_all()
    fresh = await UserRepo(session).get_by_id(user_id)
    assert fresh is not None
    assert fresh.balance == 2.0
    assert fresh.debt == 0.0


async def test_disabled_flag_skips_run(session, session_factory, monkeypatch):
    user_id, tg_id, comp_id = await _make_completion(
        session, tg_id=999000033, balance=2.0, reward=2.0
    )
    # выключаем воркер
    from services.settings import SettingsService

    await SettingsService(session).set("tasks_recheck.enabled", False)
    await session.commit()

    monkeypatch.setattr(twork, "SessionLocal", session_factory)

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        return False

    monkeypatch.setattr(SponsorService, "check_one", fake_check)

    await twork.run_tasks_rechecker(FakeBot())

    session.expire_all()
    fresh = await UserRepo(session).get_by_id(user_id)
    assert round(fresh.balance, 2) == 2.0  # ничего не списано
    comp_after = await UserTaskCompletionRepo(session).get_by_id(comp_id)
    assert comp_after is not None
