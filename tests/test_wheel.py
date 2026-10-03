"""Колесо фортуны: free 1/день, платное списывает cost, матожидание < cost."""

from __future__ import annotations

from db.repositories.user import UserRepo
from services.settings import SettingsService
from services.wheel import SpinStatus, WheelService
from tests.helpers import create_user


def _svc(session):
    return WheelService(session, SettingsService(session))


async def _set_single_prize(session, value: float) -> None:
    await SettingsService(session).set("wheel.prizes", [{"value": value, "weight": 1}])
    await session.commit()


async def test_free_spin_awards_and_consumes(session):
    await _set_single_prize(session, 0.5)
    user = await create_user(session, tg_id=999000601, balance=0.0)

    res = await _svc(session).spin(user, paid=False)
    assert res.status == SpinStatus.OK
    assert res.was_free is True
    assert res.prize == 0.5

    fresh = await UserRepo(session).get_by_id(user.id)
    assert round(fresh.balance, 2) == 0.5

    # второе бесплатное в тот же день — нельзя
    res2 = await _svc(session).spin(user, paid=False)
    assert res2.status == SpinStatus.NO_FREE


async def test_paid_spin_charges_cost(session):
    await _set_single_prize(session, 0.1)  # cost по умолчанию 1.0
    user = await create_user(session, tg_id=999000602, balance=5.0)

    await _svc(session).spin(user, paid=False)       # +0.1 → 5.1
    res = await _svc(session).spin(user, paid=True)  # -1.0 +0.1 → 4.2
    assert res.status == SpinStatus.OK

    fresh = await UserRepo(session).get_by_id(user.id)
    assert fresh.balance_units == 42000


async def test_paid_spin_not_enough(session):
    await _set_single_prize(session, 0.5)
    user = await create_user(session, tg_id=999000603, balance=0.5)  # < cost 1.0

    res = await _svc(session).spin(user, paid=True)
    assert res.status == SpinStatus.NOT_ENOUGH

    fresh = await UserRepo(session).get_by_id(user.id)
    assert round(fresh.balance, 2) == 0.5


async def test_disabled(session):
    await SettingsService(session).set("wheel.enabled", False)
    await session.commit()
    user = await create_user(session, tg_id=999000604, balance=5.0)
    res = await _svc(session).spin(user, paid=False)
    assert res.status == SpinStatus.DISABLED


async def test_expected_value_below_cost(session):
    """Дефолтные призы: матожидание держим ниже стоимости (дом в плюсе)."""
    svc = _svc(session)
    prizes = await svc._prizes()
    cost = await SettingsService(session).get_float("wheel.cost", 1.0)
    total_w = sum(w for _, w in prizes)
    ev = sum(v * w for v, w in prizes) / total_w
    assert ev < cost
