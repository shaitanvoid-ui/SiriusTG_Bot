"""Isolated native gift flow with real dispatcher, SQLite/FSM and GiftService.

The FakeAdapter models a PaymentResult authoritative for the current invocation;
UnknownPayment deliberately cannot prove whether Telegram delivered a gift.
Every Bot API request is recorded locally. No account or real payment is used.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage, SendRichMessage
from aiogram.types import Chat, Message, RichMessage
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

import bot.middlewares.db as middleware_db
from bot.handlers import get_root_router
from bot.states.admin import EcoEditStates
from core.config import settings
from db.base import Base, utcnow
from db.engine import create_app_engine
from db.fsm_storage import SQLiteFSMStorage
from db.gift_models import GiftAdminDecision, GiftQuote, GiftRequest
from db.models import MoneyOperation
from db.repositories.setting import SettingRepo
from db.repositories.user import UserRepo
from locales.ru import T
from main import _setup_middlewares
from services.gifts import GiftService
from services.settings import DEFAULTS, SettingsService
from tests.helpers import create_user
from tests.test_gift_queue import FakeAdapter
from userbot.gifts import Gift, GiftAdapterError, SenderStatus, UnknownPayment
from bot.middlewares.presentation import PresentationMiddleware


def test_native_gift_flow_with_real_service_and_isolated_adapter(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "tests.test_gift_dispatcher", str(tmp_path)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Native gift dispatcher passed" in result.stdout


class NativeFakeAdapter(FakeAdapter):
    def __init__(self):
        super().__init__()
        self.read_error = None
        self.resolved_ids = []
        self.account_reads = 0

    async def catalogue(self, force=False):
        if self.read_error is not None:
            raise self.read_error
        return (Gift(7, "<Gift & more>", self.price, self.available),)

    async def sender_status(self):
        self.account_reads += 1
        return SenderStatus(True, tg_id=999, username="fake_sender", stars=500)

    async def resolve_recipient(self, tg_id, username):
        self.resolved_ids.append(tg_id)
        return await super().resolve_recipient(tg_id, username)

    async def pay(self, prepared):
        result = await super().pay(prepared)
        result.proof = dict(form_id=result.form_id, sender_id=result.sender_id,
                            recipient_id=result.recipient_id, gift_id=result.gift_id,
                            stars=result.stars, message_ids=[10101])
        return result


class RecordingGiftSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.message = None
        self.last_html = ""

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        raise AssertionError("Network and external media are forbidden")
        yield b""  # pragma: no cover

    def screen_for(self, bot, tg_id):
        self.message = Message(message_id=1, date=datetime.now(timezone.utc),
                               chat=Chat(id=tg_id, type="private"), text="SIRIUS").as_(bot)

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, AnswerCallbackQuery):
            return True
        assert isinstance(method, (SendMessage, SendRichMessage, EditMessageText)), type(method)
        rich = getattr(method, "rich_message", None)
        assert rich is None or rich.media is None
        self.last_html = rich.html if rich is not None else method.text
        assert "<img" not in self.last_html
        self.message = Message(
            message_id=getattr(method, "message_id", None) or 1,
            date=datetime.now(timezone.utc), chat=Chat(id=method.chat_id, type="private"),
            text=getattr(method, "text", None),
            rich_message=RichMessage(blocks=[]) if rich else None,
            reply_markup=method.reply_markup,
        ).as_(bot)
        return self.message


async def _scenario(folder: Path):
    recipient, stranger, owner = 777501, 777502, settings.owner_id
    # An ordinary admin still cannot administer the owner's sender/payment cap.
    settings.admin_ids_raw = str(stranger)
    engine = create_app_engine(f"sqlite+aiosqlite:///{folder / 'gifts.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        for key, (value, description) in DEFAULTS.items():
            await SettingRepo(session).set(key, value, description)
        await SettingRepo(session).set("gifts.enabled", True)
        await SettingRepo(session).set("gifts.daily_budget_stars", 500)
        for tg_id in (recipient, stranger, owner):
            await create_user(session, tg_id=tg_id, balance=100, username=f"user_{tg_id}",
                              first_name="<Анна>", confirmed_ref_count=5,
                              accepted_terms_at=utcnow(), captcha_passed_at=utcnow(), subs_passed_at=utcnow())
        await session.commit()
    SettingsService.invalidate()
    middleware_db.SessionLocal = factory
    adapter = NativeFakeAdapter()
    service = GiftService(factory, adapter)
    api = RecordingGiftSession()
    api.middleware(PresentationMiddleware())
    bot = Bot("1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE", session=api,
              default=DefaultBotProperties(parse_mode="HTML"))
    dispatcher = Dispatcher(storage=SQLiteFSMStorage(folder / "fsm.db"), events_isolation=SimpleEventIsolation())
    dispatcher["gift_service"] = service
    _setup_middlewares(dispatcher)
    dispatcher.include_router(get_root_router())
    update_id = 1

    def actor(tg_id):
        return dict(id=tg_id, is_bot=False, first_name="<Анна>", username=f"user_{tg_id}")

    async def tap(data, *, tg_id=recipient):
        nonlocal update_id
        if api.message is None or api.message.chat.id != tg_id:
            api.screen_for(bot, tg_id)
        start = len(api.calls)
        await dispatcher.feed_raw_update(bot, {"update_id": update_id, "callback_query": {
            "id": f"gift_{update_id}", "from": actor(tg_id), "chat_instance": "isolated-gifts",
            "message": api.message.model_dump(mode="json", exclude_none=True), "data": data,
        }})
        update_id += 1
        produced = api.calls[start:]
        assert produced, f"Callback {data} was not answered"
        assert not any(isinstance(call, AnswerCallbackQuery) and call.text == T.error_generic for call in produced), data
        return produced

    async def say(text, *, tg_id=owner):
        nonlocal update_id
        await dispatcher.feed_raw_update(bot, {"update_id": update_id, "message": {
            "message_id": update_id + 10, "date": int(datetime.now(timezone.utc).timestamp()),
            "chat": {"id": tg_id, "type": "private"}, "from": actor(tg_id), "text": text,
        }})
        update_id += 1

    def button(prefix):
        result = [key.callback_data for row in api.message.reply_markup.inline_keyboard
                  for key in row if key.callback_data and key.callback_data.startswith(prefix)]
        assert result, f"Missing button {prefix}"
        return result[0]

    async def balances(tg_id=recipient):
        async with factory() as session:
            user = await UserRepo(session).get_by_tg_id(tg_id)
            return user.balance_units, user.reserved_units

    async def count(model, *, reason=None):
        async with factory() as session:
            statement = select(func.count()).select_from(model)
            if reason is not None:
                statement = statement.where(model.reason == reason)
            return await session.scalar(statement)

    async def new_request():
        await tap("gift:quote:7")
        assert "25 ед." in api.last_html
        confirmation = button("gift:confirm:")
        await tap(confirmation)
        async with factory() as session:
            request = await session.scalar(select(GiftRequest).order_by(GiftRequest.id.desc()).limit(1))
            assert request.recipient_tg_id == recipient
            return request.id, confirmation

    try:
        # Catalogue/card/quote cannot reserve or buy anything.
        await tap("gift:open")
        catalogue = next(call for call in reversed(api.calls) if isinstance(call, EditMessageText))
        assert any(b.text == "🎁 <Gift & more> · 25 ед." for row in catalogue.reply_markup.inline_keyboard for b in row)
        assert any(isinstance(call, EditMessageText) and call.rich_message is not None for call in api.calls)
        await tap("gift:view:7")
        assert "&lt;Gift &amp; more&gt;" in api.last_html
        assert "25 Stars" in api.last_html and "25 ед." in api.last_html
        assert "15 ед." in api.last_html and "Подтверждённых друзей" in api.last_html
        assert await balances() == (1000000, 0) and adapter.calls == 0
        await tap("gift:quote:7")
        confirmation = button("gift:confirm:")
        assert await count(GiftQuote) == 1 and await count(GiftRequest) == 0
        assert await balances() == (1000000, 0) and adapter.calls == 0
        # A different actor cannot reuse the confirmation or read the request.
        calls = await tap(confirmation, tg_id=stranger)
        assert any(isinstance(call, AnswerCallbackQuery) and call.text == T.stale_screen_alert for call in calls)
        await tap(confirmation)
        assert await balances() == (750000, 250000)
        assert await count(GiftRequest) == 1 and await count(MoneyOperation, reason="gift_reserve") == 1
        assert adapter.calls == 0
        await tap(confirmation)
        assert await count(GiftRequest) == 1 and await count(MoneyOperation, reason="gift_reserve") == 1
        await tap("gift:request:1", tg_id=stranger)
        assert T.gift_error_not_found in api.last_html
        assert await balances(stranger) == (1000000, 0)
        # Explicit cancellation releases once without affecting the first request.
        cancelled_id, _ = await new_request()
        await tap(f"gift:cancel:{cancelled_id}")
        assert (await service.detail(recipient, cancelled_id)).status == "pending"
        cancel = button("gift:cancel_yes:")
        await tap(cancel)
        await tap(cancel)
        assert await count(MoneyOperation, reason="gift_release") == 1
        assert await balances() == (750000, 250000) and adapter.calls == 0
        # A successful fake PaymentResult consumes the first reserve exactly once.
        assert await service.process_one()
        await tap("gift:request:1")
        assert T.gift_confirmation_telegram in api.last_html
        assert await balances() == (750000, 0) and adapter.calls == 1
        # Price change at confirm creates no request or reserve.
        await tap("gift:quote:7")
        changed = button("gift:confirm:")
        adapter.price = 30
        await tap(changed)
        assert T.gift_error_price in api.last_html
        assert await count(GiftRequest) == 2 and await balances() == (750000, 0)
        adapter.price = 25
        # Unknown external outcome preserves funds and has no cancellation/retry.
        unknown_id, _ = await new_request()
        adapter.error = UnknownPayment("payment_unknown")
        assert await service.process_one()
        assert not await service.process_one()
        await tap(f"gift:request:{unknown_id}")
        assert T.gift_reconciliation_detail in api.last_html
        assert not any("cancel" in key.callback_data for row in api.message.reply_markup.inline_keyboard
                       for key in row if key.callback_data)
        assert await balances() == (500000, 250000) and adapter.calls == 2
        # Non-owner admin callback cannot make a decision or expose operations.
        before = await count(GiftAdminDecision)
        await tap(f"adm:gift:action:{unknown_id}:manual_success", tg_id=stranger)
        assert await count(GiftAdminDecision) == before
        assert (await service.detail(recipient, unknown_id)).status == "reconciliation_required"
        # Owner's retry is also disallowed on an unknown outcome.
        await tap(f"adm:gift:action:{unknown_id}:retry", tg_id=owner)
        assert await count(GiftAdminDecision) == before
        # Owner account/budget and details use the injected adapter/service.
        await tap("adm:gift:account", tg_id=owner)
        assert T.admin_gift_account_ready in api.last_html and "500" in api.last_html
        calls = await tap("adm:eco:k:gifts.daily_budget_stars", tg_id=stranger)
        assert any(isinstance(call, AnswerCallbackQuery) and call.text == T.admin_gift_owner_only for call in calls)
        forged = FSMContext(dispatcher.storage, StorageKey(bot_id=bot.id, chat_id=stranger, user_id=stranger))
        await forged.set_state(EcoEditStates.waiting_value)
        await forged.update_data(eco_key="gifts.daily_budget_stars")
        await say("999", tg_id=stranger)
        assert T.admin_gift_owner_only in api.last_html
        assert (await service.budget())["limit_stars"] == 500
        await tap("adm:eco:k:gifts.daily_budget_stars", tg_id=owner)
        await say("450", tg_id=owner)
        assert (await service.budget())["limit_stars"] == 450
        await tap(f"adm:gift:request:{unknown_id}", tg_id=owner)
        assert "Резервирование" in api.last_html
        await tap(f"adm:gift:action:{unknown_id}:manual_success", tg_id=owner)
        assert await count(GiftAdminDecision) == before
        await say("не знаю")
        assert T.admin_gift_evidence_invalid in api.last_html
        assert await count(GiftAdminDecision) == before
        evidence = "Владелец проверил операцию Telegram #10101 и наличие подарка у получателя."
        await say(evidence)
        decision = button("adm:gift:decide:")
        assert await count(GiftAdminDecision) == before+1
        assert (await service.detail(recipient, unknown_id)).status == "reconciliation_required"
        await tap(decision, tg_id=owner)
        await tap(decision, tg_id=owner)
        stored = await service.detail(recipient, unknown_id)
        assert stored.status == "succeeded" and stored.confirmation_kind == "manual"
        assert stored.proof == evidence
        assert await count(MoneyOperation, reason="gift_consume") == 2
        assert await balances() == (500000, 0) and adapter.calls == 2
        await tap(f"gift:request:{unknown_id}")
        assert T.gift_confirmation_manual in api.last_html
        # An unfamiliar adapter error receives reviewed text, never its RPC code.
        adapter.read_error = GiftAdapterError("unreviewed_mock_rpc_code")
        await tap("gift:open")
        assert T.gift_error_unavailable in api.last_html
        assert "unreviewed_mock_rpc_code" not in api.last_html
        assert adapter.resolved_ids and set(adapter.resolved_ids) == {recipient}
        assert adapter.calls == 2  # one success, one unknown; no blind repeat
        print(f"Native gift dispatcher passed: {update_id-1} updates, isolated SQLite/FSM, no network or real Stars")
    finally:
        await dispatcher.storage.close()
        await engine.dispose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(_scenario(Path(sys.argv[1])))
