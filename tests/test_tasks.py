"""Опц. задания: список и claim (ok → already_done)."""

from __future__ import annotations

from services.settings import SettingsService
from services.sponsor import SponsorService
from services.tasks import TasksService, TaskStatus
from tests.helpers import create_sponsor, create_user


async def test_list_shows_only_optional_active(session):
    user = await create_user(session, tg_id=999000020)
    await create_sponsor(session, title="Opt", is_required=False, is_active=True, reward=2.0, username="opt")
    await create_sponsor(session, title="Req", is_required=True, is_active=True, username="req")
    await create_sponsor(session, title="OptOff", is_required=False, is_active=False, username="off")

    svc = TasksService(session, SettingsService(session))
    items = await svc.list_for_user(user)
    assert len(items) == 1
    assert items[0].sponsor.title == "Opt"
    assert items[0].is_completed is False


async def test_claim_ok_then_already_done(session, monkeypatch):
    user = await create_user(session, tg_id=999000021)
    sponsor = await create_sponsor(session, title="Opt", is_required=False, reward=2.0, username="opt")
    svc = TasksService(session, SettingsService(session))

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        return True

    monkeypatch.setattr(SponsorService, "check_one", fake_check)

    r = await svc.claim(None, user=user, sponsor_id=sponsor.id)
    assert r.status == TaskStatus.OK
    assert r.reward == 2.0
    assert r.balance == 2.0

    r2 = await svc.claim(None, user=user, sponsor_id=sponsor.id)
    assert r2.status == TaskStatus.ALREADY_DONE


async def test_claim_not_subscribed(session, monkeypatch):
    user = await create_user(session, tg_id=999000022)
    sponsor = await create_sponsor(session, title="Opt", is_required=False, reward=2.0, username="opt")
    svc = TasksService(session, SettingsService(session))

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        return False

    monkeypatch.setattr(SponsorService, "check_one", fake_check)

    r = await svc.claim(None, user=user, sponsor_id=sponsor.id)
    assert r.status == TaskStatus.NOT_SUBSCRIBED
    assert r.balance == 0.0
