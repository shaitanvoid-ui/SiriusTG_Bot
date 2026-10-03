"""Регрессии критических onboarding/subscription-потоков."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import bot.handlers.captcha as captcha_handler
import userbot.bio_reader as bio_reader
import userbot.client as userbot_client
from bot.handlers.admin.channel import msg_set_channel
from bot.handlers.flow import show_captcha
from db.repositories.sponsor import SponsorRepo
from services.settings import SettingsService
from tests.helpers import create_sponsor
from userbot.bio_reader import bio_contains_ref
from utils.captcha import CaptchaTask


class _State:
    def __init__(self, data: dict | None = None) -> None:
        self.data = dict(data or {})
        self.state = None
        self.cleared = False

    async def get_data(self) -> dict:
        return dict(self.data)

    async def set_state(self, state) -> None:
        self.state = state

    async def update_data(self, **kwargs) -> None:
        self.data.update(kwargs)

    async def clear(self) -> None:
        self.data.clear()
        self.state = None
        self.cleared = True


class _Message:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.answers: list[tuple[str, dict]] = []
        self.photos: list[dict] = []
        self.deleted = False

    async def answer(self, text: str, **kwargs):
        self.answers.append((text, kwargs))
        return self

    async def answer_photo(self, **kwargs) -> None:
        self.photos.append(kwargs)

    async def delete(self) -> None:
        self.deleted = True


async def test_show_captcha_preserves_remaining_attempts(monkeypatch):
    task = CaptchaTask(
        answer="🍎",
        on_image=("🍎", "🍌", "🍇", "🍉", "🍒", "🍓"),
        choices=("🍎", "🚗", "⚽", "🐶"),
        token="fixed-token",
    )
    monkeypatch.setattr("bot.handlers.flow.generate_task", lambda: task)
    monkeypatch.setattr("bot.handlers.flow.render_captcha_image", lambda _: b"png")

    state = _State()
    message = _Message()
    await show_captcha(message, state, total_steps=3, attempts_left=2)

    assert state.data["captcha_attempts_left"] == 2
    assert state.data["captcha_token"] == "fixed-token"
    assert len(message.photos) == 1


async def test_wrong_captcha_passes_decremented_attempts_to_next_task(
    session, monkeypatch
):
    state = _State(
        {
            "captcha_token": "token",
            "captcha_answer": "🍎",
            "captcha_attempts_left": 3,
            "total_steps": 3,
        }
    )
    message = _Message()
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=1001),
        data="cap:token:🍌",
        message=message,
        answers=[],
    )

    async def answer(text=None, **kwargs) -> None:
        callback.answers.append((text, kwargs))

    callback.answer = answer
    shown: dict[str, int] = {}

    async def fake_show(message, state, *, total_steps, attempts_left):  # noqa: ARG001
        shown["attempts_left"] = attempts_left

    monkeypatch.setattr(captcha_handler, "show_captcha", fake_show)
    await captcha_handler.cb_captcha_choice(callback, state, session)

    assert shown["attempts_left"] == 2
    assert message.deleted is True


class _ChannelBot:
    id = 77

    async def get_chat(self, chat_ref: str):
        assert chat_ref == "@NewChannel"
        return SimpleNamespace(id=-100200, title="Новый канал", username="NewChannel")

    async def get_chat_member(self, chat_id: int, user_id: int):
        assert (chat_id, user_id) == (-100200, self.id)
        return SimpleNamespace(status="administrator")


async def test_replacing_project_channel_deactivates_previous_sponsor(session):
    old = await create_sponsor(
        session,
        title="Старый канал",
        username="OldChannel",
        chat_id=-100100,
        is_required=True,
        is_active=True,
    )
    unrelated = await create_sponsor(
        session,
        title="Другой обязательный",
        username="RequiredChannel",
        chat_id=-100300,
        is_required=True,
        is_active=True,
    )
    await SettingsService(session).set("channel.url", "https://t.me/OldChannel")

    message = _Message("@NewChannel")
    state = _State()
    await msg_set_channel(message, state, session, _ChannelBot())

    await session.refresh(old)
    await session.refresh(unrelated)
    new = await SponsorRepo(session).get_by_username("newchannel")
    assert old.is_active is False
    assert old.is_required is False
    assert unrelated.is_active is True
    assert unrelated.is_required is True
    assert new is not None and new.is_active is True and new.is_required is True
    assert await SettingsService(session).get_str("channel.url", "") == (
        "https://t.me/NewChannel"
    )
    assert state.cleared is True


@pytest.mark.parametrize(
    "about",
    [
        "https://t.me/SiriusBot?start=r123",
        "@SiriusBot r123",
        "Мой бот: siriusbot; код: R123!",
    ],
)
def test_bio_referral_accepts_exact_payload(about: str):
    assert bio_contains_ref(about, payload="r123", bot_username="SiriusBot") is True


@pytest.mark.parametrize(
    "about",
    [
        "https://t.me/SiriusBot?start=r1234",
        "https://t.me/SiriusBot?start=r123abc",
        "https://t.me/SiriusBot?start=r123-extra",
        "https://t.me/OtherBot?start=r123",
        "@SiriusBot r123_",
        "@SiriusBot кодr123",
        "@FakeSiriusBot r123",
        "@SiriusBotFake r123",
        "ФSiriusBot r123",
        "mail@SiriusBot r123",
    ],
)
def test_bio_referral_rejects_payload_and_bot_substrings(about: str):
    assert bio_contains_ref(about, payload="r123", bot_username="SiriusBot") is False


async def test_bio_reader_falls_back_from_username_to_tg_id(monkeypatch):
    class Client:
        def __init__(self) -> None:
            self.candidates = []

        async def get_entity(self, candidate):
            self.candidates.append(candidate)
            if isinstance(candidate, str):
                raise ValueError("username is stale")
            return SimpleNamespace(id=candidate)

        async def __call__(self, request):  # noqa: ARG002
            return SimpleNamespace(full_user=SimpleNamespace(about="bio"))

    client = Client()

    async def get_client():
        return client

    async def no_throttle() -> None:
        return None

    monkeypatch.setattr(bio_reader, "get_client", get_client)
    monkeypatch.setattr(bio_reader, "_throttle", no_throttle)

    about, available = await bio_reader.fetch_about(tg_id=123, username="old_name")

    assert (about, available) == ("bio", True)
    assert client.candidates == ["@old_name", 123]


async def test_bio_reader_does_not_hide_programming_errors(monkeypatch):
    class Client:
        async def get_entity(self, candidate):  # noqa: ARG002
            raise RuntimeError("unexpected bug")

    async def get_client():
        return Client()

    async def no_throttle() -> None:
        return None

    monkeypatch.setattr(bio_reader, "get_client", get_client)
    monkeypatch.setattr(bio_reader, "_throttle", no_throttle)

    with pytest.raises(RuntimeError, match="unexpected bug"):
        await bio_reader.fetch_about(tg_id=123, username="name")


async def test_userbot_disconnect_softly_handles_network_error(monkeypatch):
    class Client:
        async def disconnect(self) -> None:
            raise OSError("network down")

    monkeypatch.setattr(userbot_client, "_client", Client())

    await userbot_client.disconnect()

    assert userbot_client._client is None
