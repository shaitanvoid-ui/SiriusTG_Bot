"""Партнёрская система (Этап 10): роль, атрибуция, начисления, ссылки, выплаты."""

from __future__ import annotations

import asyncio

from db.base import utcnow
from db.models import PartnerStatus, PayoutMethod, PayoutStatus
from db.repositories.partner import PartnerLinkRepo, PartnerPayoutRepo, PartnerRepo
from db.repositories.user import UserRepo
from services.partner import PartnerService, PayoutRequestStatus
from services.settings import SettingsService
from services.sponsor import SponsorService
from services.tasks import TasksService, TaskStatus
from tests.helpers import create_sponsor, create_user


def _svc(session) -> PartnerService:
    return PartnerService(session, SettingsService(session))


# ---------- роль ----------

async def test_assign_and_reactivate(session):
    user = await create_user(session, tg_id=999001001)
    svc = _svc(session)

    assert await svc.get_for_user(user) is None
    partner = await svc.assign(user)
    assert partner.status == PartnerStatus.ACTIVE.value
    assert (await svc.get_for_user(user)).id == partner.id

    # повторное назначение не создаёт дубль, а реактивирует
    partner.is_deleted = True
    partner.status = PartnerStatus.PAUSED.value
    again = await svc.assign(user)
    assert again.id == partner.id
    assert again.is_deleted is False
    assert again.status == PartnerStatus.ACTIVE.value


# ---------- UTM: атрибуция ----------

async def test_track_start_attribution(session):
    owner = await create_user(session, tg_id=999001002)
    svc = _svc(session)
    partner = await svc.assign(owner)
    link = await svc.create_link(partner, "Тест")
    assert link is not None

    visitor = await create_user(session, tg_id=999001003)
    await svc.track_start(visitor, link.code)
    await session.refresh(link)
    assert link.clicks == 1 and link.joins == 1
    assert visitor.partner_id == partner.id
    assert visitor.partner_link_id == link.id

    # повторный клик: clicks растёт, joins нет, привязка не меняется
    await svc.track_start(visitor, link.code)
    await session.refresh(link)
    assert link.clicks == 2 and link.joins == 1

    # сам партнёр по своей ссылке не атрибуцируется
    await svc.track_start(owner, link.code)
    assert owner.partner_id is None

    # юзер, уже прошедший гейт, не атрибуцируется
    passed_user = await create_user(session, tg_id=999001004, subs_passed_at=utcnow())
    await svc.track_start(passed_user, link.code)
    assert passed_user.partner_id is None


async def test_parallel_track_start_keeps_single_attribution(session, session_factory):
    first_owner = await create_user(session, tg_id=999001017)
    second_owner = await create_user(session, tg_id=999001018)
    first_partner = await _svc(session).assign(first_owner)
    second_partner = await _svc(session).assign(second_owner)
    first_link = await _svc(session).create_link(first_partner, "first")
    second_link = await _svc(session).create_link(second_partner, "second")
    visitor = await create_user(session, tg_id=999001019)
    assert first_link is not None and second_link is not None
    visitor_id = visitor.id
    link_codes = [first_link.code, second_link.code]
    await session.commit()

    async def track(code: str) -> None:
        async with session_factory() as worker_session:
            worker_user = await UserRepo(worker_session).get_by_id(visitor_id)
            assert worker_user is not None
            await _svc(worker_session).track_start(worker_user, code)
            await worker_session.commit()

    await asyncio.gather(*(track(code) for code in link_codes))

    async with session_factory() as check_session:
        fresh_user = await UserRepo(check_session).get_by_id(visitor_id)
        fresh_first = await PartnerLinkRepo(check_session).get(first_link.id)
        fresh_second = await PartnerLinkRepo(check_session).get(second_link.id)
        assert fresh_user is not None
        assert (fresh_user.partner_id, fresh_user.partner_link_id) in {
            (first_partner.id, first_link.id),
            (second_partner.id, second_link.id),
        }
        assert fresh_first is not None and fresh_second is not None
        assert fresh_first.joins + fresh_second.joins == 1


# ---------- начисления ----------

async def test_accrue_passed_user_cpa(session):
    owner = await create_user(session, tg_id=999001005)
    svc = _svc(session)
    partner = await svc.assign(owner)
    link = await svc.create_link(partner, "CPA")

    visitor = await create_user(session, tg_id=999001006)
    await svc.track_start(visitor, link.code)

    amount = await svc.accrue_passed_user(visitor)
    assert amount == 1.0  # partner.reward_per_passed_user default
    await session.refresh(partner)
    await session.refresh(link)
    assert partner.balance == 1.0
    assert partner.total_earned == 1.0
    assert link.passed == 1

    # партнёр на паузе — начисления нет
    await PartnerRepo(session).set_status(partner.id, PartnerStatus.PAUSED)
    visitor2 = await create_user(session, tg_id=999001007)
    await session.refresh(partner)
    visitor2.partner_id = partner.id
    assert await svc.accrue_passed_user(visitor2) == 0.0


