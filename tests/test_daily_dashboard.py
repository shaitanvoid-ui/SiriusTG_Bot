from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText

from sqlalchemy import func, select

from bot.handlers.menu import _build_caption
from bot.keyboards.daily import kb_daily
from db.models import ClickerDay, UserTaskCompletion
from services.dashboard import DashboardService
from services.settings import SettingsService
from tests.helpers import create_sponsor, create_user
from utils.tz import today_msk


async def test_dashboard_reads_availability_without_creating_clicker_rows(session) -> None:
    user = await create_user(session, tg_id=777101)
    await SettingsService(session).set("bonus.bio_required", False)
    view = await DashboardService(session, SettingsService(session)).get_view(user)
    assert view.next_action.callback == "bns:open"
    assert view.level.name and view.next_reset.hour == 0
    assert view.next_reset.date() == today_msk() + timedelta(days=1)
    count = await session.scalar(select(func.count(ClickerDay.id)))
    assert count == 0


async def test_claimed_bonus_is_not_offered_as_next_action(session) -> None:
    user = await create_user(session, tg_id=777102, last_bonus_date=today_msk(), bonus_streak=7)
    view = await DashboardService(session, SettingsService(session)).get_view(user)
    assert view.actions[0].complete
    assert view.next_action.callback == "whl:open"
    callbacks = [button.callback_data for row in kb_daily(view.actions).inline_keyboard for button in row]
    assert "bns:open" not in callbacks
    assert "day:open" in callbacks and "nav:menu" in callbacks


async def test_disabled_and_completed_tasks_do_not_appear_as_new(session) -> None:
    user = await create_user(session, tg_id=777103)
    sponsor = await create_sponsor(session, title="Task", is_required=False, reward=2, username="task_channel")
    svc = DashboardService(session, SettingsService(session))
    view = await svc.get_view(user)
    assert any(action.callback == "tsk:list" for action in view.actions)
    session.add(UserTaskCompletion(user_id=user.id, sponsor_id=sponsor.id, reward=2))
    await session.flush()
    view = await svc.get_view(user)
    assert not any(action.callback == "tsk:list" for action in view.actions)
    await svc.settings.set("wheel.enabled", False)
    view = await svc.get_view(user)
    assert not any(action.callback == "whl:open" for action in view.actions)


async def test_home_is_personal_escaped_and_has_next_action(session) -> None:
    user = await create_user(session, tg_id=777104, first_name='<script>"&')
    await SettingsService(session).set("bonus.bio_required", False)
    text, keyboard = await _build_caption(session, user)
    assert "&lt;script&gt;" in text and "<script>" not in text
    assert "Следующий шаг" in text
    assert keyboard.inline_keyboard[0][0].callback_data == "gift:open"
    assert keyboard.inline_keyboard[0][0].style == "primary"
    next_button = next(button for row in keyboard.inline_keyboard for button in row
                       if button.callback_data == "bns:open")
    assert next_button.style is None


async def test_refreshing_identical_daily_screen_is_harmless(session) -> None:
    from bot.handlers.daily import cb_open
    user = await create_user(session, tg_id=777105)
    callback = SimpleNamespace(answer=AsyncMock(), message=SimpleNamespace(edit_text=AsyncMock(
        side_effect=TelegramBadRequest(method=EditMessageText(text="same"), message="message is not modified"),
    )))
    state = AsyncMock()
    await cb_open(callback, session, user, state)
    callback.answer.assert_awaited_once()
    state.clear.assert_awaited_once()
