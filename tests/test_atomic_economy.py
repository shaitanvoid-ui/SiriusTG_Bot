from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from db.models import WheelSpin
from db.repositories.user import UserRepo
from services.settings import SettingsService
from services.wheel import SpinStatus, WheelService
from tests.helpers import create_user


async def test_parallel_balance_additions_are_not_lost(session, session_factory) -> None:
    user = await create_user(session, tg_id=999001001)
    user_id = user.id
    await session.commit()

    async def add_once() -> None:
        async with session_factory() as worker_session:
            await UserRepo(worker_session).add_balance(user_id, 1.0)
            await worker_session.commit()

    await asyncio.gather(*(add_once() for _ in range(10)))

    async with session_factory() as check_session:
        fresh = await UserRepo(check_session).get_by_id(user_id)
        assert fresh is not None
        assert round(fresh.balance, 2) == 10.0


async def test_parallel_paid_spend_cannot_overdraw(session, session_factory) -> None:
    user = await create_user(session, tg_id=999001002, balance=1.0)
    user_id = user.id
    await session.commit()

    async def spend_once() -> bool:
        async with session_factory() as worker_session:
            won = await UserRepo(worker_session).try_spend_balance(user_id, 1.0)
            await worker_session.commit()
            return won

    results = await asyncio.gather(spend_once(), spend_once())
    assert sorted(results) == [False, True]


async def test_negative_add_balance_uses_debt_instead_of_negative_balance(session) -> None:
    user = await create_user(session, tg_id=999001004, balance=1.0)

    await UserRepo(session).add_balance(user.id, -2.5)
    await session.refresh(user)

    assert user.balance == 0.0
    assert user.debt == 1.5


async def test_parallel_free_wheel_uses_one_slot(session, session_factory) -> None:
    await SettingsService(session).set(
        "wheel.prizes", [{"value": 0.5, "weight": 1}]
    )
    user = await create_user(session, tg_id=999001003)
    user_id = user.id
    await session.commit()

    async def spin_once() -> SpinStatus:
        async with session_factory() as worker_session:
            worker_user = await UserRepo(worker_session).get_by_id(user_id)
            assert worker_user is not None
            result = await WheelService(
                worker_session, SettingsService(worker_session)
            ).spin(worker_user, paid=False)
            await worker_session.commit()
            return result.status

    statuses = await asyncio.gather(spin_once(), spin_once())
    assert sorted(statuses) == [SpinStatus.NO_FREE, SpinStatus.OK]

    async with session_factory() as check_session:
        count = await check_session.scalar(
            select(func.count(WheelSpin.id)).where(
                WheelSpin.user_id == user_id,
                WheelSpin.is_free.is_(True),
            )
        )
        fresh = await UserRepo(check_session).get_by_id(user_id)
        assert count == 1
        assert fresh is not None and round(fresh.balance, 2) == 0.5
