"""Воркер недельных выплат топу: начисление по местам, идемпотентность, выключение."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

import workers.leaderboard_payout as lw
from db.models import LeaderboardPayout, Referral
from db.repositories.user import UserRepo
from services.settings import SettingsService
from tests.helpers import create_user


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text, **kwargs):  # noqa: ARG002
        self.sent.append((chat_id, text))


async def _add_confirmed_refs(session, referrer, n):
    when = datetime.now(tz=timezone.utc)
    for i in range(n):
        referred = await create_user(session, tg_id=referrer.tg_id * 1000 + i)
        session.add(
            Referral(
                referrer_user_id=referrer.id,
                referred_user_id=referred.id,
                is_confirmed=True,
                is_rewarded=True,
                reward_amount=3.0,
                confirmed_at=when,
            )
        )
    await session.flush()


async def test_payout_credits_top(session, session_factory, monkeypatch):
    a = await create_user(session, tg_id=999000801, balance=0.0)
    b = await create_user(session, tg_id=999000802, balance=0.0)
    await _add_confirmed_refs(session, a, 20)
    await _add_confirmed_refs(session, b, 12)
    await session.commit()
    aid, bid = a.id, b.id

    monkeypatch.setattr(lw, "SessionLocal", session_factory)
    bot = FakeBot()
    await lw.run_leaderboard_payout(bot)

    session.expire_all()
    fa = await UserRepo(session).get_by_id(aid)
    fb = await UserRepo(session).get_by_id(bid)
    assert round(fa.balance, 2) == 50.0  # 1-е место
    assert round(fb.balance, 2) == 30.0  # 2-е место
    assert any(chat_id == 999000801 for chat_id, _ in bot.sent)

    rows = await session.execute(select(LeaderboardPayout))
    assert len(rows.scalars().all()) == 2


async def test_payout_idempotent(session, session_factory, monkeypatch):
    a = await create_user(session, tg_id=999000811, balance=0.0)
    await _add_confirmed_refs(session, a, 20)
    await session.commit()
    aid = a.id

    monkeypatch.setattr(lw, "SessionLocal", session_factory)
    await lw.run_leaderboard_payout(FakeBot())
    await lw.run_leaderboard_payout(FakeBot())  # второй прогон на той же неделе — no-op

    session.expire_all()
    fa = await UserRepo(session).get_by_id(aid)
    assert round(fa.balance, 2) == 50.0  # не задвоилось


async def test_payout_disabled(session, session_factory, monkeypatch):
    await SettingsService(session).set("leaderboard.payout_enabled", False)
    await session.commit()
    a = await create_user(session, tg_id=999000821, balance=0.0)
    await _add_confirmed_refs(session, a, 20)
    await session.commit()
    aid = a.id

    monkeypatch.setattr(lw, "SessionLocal", session_factory)
    await lw.run_leaderboard_payout(FakeBot())

    session.expire_all()
    fa = await UserRepo(session).get_by_id(aid)
    assert round(fa.balance, 2) == 0.0
