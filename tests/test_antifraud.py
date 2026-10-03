"""Deterministic fraud rules, durable contention, conservative gates and owner review."""
from __future__ import annotations

import asyncio
import importlib
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.types import CallbackQuery, User as TelegramUser
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, inspect, select, text

from bot.handlers.admin.antifraud import cb_confirm, cb_create_confirm
from bot.middlewares.antifraud import AntifraudMiddleware
from core.config import settings as app_settings
from db.antifraud_models import AntifraudEvent, AntifraudRateState, AntifraudSnapshot
from db.base import utcnow
from db.engine import create_app_engine
from db.models import MoneyOperation, PromoActivation, Sponsor, UserTaskCompletion
from db.repositories.user import UserRepo
from ml.risk import regular_click_pattern, score_rules
from services.antifraud import AntifraudService
from services.promo import PromoService, PromoStatus
from services.settings import SettingsService
from services.settings_validation import validate_setting_change, validate_setting_value
from services.tasks import TaskStatus, TasksService
from services.sponsor import SponsorService
from tests.helpers import create_promo, create_sponsor, create_user


def test_weak_signals_cannot_auto_shadow_even_if_weights_are_high():
    names = ("young_first_seen", "no_username", "ref_velocity", "rate_limit", "click_pattern")
    result = score_rules(dict.fromkeys(names, True), dict.fromkeys(names, 100), threshold=70)
    assert result.score == 100 and not result.should_shadow and not result.strong_signals
    assert not score_rules({"honeypot_task": True}, {"honeypot_task": 70}, threshold=70).should_shadow
    assert score_rules({"honeypot_task": True}, {"honeypot_task": 80}, threshold=70).should_shadow


def test_pattern_is_observable_and_requires_enough_positive_intervals():
    assert regular_click_pattern(list(range(0, 8000, 1000)), minimum=8, variation_permille=80)
    assert not regular_click_pattern(list(range(7)), minimum=8, variation_permille=80)
    assert not regular_click_pattern([0] * 8, minimum=8, variation_permille=80)
    assert not regular_click_pattern([0, 100, 300, 1300, 6000, 7200, 10000, 90000], minimum=8, variation_permille=80)


async def test_parallel_sliding_limit_is_global_durable_and_bounded(session, session_factory):
    user = await create_user(session, tg_id=7801001)
    await session.commit()
    now = utcnow()

    async def act():
        async with session_factory() as worker:
            result = await AntifraudService(worker).observe(actor_tg_id=user.tg_id, now=now)
            await worker.commit()
            return result

    results = await asyncio.gather(*(act() for _ in range(30)))
    assert sum(result.allowed for result in results) == 20
    assert all(result.retry_seconds == 60 for result in results if not result.allowed)
    async with session_factory() as restarted:
        svc = AntifraudService(restarted)
        assert not (await svc.observe(actor_tg_id=user.tg_id, now=now + timedelta(seconds=59))).allowed
        await restarted.commit()
    async with session_factory() as restarted:
        assert (await AntifraudService(restarted).observe(actor_tg_id=user.tg_id, now=now + timedelta(seconds=61))).allowed
        await restarted.commit()
        state = await restarted.get(AntifraudRateState, user.tg_id)
        assert len(json.loads(state.accepted_times_json)) == 1
        assert await restarted.scalar(select(func.count(AntifraudEvent.id)).where(AntifraudEvent.kind == "rate_limit")) == 1


async def test_civil_minute_boundary_does_not_double_allowance(session):
    now = utcnow().replace(second=59, microsecond=0)
    svc = AntifraudService(session)
    for _ in range(20):
        assert (await svc.observe(actor_tg_id=7801002, now=now)).allowed
    assert not (await svc.observe(actor_tg_id=7801002, now=now + timedelta(seconds=2))).allowed


async def test_regular_clicks_and_referral_velocity_only_create_observation(session):
    user = await create_user(session, tg_id=7801003, username=None)
    for number in range(10):
        await create_user(session, tg_id=7802000 + number, referrer_tg_id=user.tg_id)
    now = utcnow()
    svc = AntifraudService(session)
    for number in range(8):
        assert (await svc.observe(actor_tg_id=user.tg_id, click=True, now=now + timedelta(seconds=number))).allowed
    await session.refresh(user)
    snapshot = await session.get(AntifraudSnapshot, user.id)
    assert "click_pattern" in dict(json.loads(snapshot.reasons_json))
    assert "ref_velocity" in dict(json.loads(snapshot.reasons_json))
    assert snapshot.score == 50 and user.is_shadow_banned is False