async def test_accrue_sponsor_share_with_override(session):
    owner = await create_user(session, tg_id=999001008)
    svc = _svc(session)
    partner = await svc.assign(owner)
    sponsor = await create_sponsor(
        session, title="P", is_required=False, reward=2.0, username="pchan"
    )
    sponsor.partner_id = partner.id

    first_user = await create_user(session, tg_id=999001028)
    amount = await svc.accrue_sponsor_share(sponsor, sponsor.reward, task_user=first_user)
    assert amount == 1.0  # 50% от 2.0 (дефолт)
    await session.refresh(partner)
    assert partner.balance == 1.0

    await PartnerRepo(session).set_rates(partner.id, percent_sponsor=25.0)
    await session.refresh(partner)
    second_user = await create_user(session, tg_id=999001029)
    amount = await svc.accrue_sponsor_share(sponsor, sponsor.reward, task_user=second_user)
    assert amount == 0.5  # персональные 25%


async def test_task_claim_pays_partner_share(session, monkeypatch):
    """Интеграция: claim задания по партнёрскому спонсору кормит партнёра."""
    owner = await create_user(session, tg_id=999001009)
    partner = await _svc(session).assign(owner)
    sponsor = await create_sponsor(
        session, title="P", is_required=False, reward=2.0, username="pchan2"
    )
    sponsor.partner_id = partner.id
    user = await create_user(session, tg_id=999001010)

    async def fake_check(self, bot, *, sponsor, tg_id):  # noqa: ARG001
        return True

    monkeypatch.setattr(SponsorService, "check_one", fake_check)

    r = await TasksService(session, SettingsService(session)).claim(
        None, user=user, sponsor_id=sponsor.id
    )
    assert r.status == TaskStatus.OK
    await session.refresh(partner)
    assert partner.balance == 1.0  # 50% от 2.0


# ---------- ссылки: лимит ----------

async def test_create_link_limit(session):
    owner = await create_user(session, tg_id=999001011)
    svc = _svc(session)
    partner = await svc.assign(owner)
    await SettingsService(session).set("partner.max_links", 2)

    assert await svc.create_link(partner, "1") is not None
    assert await svc.create_link(partner, "2") is not None
    assert await svc.create_link(partner, "3") is None
    assert await PartnerLinkRepo(session).count_for_partner(partner.id) == 2


async def test_parallel_create_link_respects_limit(session, session_factory):
    owner = await create_user(session, tg_id=999001016)
    partner = await _svc(session).assign(owner)
    partner_id = partner.id
    await SettingsService(session).set("partner.max_links", 1)
    await session.commit()

    async def create(title: str) -> bool:
        async with session_factory() as worker_session:
            worker_partner = await PartnerRepo(worker_session).get(partner_id)
            assert worker_partner is not None
            link = await _svc(worker_session).create_link(worker_partner, title)
            await worker_session.commit()
            return link is not None

    created = await asyncio.gather(create("one"), create("two"))
    assert sorted(created) == [False, True]

    async with session_factory() as check_session:
        assert await PartnerLinkRepo(check_session).count_for_partner(partner_id) == 1


# ---------- выплаты ----------

async def test_payout_lifecycle(session):
    owner = await create_user(session, tg_id=999001012)
    svc = _svc(session)
    partner = await svc.assign(owner)

    # меньше минимума
    await PartnerRepo(session).add_earning(partner.id, 10.0)
    await session.refresh(partner)
    res = await svc.request_payout(
        partner, method=PayoutMethod.CARD, requisites="1234 5678"
    )
    assert res.status == PayoutRequestStatus.TOO_SMALL

    # хватает: резервируем всё, курс фиксируется
    await PartnerRepo(session).add_earning(partner.id, 90.0)
    await session.refresh(partner)
    res = await svc.request_payout(
        partner, method=PayoutMethod.CARD, requisites="1234 5678"
    )
    assert res.status == PayoutRequestStatus.OK and res.payout is not None
    payout = res.payout
    assert payout.amount_stars == 100.0
    assert payout.rate_rub == 1.5
    assert payout.amount_rub == 150.0
    assert payout.requisites.startswith("enc:v1:")
    assert "1234 5678" not in payout.requisites
    assert svc.payout_requisites(payout) == "1234 5678"
    await session.refresh(partner)
    assert partner.balance == 0.0


    assert partner.total_earned == 100.0  # total не трогаем

    # вторая заявка при pending — отказ
    await PartnerRepo(session).add_earning(partner.id, 60.0)
    await session.refresh(partner)
    res2 = await svc.request_payout(
        partner, method=PayoutMethod.YOOMONEY, requisites="410011"
    )
    assert res2.status == PayoutRequestStatus.ALREADY_PENDING

    # отклонение возвращает резерв
    rejected = await svc.reject_payout(payout.id, "тест")
    assert rejected is not None
    await session.refresh(partner)
    assert partner.balance == 160.0  # 60 + возврат 100
    fresh = await PartnerPayoutRepo(session).get(payout.id)
    assert fresh.status == PayoutStatus.REJECTED.value

    # повторная обработка той же заявки — идемпотентно None
    assert await svc.reject_payout(payout.id) is None
    assert await svc.mark_payout_paid(payout.id) is None

    # новая заявка → выплачено
    res3 = await svc.request_payout(
        partner, method=PayoutMethod.YOOMONEY, requisites="410011"
    )
    assert res3.status == PayoutRequestStatus.OK
    paid = await svc.mark_payout_paid(res3.payout.id)
    assert paid is not None
    fresh = await PartnerPayoutRepo(session).get(res3.payout.id)
    assert fresh.status == PayoutStatus.PAID.value
    await session.refresh(partner)
    assert partner.balance == 0.0


