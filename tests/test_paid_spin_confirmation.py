from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import func, select

from bot.handlers.wheel import cb_paid
from db.models import WheelSpin
from db.repositories.user import UserRepo
from locales.ru import T
from services.settings import SettingsService
from services.wheel import SpinStatus, WheelService
from tests.helpers import create_user


async def test_concurrent_duplicate_paid_token_charges_once(session, session_factory):
    user = await create_user(session, tg_id=777401, balance=5)
    await SettingsService(session).set("wheel.prizes", [{"value": .25, "weight": 1}])
    await session.commit()
    async def spin():
        async with session_factory() as transaction:
            current = await UserRepo(transaction).get_by_tg_id(777401)
            result = await WheelService(transaction, SettingsService(transaction)).spin(
                current, paid=True, request_token="same-confirmation",
            )
            await transaction.commit()
            return result.status
    outcomes = await asyncio.gather(spin(), spin())
    assert outcomes.count(SpinStatus.OK) == 1 and outcomes.count(SpinStatus.ALREADY) == 1
    await session.refresh(user)
    assert round(user.balance, 2) == 4.25
    assert await session.scalar(select(func.count(WheelSpin.id))) == 1


async def test_failed_paid_reservation_leaves_no_record_or_charge(session):
    user = await create_user(session, tg_id=777402, balance=.2)
    result = await WheelService(session, SettingsService(session)).spin(user, paid=True, request_token="unfunded")
    assert result.status == SpinStatus.NOT_ENOUGH
    assert await session.scalar(select(func.count(WheelSpin.id))) == 0
    await session.refresh(user)
    assert user.balance_units == 2000


async def test_price_change_invalidates_confirmation_without_charge(session):
    user = await create_user(session, tg_id=777403, balance=5)
    callback = SimpleNamespace(data="whl:paid:nonce", from_user=SimpleNamespace(id=user.tg_id),
                               message=AsyncMock(), answer=AsyncMock())
    state = AsyncMock()
    state.get_data.return_value = {"wheel_paid_token":"nonce", "wheel_paid_cost":2,
                                  "wheel_paid_expires_at":int(time.time())+60}
    await cb_paid(callback, session, state, user)
    callback.answer.assert_awaited_once_with(T.wheel_price_changed_alert, show_alert=True)
    assert await session.scalar(select(func.count(WheelSpin.id))) == 0
    assert user.balance == 5


async def test_expired_confirmation_is_rejected(session):
    callback = SimpleNamespace(data="whl:paid:old", answer=AsyncMock())
    state = AsyncMock()
    state.get_data.return_value = {"wheel_paid_token":"old", "wheel_paid_expires_at":0}
    await cb_paid(callback, session, state)
    callback.answer.assert_awaited_once_with(T.stale_screen_alert, show_alert=True)
