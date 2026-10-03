from unittest.mock import AsyncMock

from aiogram.types import CallbackQuery, User
from aiogram import Bot

from bot.middlewares.navigation import NavigationStateMiddleware
from bot.middlewares.callback_access import CallbackAccessMiddleware
from locales.ru import T


async def test_opening_another_section_clears_pending_dialogue():
    callback = CallbackQuery(id="test", from_user=User(id=1,is_bot=False,first_name="A"),
                             chat_instance="test", data="sec:earn")
    state = AsyncMock()
    data = {"state":state,"raw_state":"PromoStates:waiting_code"}
    handler = AsyncMock(return_value="ready")
    assert await NavigationStateMiddleware()(handler, callback, data) == "ready"
    state.clear.assert_awaited_once()
    assert data["raw_state"] is None


async def test_action_callbacks_keep_their_confirmation_state():
    callback = CallbackQuery(id="test", from_user=User(id=1,is_bot=False,first_name="A"),
                             chat_instance="test", data="whl:paid:nonce")
    state = AsyncMock()
    await NavigationStateMiddleware()(AsyncMock(), callback, {"state":state})
    state.clear.assert_not_called()


async def test_inaccessible_callback_never_reaches_economy(monkeypatch):
    bot = Bot("1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE")
    request = AsyncMock(return_value=True)
    monkeypatch.setattr(bot.session, "make_request", request)
    callback = CallbackQuery(id="test", from_user=User(id=1,is_bot=False,first_name="A"),
                             chat_instance="test", inline_message_id="old", data="whl:spin:paid").as_(bot)
    handler = AsyncMock()
    await CallbackAccessMiddleware()(handler, callback, {})
    handler.assert_not_called()
    assert request.call_args.args[1].text == T.stale_screen_alert