async def test_parallel_payout_requests_create_only_one_pending(
    session, session_factory
):
    owner = await create_user(session, tg_id=999001015)
    partner = await _svc(session).assign(owner)
    await PartnerRepo(session).add_earning(partner.id, 100.0)
    partner_id = partner.id
    await session.commit()

    async def request_once() -> PayoutRequestStatus:
        async with session_factory() as worker_session:
            worker_partner = await PartnerRepo(worker_session).get(partner_id)
            assert worker_partner is not None
            result = await _svc(worker_session).request_payout(
                worker_partner,
                method=PayoutMethod.YOOMONEY,
                requisites="410011",
            )
            await worker_session.commit()
            return result.status

    statuses = await asyncio.gather(request_once(), request_once())
    assert sorted(statuses) == [
        PayoutRequestStatus.ALREADY_PENDING,
        PayoutRequestStatus.OK,
    ]

    async with session_factory() as check_session:
        fresh_partner = await PartnerRepo(check_session).get(partner_id)
        payouts = await PartnerPayoutRepo(check_session).list_for_partner(partner_id)
        assert fresh_partner is not None and fresh_partner.balance == 0.0
        assert len(payouts) == 1
        assert payouts[0].status == PayoutStatus.PENDING.value


# ---------- рендер панелей (формат-строки локалей) ----------

class _FakeMsg:
    def __init__(self) -> None:
        self.text: str | None = None
        self.markup = None

    async def edit_text(self, text, reply_markup=None, **kw) -> None:
        self.text = text
        self.markup = reply_markup


async def test_partner_panel_renders(session):
    from bot.handlers.partner import _render_root

    owner = await create_user(session, tg_id=999001013)
    partner = await _svc(session).assign(owner)
    msg = _FakeMsg()
    await _render_root(msg, session, partner)
    assert msg.text is not None and "партнёрская панель" in msg.text.lower()


async def test_admin_partner_card_renders(session):
    from bot.handlers.admin.partners import _render_card, _render_payouts, _render_root

    owner = await create_user(session, tg_id=999001014, username="pnick")
    partner = await _svc(session).assign(owner)

    msg = _FakeMsg()
    await _render_card(msg, session, partner)
    assert msg.text is not None and "Партнёр #" in msg.text

    msg2 = _FakeMsg()
    await _render_root(msg2, session)
    assert msg2.text is not None and "партнёры" in msg2.text.lower()

    owner.username = None
    owner.first_name = "<b>R&D</b>"
    await PartnerRepo(session).add_earning(partner.id, 100.0)
    await session.refresh(partner)
    payout_result = await _svc(session).request_payout(
        partner, method=PayoutMethod.CARD, requisites="1234 5678"
    )
    assert payout_result.status == PayoutRequestStatus.OK

    msg3 = _FakeMsg()
    await _render_payouts(msg3, session)
    assert msg3.text is not None
    assert "&lt;b&gt;R&amp;D&lt;/b&gt;" in msg3.text
    assert "<b>R&D</b>" not in msg3.text
    button_texts = [
        button.text
        for row in msg3.markup.inline_keyboard
        for button in row
        if button.text
    ]
    assert any("<b>R&D</b>" in text for text in button_texts)


# ---------- /start payload ----------

def test_partner_payload_parser():
    from bot.handlers.start import _parse_partner_code, _parse_referrer_tg_id

    assert _parse_partner_code("pabcd1234") == "abcd1234"
    assert _parse_partner_code("r12345") is None
    assert _parse_partner_code("p") is None
    assert _parse_partner_code(None) is None
    # реферальный парсер не ломается от партнёрского payload
    assert _parse_referrer_tg_id("pabcd1234") is None