async def test_middleware_uses_actual_actor_and_answers_rate_callback_once(session_factory, monkeypatch):
    bot = Bot("1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE")
    request = AsyncMock(return_value=True)
    monkeypatch.setattr(bot.session, "make_request", request)
    callback = CallbackQuery(id="limit", from_user=TelegramUser(id=7801004, is_bot=False, first_name="A"),
        chat_instance="local", data="adm:af:open").as_(bot)
    handler = AsyncMock()
    middleware = AntifraudMiddleware(session_factory)
    try:
        for _ in range(21):
            await middleware(handler, callback, {"actor_tg_id": app_settings.owner_id, "db_user": SimpleNamespace(tg_id=app_settings.owner_id)})
        assert handler.await_count == 20
        assert request.await_count == 1
        alert = request.call_args.args[1]
        assert alert.show_alert is True and "60" in alert.text
    finally:
        await bot.session.close()


async def test_limiter_commit_survives_handler_exception_and_owner_is_exempt(session_factory):
    callback = CallbackQuery(id="fail", from_user=TelegramUser(id=7801005, is_bot=False, first_name="A"),
        chat_instance="local", data="clk:tap")
    middleware = AntifraudMiddleware(session_factory)
    with pytest.raises(RuntimeError):
        await middleware(AsyncMock(side_effect=RuntimeError("handler failed")), callback, {})
    async with session_factory() as check:
        state = await check.get(AntifraudRateState, 7801005)
        assert len(json.loads(state.accepted_times_json)) == 1
    owner = callback.model_copy(update={"from_user": TelegramUser(id=app_settings.owner_id, is_bot=False, first_name="Owner")})
    handler = AsyncMock()
    await middleware(handler, owner, {})
    handler.assert_awaited_once()
    async with session_factory() as check:
        assert await check.get(AntifraudRateState, app_settings.owner_id) is None


async def test_honeypot_task_is_hidden_and_never_checks_subscription_or_rewards(session, monkeypatch):
    user = await create_user(session, tg_id=7801006, balance=12, reserved=3, debt=2)
    trap = await create_sponsor(session, title="Hidden", reward=100, username="not_a_real_channel", is_honeypot=True)
    normal = await create_sponsor(session, title="Real task", reward=1, username="real_channel")
    check = AsyncMock(side_effect=AssertionError("honeypot must precede Telegram I/O"))
    monkeypatch.setattr(SponsorService, "check_one", check)
    svc = TasksService(session, SettingsService(session))
    items = await svc.list_for_user(user)
    assert [item.sponsor.id for item in items] == [normal.id]
    result = await svc.claim(SimpleNamespace(), user=user, sponsor_id=trap.id)
    assert result.status == TaskStatus.BLOCKED
    check.assert_not_awaited()
    await session.refresh(user)
    await session.refresh(trap)
    assert user.is_shadow_banned and not user.is_banned
    assert (user.balance, user.reserved, user.debt) == (12, 3, 2)
    assert trap.subs_counter == 0
    assert await session.scalar(select(func.count(UserTaskCompletion.id))) == 0
    assert await session.scalar(select(func.count(MoneyOperation.id))) == 0
    assert await session.scalar(select(func.count(AntifraudEvent.id)).where(AntifraudEvent.kind == "honeypot_task")) == 1
    assert not await UserRepo(session).rewards_allowed(user.id)


async def test_honeypot_promo_keeps_status_but_shadow_not_hard_ban(session):
    user = await create_user(session, tg_id=7801007)
    promo = await create_promo(session, code="CONTROLTRAP", reward=10, max_activations=1, is_honeypot=True)
    result = await PromoService(session, SettingsService(session)).redeem(user=user, raw_code=promo.code)
    assert result.status == PromoStatus.HONEYPOT_BANNED
    await session.refresh(user)
    assert user.is_shadow_banned and not user.is_banned and user.balance == 0
    activation = await session.scalar(select(PromoActivation).where(PromoActivation.user_id == user.id))
    assert activation.is_honeypot_hit and activation.reward == 0
    assert await session.scalar(select(func.count(MoneyOperation.id))) == 0


