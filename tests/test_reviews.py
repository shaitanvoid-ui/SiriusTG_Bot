"""Отзывы (Этап 8): фильтры, модерация, публикация в канал + регрессии багфиксов.

Регрессии:
  - флоу был недостижим (на интро не было кнопки rev:start);
  - выбор анонимности был фиктивным (одна кнопка, инверсная логика);
  - публикация в reviews_channel_id не была реализована;
  - повторная модерация не отсекалась в хендлере.
"""

from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select

from bot.handlers.reviews import cb_review_anonymity
from bot.keyboards.reviews import (
    kb_review_anonymity,
    kb_review_intro,
    kb_review_rating,
    kb_review_text_step,
)
from bot.states.reviews import ReviewStates
from db.models import ReviewStatus, SupportTicket
from db.repositories.review import ReviewRepo
from db.repositories.user import UserRepo
from services.reviews import ReviewService
from services.settings import SettingsService
from tests.helpers import create_user


GOOD_TEXT = "Отличный бот, всё быстро и понятно, рекомендую друзьям и знакомым."


class _FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str, **kw) -> None:
        self.sent.append((chat_id, text))


# ---------- сервис: фильтры и создание ----------

async def test_create_review_filters(session):
    user = await create_user(session, tg_id=999000901, confirmed_ref_count=5)
    svc = ReviewService(session)

    r, err = await svc.create_review(user, 5, "коротко", False)
    assert r is None and err

    r, err = await svc.create_review(
        user, 5, "Бот хорош, вот ссылка https://spam.example и ещё немного текста", False
    )
    assert r is None

    r, err = await svc.create_review(user, 5, GOOD_TEXT, False)
    assert r is not None and r.status == ReviewStatus.PENDING.value


async def test_create_review_antispam_min_refs(session):
    user = await create_user(session, tg_id=999000902, confirmed_ref_count=0)
    r, err = await ReviewService(session).create_review(user, 5, GOOD_TEXT, False)
    assert r is None and "рефер" in err.lower()


# ---------- модерация ----------

async def test_moderate_approve_rewards_once(session):
    user = await create_user(session, tg_id=999000903, confirmed_ref_count=5)
    review = await ReviewRepo(session).create(user_id=user.id, rating=5, text=GOOD_TEXT)
    svc = ReviewService(session)

    res, key = await svc.moderate(review.id, "approve")
    assert res is not None and key == "approved"
    await session.refresh(user)
    assert user.balance == 1.0  # review.reward default
    assert res.status == ReviewStatus.APPROVED.value

    # повторная модерация — идемпотентно, без второй награды
    res2, _ = await svc.moderate(review.id, "approve")
    assert res2 is None
    await session.refresh(user)
    assert user.balance == 1.0


async def test_moderate_convert_creates_ticket(session):
    user = await create_user(session, tg_id=999000904, confirmed_ref_count=5)
    review = await ReviewRepo(session).create(user_id=user.id, rating=2, text=GOOD_TEXT)

    res, key = await ReviewService(session).moderate(review.id, "convert", "низкая оценка")
    assert key == "converted" and res is not None

    tickets = list((await session.execute(select(SupportTicket))).scalars().all())
    assert len(tickets) == 1 and tickets[0].review_id == review.id


# ---------- публикация в канал ----------

async def test_publish_review_channel_and_anonymity(session):
    user = await create_user(
        session, tg_id=999000905, username="nickname", confirmed_ref_count=5
    )
    repo = ReviewRepo(session)
    svc = ReviewService(session)
    bot = _FakeBot()

    public = await repo.create(user_id=user.id, rating=5, text=GOOD_TEXT, is_anonymous=False)
    # канал не настроен → ничего не уходит
    await svc.publish_review(bot, public)
    assert bot.sent == []

    await SettingsService(session).set("reviews_channel_id", "-100500")
    await svc.publish_review(bot, public)
    assert len(bot.sent) == 1
    chat_id, text = bot.sent[0]
    assert chat_id == -100500
    assert "@nickname" in text and GOOD_TEXT in text

    anon = await repo.create(user_id=user.id, rating=4, text=GOOD_TEXT, is_anonymous=True)
    await svc.publish_review(bot, anon)
    assert "Аноним" in bot.sent[1][1]
    assert "@nickname" not in bot.sent[1][1]


async def test_notify_user_approved(session):
    user = await create_user(session, tg_id=999000906, confirmed_ref_count=5)
    review = await ReviewRepo(session).create(user_id=user.id, rating=5, text=GOOD_TEXT)
    bot = _FakeBot()
    await ReviewService(session).notify_user_approved(bot, review, 1.0)
    assert bot.sent and bot.sent[0][0] == user.tg_id
    assert "+1.00⭐" in bot.sent[0][1]


# ---------- клавиатуры (регрессия: флоу был недостижим) ----------

def _cb_datas(markup) -> list[str]:
    return [b.callback_data for row in markup.inline_keyboard for b in row]


def test_review_keyboards_wired():
    assert "rev:start" in _cb_datas(kb_review_intro())
    rating = _cb_datas(kb_review_rating(3))
    assert "rev:star:1" in rating and "rev:rating_next" in rating and "rev:cancel" in rating
    assert _cb_datas(kb_review_text_step()) == ["rev:cancel"]
    anon = _cb_datas(kb_review_anonymity())
    assert "rev:anon_yes" in anon and "rev:anon_no" in anon


# ---------- маппинг анонимности (регрессия: инверсная логика) ----------

class _FakeCbMessage:
    async def edit_text(self, *a, **kw) -> None:
        pass


class _FakeCallback:
    def __init__(self, data: str) -> None:
        self.data = data
        self.message = _FakeCbMessage()

    async def answer(self, *a, **kw) -> None:
        pass


async def test_anonymity_mapping():
    for data, expected in (("rev:anon_yes", True), ("rev:anon_no", False)):
        state = FSMContext(
            storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=1, user_id=1)
        )
        await state.set_state(ReviewStates.anonymity)
        await state.update_data(rating=5, text="x" * 40)
        await cb_review_anonymity(_FakeCallback(data), state)
        stored = await state.get_data()
        assert stored["is_anonymous"] is expected
