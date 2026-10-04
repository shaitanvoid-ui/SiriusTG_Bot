"""Partner task commissions remain bounded when an earned slot is reclaimed."""

import asyncio

from sqlalchemy import func, select

import workers.tasks_rechecker as task_worker
from db.models import ActionLog, MoneyOperation
from db.repositories.action_log import ActionLogRepo
from db.repositories.partner import PartnerRepo
from db.repositories.user import UserRepo
from db.repositories.user_task_completion import UserTaskCompletionRepo
from services.partner import PartnerService
from services.settings import SettingsService
from services.sponsor import SponsorService, SubscriptionCheckStatus
from services.tasks import TaskStatus, TasksService
from tests.helpers import create_sponsor, create_user
from tests.test_tasks_rechecker import FakeBot


async def setup_partner_task(session):
    owner = await create_user(session, tg_id=999007001)
    partner = await PartnerService(session, SettingsService(session)).assign(owner)
    user = await create_user(session, tg_id=999007002)
    sponsor = await create_sponsor(session, username="campaign", reward=2, subs_limit=1, partner_id=partner.id)
    await session.commit()
    return partner, user, sponsor


async def test_reclaimed_sponsor_slot_cannot_amplify_partner_commission(session, session_factory, monkeypatch):
    partner, user, sponsor = await setup_partner_task(session)
    subscribed = True

    async def check(self, bot, *, sponsor, tg_id):
        return SubscriptionCheckStatus.SUBSCRIBED if subscribed else SubscriptionCheckStatus.NOT_SUBSCRIBED

    monkeypatch.setattr(SponsorService, "check_one", check)
    monkeypatch.setattr(task_worker, "SessionLocal", session_factory)
    for _ in range(3):
        subscribed = True
        result = await TasksService(session, SettingsService(session)).claim(None, user=user, sponsor_id=sponsor.id)
        assert result.status == TaskStatus.OK
        completion = await UserTaskCompletionRepo(session).get(user.id, sponsor.id)
        completion_id = completion.id
        await session.commit()
        subscribed = False
        assert await task_worker._recheck_one(FakeBot(), completion_id=completion_id)
        await session.refresh(partner)
        await session.refresh(user)
        await session.refresh(sponsor)
        assert partner.balance == 1 and partner.total_earned == 1
        assert user.balance == 0 and user.debt == 0
        assert sponsor.subs_counter == 0 and sponsor.is_active
        await session.commit()

    # A distinct member of the same campaign still earns the normal commission.
    other = await create_user(session, tg_id=999007003)
    subscribed = True
    result = await TasksService(session, SettingsService(session)).claim(None, user=other, sponsor_id=sponsor.id)
    assert result.status == TaskStatus.OK
    await session.refresh(partner)
    assert partner.balance == 2
    journal = list((await session.scalars(select(MoneyOperation).where(
        MoneyOperation.account_kind == "partner", MoneyOperation.reason == "partner_commission"))).all())
    assert len(journal) == 2 and sum(row.balance_delta_units for row in journal) == 20000
    assert len({row.reference for row in journal}) == 2


async def test_concurrent_task_commission_is_durable_and_unique(session, session_factory):
    partner, user, sponsor = await setup_partner_task(session)
    user_id, sponsor_id = user.id, sponsor.id

    async def credit():
        async with session_factory() as worker_session:
            actor = await UserRepo(worker_session).get_by_id(user_id)
            campaign = await worker_session.get(type(sponsor), sponsor_id)
            amount = await PartnerService(worker_session, SettingsService(worker_session)).accrue_sponsor_share(
                campaign, campaign.reward, task_user=actor)
            await worker_session.commit()
            return amount

    assert sum(await asyncio.gather(credit(), credit())) == 1
    assert await credit() == 0  # New service/session, persistent journal key.
    await session.refresh(partner)
    assert partner.balance == 1
    assert await session.scalar(select(func.count()).select_from(MoneyOperation).where(
        MoneyOperation.reference == f"task-share:{user_id}:{sponsor_id}")) == 1


async def test_legacy_task_audit_prevents_another_unlinked_commission(session):
    partner, user, sponsor = await setup_partner_task(session)
    await PartnerRepo(session).add_earning(partner.id, 1, reason="partner_commission")
    await ActionLogRepo(session).log(user_tg_id=user.tg_id, action="task_done", payload={"sponsor_id": sponsor.id})
    await session.commit()
    service = PartnerService(session, SettingsService(session))
    assert await service.accrue_sponsor_share(sponsor, 2, task_user=user) == 0
    await session.refresh(partner)
    assert partner.balance == 1


async def test_malformed_legacy_audit_does_not_block_new_legitimate_task(session):
    partner, user, sponsor = await setup_partner_task(session)
    session.add(ActionLog(user_tg_id=user.tg_id, action="task_done", payload="broken legacy JSON"))
    await session.commit()
    assert await PartnerService(session, SettingsService(session)).accrue_sponsor_share(sponsor, 2, task_user=user) == 1


async def test_first_conversion_without_commission_is_not_paid_retroactively(session, monkeypatch):
    partner, user, sponsor = await setup_partner_task(session)
    async def subscribed(self, bot, *, sponsor, tg_id):
        return SubscriptionCheckStatus.SUBSCRIBED
    monkeypatch.setattr(SponsorService, "check_one", subscribed)
    settings_service = SettingsService(session)
    await settings_service.set("partner.enabled", False)
    result = await TasksService(session, settings_service).claim(None, user=user, sponsor_id=sponsor.id)
    assert result.status == TaskStatus.OK
    await session.commit()
    await settings_service.set("partner.enabled", True)
    await session.commit()
    assert await PartnerService(session, settings_service).accrue_sponsor_share(sponsor, 2, task_user=user) == 0
    await session.refresh(partner)
    assert partner.balance == 0