async def test_traps_audit_without_auto_shadow_when_owner_disables_it(session):
    user = await create_user(session, tg_id=7801008)
    await SettingsService(session).set("antifraud.auto_shadow", False)
    promo = await create_promo(session, code="REVIEWONLY", is_honeypot=True)
    result = await PromoService(session, SettingsService(session)).redeem(user=user, raw_code=promo.code)
    await session.refresh(user)
    assert result.status == PromoStatus.HONEYPOT_BANNED
    assert not user.is_shadow_banned and user.balance == 0
    assert (await session.get(AntifraudSnapshot, user.id)).score >= 80


async def test_forged_or_unmarked_honeypot_evidence_is_rejected(session):
    user = await create_user(session, tg_id=7801009)
    real = await create_sponsor(session, reward=1)
    promo = await create_promo(session, code="NOCONSUMPTION", is_honeypot=True)
    svc = AntifraudService(session)
    with pytest.raises(ValueError, match="marked database"):
        await svc.honeypot_hit(user=user, kind="task", source_id=real.id)
    with pytest.raises(ValueError, match="activation evidence"):
        await svc.honeypot_hit(user=user, kind="promo", source_id=promo.id)
    assert await session.scalar(select(func.count(AntifraudEvent.id))) == 0
    assert user.is_shadow_banned is False


async def test_owner_reset_preserves_balances_ban_and_evidence_and_reviews_old_signals(session):
    user = await create_user(session, tg_id=7801010, balance=5, reserved=2, debt=1)
    trap = await create_sponsor(session, is_honeypot=True)
    svc = AntifraudService(session)
    await svc.honeypot_hit(user=user, kind="task", source_id=trap.id)
    user.is_banned = True
    await session.flush()
    with pytest.raises(PermissionError):
        await svc.reset(user_id=user.id, actor_tg_id=7801011, reason="Проверка по обращению пользователя")
    await svc.reset(user_id=user.id, actor_tg_id=app_settings.owner_id, reason="Проверка по обращению пользователя")
    await session.refresh(user)
    snapshot = await session.get(AntifraudSnapshot, user.id)
    assert snapshot.score == 0 and snapshot.generation == 1 and not user.is_shadow_banned
    assert user.is_banned and (user.balance, user.reserved, user.debt) == (5, 2, 1)
    await svc.observe(actor_tg_id=user.tg_id)
    assert not user.is_shadow_banned
    assert not json.loads(snapshot.strong_signals_json)
    assert await session.scalar(select(func.count(AntifraudEvent.id)).where(AntifraudEvent.kind == "honeypot_task")) == 1
    event = await session.scalar(select(AntifraudEvent).where(AntifraudEvent.kind == "owner_reset"))
    assert event.actor_tg_id == app_settings.owner_id and "Проверка" in json.loads(event.details_json)["reason"]


async def test_new_hit_after_review_uses_new_generation_and_can_restrict_again(session):
    user = await create_user(session, tg_id=7801012)
    trap = await create_sponsor(session, is_honeypot=True)
    svc = AntifraudService(session)
    await svc.honeypot_hit(user=user, kind="task", source_id=trap.id)
    await svc.honeypot_hit(user=user, kind="task", source_id=trap.id)
    assert await session.scalar(select(func.count(AntifraudEvent.id)).where(AntifraudEvent.kind == "honeypot_task")) == 1
    await svc.reset(user_id=user.id, actor_tg_id=app_settings.owner_id, reason="Проверка завершена владельцем")
    await svc.honeypot_hit(user=user, kind="task", source_id=trap.id)
    await session.refresh(user)
    assert user.is_shadow_banned
    assert await session.scalar(select(func.count(AntifraudEvent.id)).where(AntifraudEvent.kind == "honeypot_task")) == 2


async def test_hidden_task_creation_and_review_are_owner_only_and_do_not_alter_real_task(session):
    real = await create_sponsor(session, title="Real", reward=2, username="existing_channel")
    svc = AntifraudService(session)
    with pytest.raises(PermissionError):
        await svc.create_hidden_task(actor_tg_id=7801013)
    with pytest.raises(PermissionError):
        await svc.review_queue(actor_tg_id=7801013)
    with pytest.raises(PermissionError):
        await svc.review_detail(actor_tg_id=7801013, user_id=1)
    trap = await svc.create_hidden_task(actor_tg_id=app_settings.owner_id)
    await session.refresh(real)
    assert trap.is_honeypot and not trap.is_required and trap.reward == 0
    assert trap.username is None and trap.chat_id is None and trap.invite_link is None
    assert not real.is_honeypot and real.reward == 2 and real.username == "existing_channel"


