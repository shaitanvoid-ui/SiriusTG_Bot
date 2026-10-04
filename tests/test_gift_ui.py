"""Native UI authorization and confirmation contracts, using no Telegram API."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import gifts
from bot.handlers.admin import gifts as admin
from bot.keyboards.gifts import kb_admin_request, kb_gift, kb_request
from core.config import settings
from locales.ru import T
from services.gifts import GiftService
from userbot.gifts import Gift, GiftAdapterError, SenderStatus
from utils.rich import is_card, render_rich_html


def callback(data: str, *, tg_id: int = 42):
    return SimpleNamespace(data=data, from_user=SimpleNamespace(id=tg_id),
                           answer=AsyncMock(), message=AsyncMock())


def state(tg_id: int = 42) -> FSMContext:
    return FSMContext(MemoryStorage(), StorageKey(bot_id=1, chat_id=tg_id, user_id=tg_id))


def request(**changes):
    values = dict(id=7, title="<Gift & more>", gift_id=123, stars=15, cost_units=150000,
                  status="pending", reserve_state="held", recipient_tg_id=42,
                  confirmation_kind=None, proof=None, created_at=datetime.now(timezone.utc))
    return SimpleNamespace(**{**values, **changes})


def callbacks(markup):
    return [button.callback_data for row in markup.inline_keyboard for button in row if button.callback_data]


async def test_quote_commits_middleware_and_uses_server_actor_without_fsm_recipient():
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    cb, fsm = callback("gift:quote:123"), state()
    await fsm.update_data(recipient_tg_id=99999, gift_stars=1)
    async def quote(tg_id, gift_id):
        session.commit.assert_awaited_once()
        assert (tg_id, gift_id) == (42, 123)
        return SimpleNamespace(id="a" * 32, title="<gift>", stars=15, cost_units=150000,
                               expires_at=datetime.now(timezone.utc) + timedelta(seconds=120))
    svc.quote.side_effect = quote
    await gifts.cb_quote(cb, session, fsm, svc)
    data = await fsm.get_data()
    assert set(data) == {"gift_quote_token", "gift_quote_expires_at"}
    assert data["gift_quote_token"] == "a" * 32
    text = cb.message.edit_text.call_args.args[0]
    assert "&lt;gift&gt;" in text and "15 ед." in text
    assert callbacks(cb.message.edit_text.call_args.kwargs["reply_markup"]) == ["gift:confirm:" + "a" * 32, "gift:open"]
    svc.confirm.assert_not_called()


async def test_confirm_uses_callback_actor_and_durable_token_only():
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    cb, fsm = callback("gift:confirm:nonce"), state()
    await fsm.update_data(gift_quote_token="nonce", gift_quote_expires_at=int(time.time())+60,
                          recipient_tg_id=99999, gift_id=99999, cost_units=1)
    svc.confirm.return_value = request()
    svc.queue_position.return_value = 4
    await gifts.cb_confirm(cb, session, fsm, svc)
    session.commit.assert_awaited_once()
    svc.confirm.assert_awaited_once_with(42, "nonce")
    assert await fsm.get_data() == {}
    assert "Место в очереди: <b>4</b>" in cb.message.edit_text.call_args.args[0]


@pytest.mark.parametrize("saved_token, expires", [("other", int(time.time())+60), ("nonce", 0)])
async def test_stale_or_expired_confirm_never_reaches_service(saved_token, expires):
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    cb, fsm = callback("gift:confirm:nonce"), state()
    await fsm.update_data(gift_quote_token=saved_token, gift_quote_expires_at=expires)
    await gifts.cb_confirm(cb, session, fsm, svc)
    svc.confirm.assert_not_called()
    session.commit.assert_not_called()
    cb.answer.assert_awaited_once_with(T.stale_screen_alert, show_alert=True)


async def test_navigation_invalidates_pending_confirmation():
    svc, session = AsyncMock(spec=GiftService), AsyncMock()
    cb, fsm = callback("gift:history"), state()
    svc.history.return_value = []
    await fsm.update_data(gift_quote_token="old", gift_quote_expires_at=int(time.time())+60)
    await gifts.cb_history(cb, session, fsm, svc)
    cb.data = "gift:confirm:old"
    await gifts.cb_confirm(cb, session, fsm, svc)
    svc.confirm.assert_not_called()


async def test_catalogue_paginates_and_releases_sqlite_lock_before_adapter():
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    cb, fsm = callback("gift:page:1"), state()
    async def catalogue():
        session.commit.assert_awaited_once()
        return tuple(Gift(id, "G" * 120, 15) for id in range(1, 41))
    svc.catalogue.side_effect = catalogue
    await gifts.cb_page(cb, session, fsm, svc)
    text = cb.message.edit_text.call_args.args[0]
    keyboard = cb.message.edit_text.call_args.kwargs["reply_markup"]
    assert "Страница 2 из 7" in text and len(text) < 4096
    gift_buttons = [value for value in callbacks(keyboard) if value.startswith("gift:view:")]
    assert gift_buttons == [f"gift:view:{id}" for id in range(7, 13)]
    assert {"gift:page:0", "gift:page:2"} <= set(callbacks(keyboard))


async def test_adapter_errors_render_public_explanation_without_technical_exception():
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    cb, fsm = callback("gift:open"), state()
    svc.catalogue.side_effect = GiftAdapterError("not_authorized")
    await gifts.cb_open(cb, session, fsm, svc)
    text = cb.message.edit_text.call_args.args[0]
    assert text == T.gift_error_account
    assert "not_authorized" not in text and "MTProto" not in text


async def test_recipient_without_username_has_actionable_sender_contact_path():
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    cb, fsm = callback("gift:quote:123"), state()
    svc.quote.side_effect = GiftAdapterError("recipient_unresolved")
    svc.account.return_value = SenderStatus(True, tg_id=99, username="gift_sender", stars=50)
    await gifts.cb_quote(cb, session, fsm, svc)
    text = cb.message.edit_text.call_args.args[0]
    assert "@gift_sender" in text and "username необязателен" in text
    assert "sup:open" in callbacks(cb.message.edit_text.call_args.kwargs["reply_markup"])


async def test_cancel_requires_confirmation_and_owner_bound_service_detail():
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    cb, fsm = callback("gift:cancel:7"), state()
    svc.detail.return_value = request()
    svc.cancel.return_value = request(status="cancelled", reserve_state="released")
    await gifts.cb_cancel(cb, session, fsm, svc)
    svc.detail.assert_awaited_once_with(42, 7)
    svc.cancel.assert_not_called()
    cb.data = "gift:cancel_yes:7"
    await gifts.cb_cancel_confirm(cb, session, fsm, svc)
    svc.cancel.assert_awaited_once_with(42, 7)
    cb.data = "gift:cancel_yes:7"
    await gifts.cb_cancel_confirm(cb, session, fsm, svc)
    assert svc.cancel.await_count == 1


def test_unknown_payment_cannot_be_cancelled_or_retried_in_ui():
    unknown = request(status="reconciliation_required")
    assert not any("cancel" in item for item in callbacks(kb_request(unknown)))
    admin_callbacks = callbacks(kb_admin_request(unknown))
    assert not any(":retry" in item for item in admin_callbacks)
    assert any(":manual_success" in item for item in admin_callbacks)
    assert any(":proven_failure" in item for item in admin_callbacks)
    text = gifts.render_request(unknown)
    assert "резерв сохранён" in text and "Повторная покупка и возврат до сверки не запускаются" in text


def test_unsupported_gift_uses_native_disabled_action_and_exact_money_display():
    gift = Gift(1, "<gift>", 15, available=False, reason="gift_auction_unsupported")
    keyboard = kb_gift(gift.id, available=False)
    assert keyboard.inline_keyboard[0][0].disabled is not None
    assert keyboard.inline_keyboard[0][0].callback_data is None
    assert gifts.internal_cost(150001) == "15,0001 ед."
    assert gifts.internal_cost(-1) == "-0,0001 ед."
    text = gifts.render_gift(gift)
    assert "&lt;gift&gt;" in text and T.gift_unsupported in text
    assert is_card(text) and "<h2>" in render_rich_html(text)
    assert "<img" not in render_rich_html(text)


def test_gift_card_uses_live_admission_settings_and_explains_zero_daily_limit():
    gift = Gift(1, "Gift", 25)
    text = gifts.render_gift(gift, conditions=dict(minimum_units=200000, min_refs=3, daily_limit=2))
    assert "20 ед." in text and "<b>3</b>" in text and "<b>2</b>" in text
    assert "отсутствие долга" in text and "обязательные подписки" in text
    text = gifts.render_gift(gift, conditions=dict(minimum_units=150000, min_refs=5, daily_limit=0))
    assert T.gift_unlimited in text


async def test_non_owner_direct_call_cannot_decide_or_read_queue():
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    cb, fsm = callback("adm:gift:list:queue", tg_id=settings.owner_id+1), state()
    await admin.cb_list(cb, session, fsm, svc)
    cb.data = "adm:gift:decide:token"
    await admin.cb_decide(cb, session, fsm, svc)
    svc.admin_list.assert_not_called()
    svc.admin_decide.assert_not_called()
    session.commit.assert_not_called()


async def test_owner_reconciliation_requires_evidence_then_explicit_confirmation():
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    cb, fsm = callback("adm:gift:action:7:manual_success", tg_id=settings.owner_id), state(settings.owner_id)
    svc.admin_detail.return_value = dict(request=request(status="reconciliation_required"), attempts=[], audit=[])
    svc.admin_confirmation.return_value = "confirmed"
    await admin.cb_action(cb, session, fsm, svc)
    assert await fsm.get_state() == admin.GiftDecisionStates.evidence.state
    svc.admin_decide.assert_not_called()
    msg = SimpleNamespace(text="Проверена операция Telegram #123: подарок получен.",
                          from_user=SimpleNamespace(id=settings.owner_id), answer=AsyncMock())
    await admin.msg_evidence(msg, session, fsm, svc)
    svc.admin_confirmation.assert_awaited_once_with(settings.owner_id, 7, "manual_success")
    svc.admin_decide.assert_not_called()
    data = await fsm.get_data()
    assert data["gift_admin_token"] == "confirmed"
    cb.data = "adm:gift:decide:confirmed"
    svc.admin_detail.return_value = dict(request=request(status="succeeded", reserve_state="consumed", confirmation_kind="manual", proof=msg.text), attempts=[], audit=[])
    await admin.cb_decide(cb, session, fsm, svc)
    svc.admin_decide.assert_awaited_once_with(settings.owner_id, 7, "manual_success", "confirmed", msg.text)
    assert T.gift_confirmation_manual in cb.message.edit_text.call_args.args[0]
    assert await fsm.get_data() == {}


async def test_missing_evidence_and_stale_admin_confirmation_never_decide():
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    fsm = state(settings.owner_id)
    await fsm.set_state(admin.GiftDecisionStates.evidence)
    await fsm.update_data(gift_admin_request_id=7, gift_admin_action="proven_failure")
    msg = SimpleNamespace(text="не знаю", from_user=SimpleNamespace(id=settings.owner_id), answer=AsyncMock())
    await admin.msg_evidence(msg, session, fsm, svc)
    svc.admin_confirmation.assert_not_called()
    cb = callback("adm:gift:decide:stale", tg_id=settings.owner_id)
    await admin.cb_decide(cb, session, fsm, svc)
    svc.admin_decide.assert_not_called()
    cb.answer.assert_awaited_once_with(T.stale_screen_alert, show_alert=True)


async def test_missing_admin_request_is_explained_without_internal_error():
    session, svc = AsyncMock(), AsyncMock(spec=GiftService)
    cb, fsm = callback("adm:gift:request:777", tg_id=settings.owner_id), state(settings.owner_id)
    svc.admin_detail.return_value = dict(request=None, attempts=[], audit=[])
    await admin.cb_request(cb, session, fsm, svc)
    assert cb.message.edit_text.call_args.args[0] == T.gift_error_not_found


@pytest.mark.parametrize("code, expected", [
    ("restricted", "gift_error_access"), ("gates", "gift_error_gates"),
    ("minimum", "gift_error_minimum"), ("referrals", "gift_error_refs"),
    ("balance", "gift_error_funds"), ("cannot_cancel", "gift_error_cancel"),
    ("unsafe_retry", "gift_error_retry"), ("unreviewed_internal_error", "gift_error_unavailable"),
])
def test_business_failure_codes_have_safe_public_text(code, expected):
    assert gifts.error_text(code) == getattr(T, expected)
