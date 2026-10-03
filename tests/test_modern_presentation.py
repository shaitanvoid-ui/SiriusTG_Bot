"""Native Telegram contracts and failure behavior, without external API calls."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.methods import EditMessageText, SendMessage, SendRichMessage

from bot.keyboards.bonus import kb_bonus
from bot.keyboards.clicker import kb_clicker
from bot.keyboards.referral import kb_referral
from bot.keyboards.main_menu import kb_main_menu
from bot.middlewares.presentation import PresentationMiddleware
from locales.ru import T
from utils.rich import is_card, render_rich_html
from utils.telegram import ignore_unchanged


def _bot() -> Bot:
    return Bot("1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE", default=DefaultBotProperties(parse_mode="HTML"))


def _method(**kwargs):
    return SendMessage(chat_id=42, text=T.support_home, reply_markup=kb_bonus(can_claim=True), **kwargs)


async def test_rich_send_preserves_delivery_and_reply_routing() -> None:
    calls = []
    async def request(bot, method):
        calls.append(method)
        return "sent"
    source = _method(message_thread_id=7, disable_notification=True, protect_content=True)
    assert await PresentationMiddleware()(request, _bot(), source) == "sent"
    outgoing = calls[0]
    assert isinstance(outgoing, SendRichMessage)
    assert outgoing.chat_id == 42 and outgoing.message_thread_id == 7
    assert outgoing.disable_notification is True and outgoing.protect_content is True
    assert outgoing.reply_markup == source.reply_markup
    assert "<h2>" in outgoing.rich_message.html
    SendRichMessage.model_validate(outgoing.model_dump())


async def test_rich_edit_validates_native_model_and_has_no_text_conflict() -> None:
    request = AsyncMock(return_value=True)
    source = EditMessageText(chat_id=42, message_id=7, text=T.support_home, reply_markup=kb_bonus(can_claim=True))
    await PresentationMiddleware()(request, _bot(), source)
    outgoing = request.call_args.args[1]
    assert outgoing.text is None and outgoing.parse_mode is None
    assert outgoing.rich_message.html
    assert outgoing.message_id == 7
    EditMessageText.model_validate(outgoing.model_dump())
    assert source.text == T.support_home  # caller's original remains available for fallback


@pytest.mark.parametrize("kwargs", [{"chat_id": -42}, {"parse_mode": "MarkdownV2"}, {"reply_markup": None}])
async def test_non_ui_or_channel_messages_are_not_rewritten(kwargs) -> None:
    values = dict(chat_id=42, text=T.support_home, reply_markup=kb_bonus(can_claim=True))
    values.update(kwargs)
    method = SendMessage(**values)
    request = AsyncMock(return_value=True)
    await PresentationMiddleware()(request, _bot(), method)
    assert request.call_args.args[1] is method


async def test_unknown_rich_method_falls_back_once_then_uses_html() -> None:
    calls = []
    async def request(bot, method):
        calls.append(method)
        if isinstance(method, SendRichMessage):
            raise TelegramBadRequest(method=method, message="Bad Request: unknown method sendRichMessage")
        return True
    middleware = PresentationMiddleware()
    method = _method()
    await middleware(request, _bot(), method)
    await middleware(request, _bot(), method)
    assert [type(item) for item in calls] == [SendRichMessage, SendMessage, SendMessage]


@pytest.mark.parametrize("error", [TelegramBadRequest, TelegramNetworkError])
async def test_unrelated_or_ambiguous_failures_are_never_retried(error) -> None:
    request = AsyncMock(side_effect=error(method=_method(), message="chat not found"))
    with pytest.raises(error):
        await PresentationMiddleware()(request, _bot(), _method())
    assert request.await_count == 1  # no duplicate sends on ambiguous network errors


def test_native_details_tables_and_preformatted_blocks_are_separate() -> None:
    text = '✦ <b>Карточка</b>\n──────────────\n╭  Баланс  <b>2⭐</b>\n╰  Серия  <b>3 дня</b>\n\n<blockquote expandable><b>Условия</b>\nБез скрытых списаний.</blockquote>\n<pre>один\nдва</pre>'
    rich = render_rich_html(text)
    assert is_card(text)
    assert '<table><tr><td>Баланс</td><td><b>2⭐</b></td>' in rich
    assert '<details><summary>Условия</summary>' in rich
    assert '<pre>один\nдва</pre>' in rich
    assert '<p><pre>' not in rich and '<p><details>' not in rich


def test_native_copy_button_and_action_hierarchy() -> None:
    link = "https://t.me/sirius_bot?start=r42"
    markup = kb_referral(share_url="https://t.me/share/url?url=test", invite_link=link)
    assert markup.inline_keyboard[0][0].copy_text.text == link
    assert kb_bonus(can_claim=True).inline_keyboard[0][0].style == "success"
    assert kb_bonus(can_claim=False).inline_keyboard[0][0].style is None
    assert kb_clicker(can_click=True, cooldown_ms_left=60_000).inline_keyboard[0][0].style is None


def test_only_identical_edits_are_ignored() -> None:
    with ignore_unchanged():
        raise TelegramBadRequest(method=_method(), message="Bad Request: message is not modified")
    with pytest.raises(TelegramBadRequest), ignore_unchanged():
        raise TelegramBadRequest(method=_method(), message="Bad Request: can't parse entities")


async def test_startup_never_sends_notifications() -> None:
    import main
    from core.health import set_runtime_ready
    bot = AsyncMock()
    try:
        await main._on_startup(bot)
        bot.get_me.assert_awaited_once()
        bot.send_message.assert_not_called()
        bot.send_rich_message.assert_not_called()
        assert [call[0] for call in bot.mock_calls] == ["get_me"]
    finally:
        set_runtime_ready(False)


async def test_home_rich_message_contains_no_images_or_media() -> None:
    request = AsyncMock(return_value=True)
    source = SendMessage(chat_id=42, text=T.support_home, reply_markup=kb_main_menu())
    await PresentationMiddleware()(request, _bot(), source)
    outgoing = request.call_args.args[1]
    assert isinstance(outgoing, SendRichMessage)
    assert outgoing.rich_message.media is None
    assert "<img" not in outgoing.rich_message.html