async def test_replayed_owner_nonce_does_not_create_duplicate_or_clear_new_evidence(session):
    user = await create_user(session, tg_id=7801015)
    svc = AntifraudService(session)
    token = "a" * 32
    first = await svc.create_hidden_task(actor_tg_id=app_settings.owner_id, decision_token=token)
    repeated = await svc.create_hidden_task(actor_tg_id=app_settings.owner_id, decision_token=token)
    assert first.id == repeated.id
    assert await session.scalar(select(func.count(Sponsor.id))) == 1
    await svc.honeypot_hit(user=user, kind="task", source_id=first.id)
    await svc.reset(user_id=user.id, actor_tg_id=app_settings.owner_id, reason="Проверка подтверждена владельцем", decision_token=token)
    await svc.honeypot_hit(user=user, kind="task", source_id=first.id)
    await svc.reset(user_id=user.id, actor_tg_id=app_settings.owner_id, reason="Повтор старого подтверждения", decision_token=token)
    await session.refresh(user)
    assert user.is_shadow_banned
    assert await session.scalar(select(func.count(AntifraudEvent.id)).where(AntifraudEvent.kind == "owner_reset")) == 1


@pytest.mark.parametrize("key,value", [
    ("antifraud.actions_per_minute", 0), ("antifraud.shadow_threshold", 100),
    ("antifraud.weight_honeypot_task", -1), ("antifraud.weight_no_username", float("nan")),
    ("antifraud.window_seconds", 0.1), ("antifraud.auto_shadow", "true"),
])
def test_antifraud_settings_reject_invalid_numbers_and_flags(key, value):
    with pytest.raises(ValueError):
        validate_setting_value(key, value)


async def test_pattern_setting_pair_cannot_make_signal_unreachable(session):
    assert await validate_setting_change("antifraud.pattern_min_clicks", 20, SettingsService(session)) is not None


@pytest.mark.parametrize("handler", [cb_confirm, cb_create_confirm])
async def test_expired_or_forged_owner_confirmation_has_no_effect(session, handler):
    callback = SimpleNamespace(data="adm:af:confirm:forged", from_user=SimpleNamespace(id=app_settings.owner_id), answer=AsyncMock())
    state = AsyncMock()
    state.get_data.return_value = {"antifraud_owner": app_settings.owner_id, "antifraud_token": "valid",
        "antifraud_expiry": utcnow().timestamp() + 120, "antifraud_user_id": 1}
    await handler(callback, state, session)
    callback.answer.assert_awaited_once()
    assert await session.scalar(select(func.count(AntifraudEvent.id))) == 0
    assert await session.scalar(select(func.count(Sponsor.id))) == 0


@pytest.mark.parametrize("with_state", [False, True])
async def test_additive_migration_preserves_users_and_refuses_evidence_downgrade(tmp_path, with_state):
    migration = importlib.import_module("migrations.versions.0016_antifraud")
    engine = create_app_engine(f"sqlite+aiosqlite:///{tmp_path / 'migration.db'}")
    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, tg_id BIGINT NOT NULL)"))
            await connection.execute(text("INSERT INTO users VALUES (1, 7801014)"))
            def apply(conn):
                with Operations.context(MigrationContext.configure(conn)):
                    migration.upgrade()
                    assert "ix_antifraud_event_actor_time" in {row["name"] for row in inspect(conn).get_indexes("antifraud_events")}
                    if with_state:
                        conn.execute(text("INSERT INTO antifraud_rate_states (tg_id, accepted_times_json, click_times_json, updated_at) VALUES (7801014, '[]', '[]', CURRENT_TIMESTAMP)"))
                        with pytest.raises(RuntimeError, match="safety history"):
                            migration.downgrade()
                        assert "antifraud_rate_states" in inspect(conn).get_table_names()
                    else:
                        migration.downgrade()
                        assert "antifraud_rate_states" not in inspect(conn).get_table_names()
                    assert conn.execute(text("SELECT tg_id FROM users WHERE id=1")).scalar() == 7801014
            await connection.run_sync(apply)
    finally:
        await engine.dispose()
