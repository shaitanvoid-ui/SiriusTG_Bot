"""Этап 11: поддержка (тикеты/антиспам/автозакрытие), уведомления, история."""

from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import select

import workers.support_autoclose as swork
import workers.tasks_rechecker as twork
from db.base import utcnow
from db.models import (
    ActionLog,
    Referral,
    TicketAuthor,
    TicketStatus,
    UserTaskCompletion,
)
from db.repositories.support import TicketRepo
from db.repositories.user import UserRepo
from services.history import HistoryService
from services.notifications import NotificationService
from services.referral import ReferralService
from services.settings import SettingsService
from services.sponsor import SponsorService
from services.support import CreateStatus, SupportService, make_subject
from tests.helpers import create_sponsor, create_user


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text, **kwargs):  # noqa: ARG002
        self.sent.append((chat_id, text))


# ---------- поддержка: создание ----------

async def test_create_ticket_ok(session):
    user = await create_user(session, tg_id=999000101)
    result = await SupportService(session).create_ticket(user, "Не приходит бонус\nУже два дня")
    assert result.status is CreateStatus.OK
    ticket = result.ticket
    assert ticket is not None
    assert ticket.status == TicketStatus.NEW.value
    assert ticket.subject == "Не приходит бонус"

    msgs = await TicketRepo(session).list_messages(ticket.id)
    assert len(msgs) == 1
    assert msgs[0].author == TicketAuthor.USER.value

    logs = await session.execute(
        select(ActionLog).where(ActionLog.action == "support_ticket_created")
    )
    assert logs.scalars().first() is not None


async def test_create_ticket_length_limits(session):
    user = await create_user(session, tg_id=999000102)
    svc = SupportService(session)
    too_short = await svc.create_ticket(user, "короче")
    assert too_short.status is CreateStatus.TOO_SHORT
    too_long = await svc.create_ticket(user, "х" * 2000)
    assert too_long.status is CreateStatus.TOO_LONG


async def test_create_ticket_antispam_per_hour(session):
    user = await create_user(session, tg_id=999000103)
    svc = SupportService(session)
    for i in range(3):
        result = await svc.create_ticket(user, f"Вопрос номер {i}, достаточно длинный")
        assert result.status is CreateStatus.OK
    fourth = await svc.create_ticket(user, "Четвёртый вопрос за этот же час")
    assert fourth.status is CreateStatus.TOO_MANY


async def test_create_ticket_disabled(session):
    user = await create_user(session, tg_id=999000104)
    await SettingsService(session).set("support.enabled", False)
    result = await SupportService(session).create_ticket(user, "Достаточно длинный вопрос")
    assert result.status is CreateStatus.DISABLED


def test_make_subject_truncates():
    assert make_subject("строка\nвторая") == "строка"
    long = "д" * 80
    subject = make_subject(long)
    assert len(subject) == 60 and subject.endswith("…")


# ---------- поддержка: статусы переписки ----------

async def test_reply_status_transitions(session):
    user = await create_user(session, tg_id=999000105)
    svc = SupportService(session)
    ticket = (await svc.create_ticket(user, "Вопрос про вывод звёзд")).ticket

    assert await svc.admin_reply(ticket, "Отвечаем: всё придёт") is not None
    assert ticket.status == TicketStatus.AWAITING.value

    assert await svc.user_reply(user, ticket, "Спасибо, но всё ещё нет") is not None
    assert ticket.status == TicketStatus.IN_PROGRESS.value

    msgs = await TicketRepo(session).list_messages(ticket.id)
    assert [m.author for m in msgs] == ["user", "admin", "user"]


async def test_reply_to_closed_and_foreign_ticket(session):
    user = await create_user(session, tg_id=999000106)
    other = await create_user(session, tg_id=999000107)
    svc = SupportService(session)
    ticket = (await svc.create_ticket(user, "Вопрос достаточно длинный")).ticket

    assert await svc.user_reply(other, ticket, "чужой тикет") is None

    assert await svc.close(ticket, by="user") is True
    assert ticket.status == TicketStatus.CLOSED.value and ticket.closed_at is not None
    assert await svc.close(ticket, by="user") is False
    assert await svc.user_reply(user, ticket, "уже закрыт") is None
    assert await svc.admin_reply(ticket, "тоже нельзя") is None


# ---------- поддержка: автозакрытие ----------

async def test_autoclose_closes_stale_awaiting(session, session_factory, monkeypatch):
    user = await create_user(session, tg_id=999000108)
    svc = SupportService(session)

    stale = (await svc.create_ticket(user, "Старый вопрос без реакции юзера")).ticket
    await svc.admin_reply(stale, "Ответ админа")
    stale.updated_at = utcnow() - timedelta(days=8)

    fresh = (await svc.create_ticket(user, "Свежий вопрос с ответом админа")).ticket
    await svc.admin_reply(fresh, "Ответ админа")

    waiting_admin = (await svc.create_ticket(user, "Новый вопрос, админ молчит")).ticket
    waiting_admin.updated_at = utcnow() - timedelta(days=8)
    await session.commit()

    stale_id, fresh_id, waiting_id = stale.id, fresh.id, waiting_admin.id
    monkeypatch.setattr(swork, "SessionLocal", session_factory)
    bot = FakeBot()
    await swork.run_support_autoclose(bot)

    session.expire_all()
    repo = TicketRepo(session)
    assert (await repo.get_by_id(stale_id)).status == TicketStatus.CLOSED.value
    assert (await repo.get_by_id(fresh_id)).status == TicketStatus.AWAITING.value
    # NEW не автозакрывается — это очередь админа
    assert (await repo.get_by_id(waiting_id)).status == TicketStatus.NEW.value
    assert any(chat_id == 999000108 and f"#{stale_id}" in text for chat_id, text in bot.sent)


