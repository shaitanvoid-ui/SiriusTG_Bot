"""Этап 8 (доделка) + Этап 9: дашборд, юзеры, экономика, рассылка,
инструкция, стоп-слова."""

from __future__ import annotations

from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from db.repositories.instruction import InstructionRepo
from db.repositories.stop_word import StopWordRepo
from db.repositories.user import UserRepo
from bot.handlers.admin.economy import eco_groups, parse_value
from bot.handlers.admin.users import msg_balance_delta
from bot.states.admin import UserAdminStates
from locales.ru import T
from services.admin_stats import AdminStatsService
from services.broadcast import run_broadcast
from services.settings import DEFAULTS
from tests.helpers import create_user


# ---------- дашборд ----------

async def test_dashboard_empty(session):
    stats = await AdminStatsService(session).dashboard()
    assert stats.users_total == 0
    assert stats.balance_total == 0.0
    assert stats.clicks_today == 0


async def test_dashboard_counts_users_and_balances(session):
    await create_user(session, tg_id=999000801, balance=5.0)
    u2 = await create_user(session, tg_id=999000802, balance=2.5)
    u2.debt = 1.0
    u2.is_banned = True
    await session.flush()

    stats = await AdminStatsService(session).dashboard()
    assert stats.users_total == 2
    assert stats.users_banned == 1
    assert stats.balance_total == 7.5
    assert stats.debt_total == 1.0
    assert stats.users_new_today == 2


# ---------- юзеры: репо-методы ----------

async def test_user_admin_actions(session):
    user = await create_user(session, tg_id=999000803, username="TestNick")
    repo = UserRepo(session)

    found = await repo.get_by_username("testnick")
    assert found is not None and found.id == user.id

    await repo.set_banned(user.id, True)
    await session.refresh(user)
    assert user.is_banned is True

    await repo.set_shadow_banned(user.id, True)
    await session.refresh(user)
    assert user.is_shadow_banned is True

    # забаненный не попадает в рассылку
    await create_user(session, tg_id=999000804)
    ids = await repo.list_broadcast_tg_ids()
    assert 999000804 in ids
    assert 999000803 not in ids


# ---------- юзеры: баланс ± через хендлер ----------
# Регрессия: session.refresh после add_balance отбрасывал начисление
# («прибавляю звёзды — не прибавляются»).

class _FakeSent:
    async def edit_text(self, *a, **kw) -> None:
        pass


class _FakeAdminMessage:
    def __init__(self, text: str) -> None:
        self.text = text

    async def answer(self, *a, **kw) -> "_FakeSent":
        return _FakeSent()


def _admin_state() -> FSMContext:
    return FSMContext(
        storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=1, user_id=1)
    )


async def test_admin_balance_delta_adds_stars(session):
    user = await create_user(session, tg_id=999000805, balance=1.0)
    state = _admin_state()
    await state.set_state(UserAdminStates.waiting_balance_delta)
    await state.update_data(target_user_id=user.id)

    await msg_balance_delta(_FakeAdminMessage("5"), state, session)
    await session.commit()

    fresh = await UserRepo(session).get_by_id(user.id)
    assert fresh.balance == 6.0


async def test_admin_balance_delta_subtract_goes_to_debt(session):
    user = await create_user(session, tg_id=999000806, balance=2.0)
    state = _admin_state()
    await state.set_state(UserAdminStates.waiting_balance_delta)
    await state.update_data(target_user_id=user.id)

    await msg_balance_delta(_FakeAdminMessage("-5"), state, session)
    await session.commit()

    fresh = await UserRepo(session).get_by_id(user.id)
    assert fresh.balance == 0.0
    assert fresh.debt == 3.0


# ---------- экономика ----------

def test_eco_groups_cover_all_defaults():
    keys_in_groups = [k for keys in eco_groups().values() for k in keys]
    assert sorted(keys_in_groups) == sorted(DEFAULTS.keys())


def test_parse_value_types():
    assert parse_value("да", True) == (True, True)
    assert parse_value("off", True) == (False, True)
    assert parse_value("мимо", True) == (None, False)
    assert parse_value("42", 7) == (42, True)
    assert parse_value("4.5", 7) == (None, False)
    assert parse_value("3,5", 1.0) == (3.5, True)
    assert parse_value('{"1": 0.5}', {"1": 0.1}) == ({"1": 0.5}, True)
    assert parse_value("[1, 2]", {"a": 1}) == (None, False)  # тип не совпал
    assert parse_value("hello", "world") == ("hello", True)


# ---------- рассылка ----------

class _FakeBot:
    def __init__(self, fail_ids: set[int]) -> None:
        self.fail_ids = fail_ids
        self.sent: list[int] = []

    async def send_message(self, tg_id: int, text: str) -> None:
        if tg_id in self.fail_ids:
            raise TelegramAPIError(method=None, message="forbidden")  # type: ignore[arg-type]
        self.sent.append(tg_id)


async def test_run_broadcast_counts_and_progress():
    bot = _FakeBot(fail_ids={2, 4})
    progress: list[tuple[int, int]] = []

    async def cb(done: int, total: int) -> None:
        progress.append((done, total))

    result = await run_broadcast(
        bot, [1, 2, 3, 4, 5], "hi", delay_sec=0, report_every=2, progress_cb=cb
    )
    assert result.total == 5
    assert result.sent == 3
    assert result.failed == 2
    assert bot.sent == [1, 3, 5]
    assert progress[-1] == (5, 5)


# ---------- инструкция: CRUD ----------

async def test_instruction_crud(session):
    repo = InstructionRepo(session)
    page = await repo.create(title="Тест", body="Текст", sort_order=1)
    assert await repo.count() >= 1

    await repo.update(page.id, title="Новый", body=None)
    fresh = await repo.get_by_id(page.id)
    assert fresh.title == "Новый" and fresh.body == "Текст"

    assert await repo.delete(page.id) is True
    active = await repo.get_active()
    assert all(p.id != page.id for p in active)  # soft-delete


# ---------- стоп-слова ----------

async def test_stop_words_bulk_and_remove(session):
    repo = StopWordRepo(session)
    added = await repo.add_bulk(["Скам", "скам", "обман"])
    assert added == 2  # дубль не добавился
    assert set(await repo.get_words()) >= {"скам", "обман"}
    assert await repo.remove("скам") is True
    assert await repo.remove("скам") is False


# ---------- локали ----------

def test_admin_locales_present():
    assert "{users_total}" in T.admin_dash
    assert "{count}" in T.admin_bc_intro
    assert "{key}" in T.admin_eco_edit_prompt
    assert "{title}" in T.admin_channel_set