# ---------- уведомления: преференции ----------

async def test_notify_prefs_default_and_toggle(session):
    user = await create_user(session, tg_id=999000109)
    assert NotificationService.prefs_of(user) == {"refs": True, "tasks": True, "rewards": True}
    assert NotificationService.is_enabled(user, "refs") is True

    user_id = user.id
    prefs = NotificationService.toggle(user, "refs")
    assert prefs["refs"] is False
    await session.commit()
    session.expire_all()

    fresh = await UserRepo(session).get_by_id(user_id)
    assert NotificationService.is_enabled(fresh, "refs") is False
    assert NotificationService.is_enabled(fresh, "tasks") is True

    # битый JSON не роняет — считаем всё включённым
    fresh.notify_prefs = "не json"
    assert NotificationService.is_enabled(fresh, "refs") is True


async def test_tasks_rechecker_respects_pref(session, session_factory, monkeypatch):
    user = await create_user(
        session, tg_id=999000110, balance=2.0, notify_prefs=json.dumps({"tasks": False})
    )
    sponsor = await create_sponsor(
        session, title="OptCh", is_required=False, reward=2.0, username="ch110"
    )
    session.add(UserTaskCompletion(user_id=user.id, sponsor_id=sponsor.id, reward=2.0))
    await session.commit()
    user_id = user.id

    monkeypatch.setattr(twork, "SessionLocal", session_factory)

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        return False

    monkeypatch.setattr(SponsorService, "check_one", fake_check)

    bot = FakeBot()
    await twork.run_tasks_rechecker(bot)

    session.expire_all()
    fresh = await UserRepo(session).get_by_id(user_id)
    assert round(fresh.balance, 2) == 0.0  # списание прошло
    assert all(chat_id != 999000110 for chat_id, _ in bot.sent)  # DM юзеру не ушло


async def test_ref_reward_event_carries_pref_and_history_log(session):
    referrer = await create_user(
        session, tg_id=999000111, notify_prefs=json.dumps({"refs": False})
    )
    referred = await create_user(session, tg_id=999000112)
    session.add(
        Referral(referrer_user_id=referrer.id, referred_user_id=referred.id)
    )
    await session.flush()

    svc = ReferralService(session, SettingsService(session))
    event = await svc.on_user_passed_subs(user=referred)
    assert event is not None
    assert event.notify_allowed is False

    # денежная запись для «📜 Истории» — от лица реферера
    logs = await session.execute(
        select(ActionLog).where(
            ActionLog.action == "ref_reward", ActionLog.user_tg_id == referrer.tg_id
        )
    )
    assert logs.scalars().first() is not None


# ---------- история операций ----------

async def _log(session, tg_id: int, action: str, payload: dict) -> None:
    session.add(
        ActionLog(user_tg_id=tg_id, action=action, payload=json.dumps(payload))
    )


async def test_history_amounts_and_exclusions(session):
    user = await create_user(session, tg_id=999000113)
    await _log(session, user.tg_id, "bonus_claimed", {"amount": 0.5, "streak": 3})
    await _log(session, user.tg_id, "wheel_spin", {"prize": 0.1, "free": False, "cost": 1.0})
    await _log(session, user.tg_id, "task_lost", {"sponsor_id": 1, "reward": 2.0})
    await _log(session, user.tg_id, "admin_balance_delta", {"delta": -1.5})
    await _log(session, user.tg_id, "promo_redeem", {"promo_id": 1, "code": "X", "reward": 3.0})
    await _log(session, user.tg_id, "click", {"reward": 0.1, "clicks": 1})  # исключён
    await session.flush()

    page = await HistoryService(session).page_for(user, 1)
    assert page.total_pages == 1
    assert len(page.entries) == 5  # click не попал

    by_title = {e.title: e for e in page.entries}
    assert by_title["Бонус дня"].amount == 0.5
    assert by_title["Колесо фортуны"].amount == -0.9  # приз 0.1 − спин 1.0
    assert by_title["Задание отменено"].amount == -2.0
    assert by_title["Корректировка баланса"].amount == -1.5
    assert by_title["Промокод «X»"].amount == 3.0


async def test_history_pagination(session):
    user = await create_user(session, tg_id=999000114)
    for i in range(10):
        await _log(session, user.tg_id, "bonus_claimed", {"amount": 0.5, "streak": i})
    await session.flush()

    svc = HistoryService(session)
    page1 = await svc.page_for(user, 1)
    assert page1.page == 1 and page1.total_pages == 2 and len(page1.entries) == 8
    page2 = await svc.page_for(user, 2)
    assert page2.page == 2 and len(page2.entries) == 2
    # выход за границы прижимается к последней странице
    page99 = await svc.page_for(user, 99)
    assert page99.page == 2


async def test_history_empty(session):
    user = await create_user(session, tg_id=999000115)
    page = await HistoryService(session).page_for(user, 1)
    assert page.entries == [] and page.total_pages == 1
