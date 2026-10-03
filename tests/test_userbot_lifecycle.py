from __future__ import annotations

from types import SimpleNamespace

import pytest

import userbot.client as client_module
from userbot.client import SessionInUse, SessionProcessLock, account_matches


def test_session_lock_excludes_second_process_and_releases(tmp_path):
    first = SessionProcessLock(tmp_path)
    second = SessionProcessLock(tmp_path)
    first.acquire()
    try:
        with pytest.raises(SessionInUse):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()


def test_client_disables_hidden_payment_retries(monkeypatch):
    calls = {}

    def factory(*args, **kwargs):
        calls.update(kwargs)
        return object()

    monkeypatch.setattr(client_module, "TelegramClient", factory)
    client_module._build_client("")
    assert calls["request_retries"] == 0
    assert calls["flood_sleep_threshold"] == 0
    assert calls["auto_reconnect"] is False
    assert calls["raise_last_call_error"] is True


def test_sender_account_binds_selected_phone_id_and_human(monkeypatch):
    monkeypatch.setattr(client_module, "settings", SimpleNamespace(owner_id=999, userbot_account_id=1))
    assert account_matches(SimpleNamespace(id=1, phone="12345678901", bot=False), "+1 234 567 8901")
    assert not account_matches(SimpleNamespace(id=2, phone="12345678901", bot=False), "+12345678901")
    assert not account_matches(SimpleNamespace(id=1, phone="22345678901", bot=False), "+12345678901")
    assert not account_matches(SimpleNamespace(id=1, phone="12345678901", bot=True), "+12345678901")


def test_sender_can_be_separate_personal_account_on_first_login(monkeypatch):
    monkeypatch.setattr(client_module, "settings", SimpleNamespace(owner_id=999, userbot_account_id=None))
    assert account_matches(SimpleNamespace(id=1, phone="12345678901", bot=False), "+12345678901")
    assert not account_matches(SimpleNamespace(id=1, phone="22345678901", bot=False), "+12345678901")


async def test_concurrent_get_client_builds_one_connected_session(monkeypatch, tmp_path):
    import asyncio

    built = []

    class Client:
        connected = False

        def is_connected(self):
            return self.connected

        async def connect(self):
            await asyncio.sleep(0)
            self.connected = True

        async def is_user_authorized(self):
            return True

        async def get_me(self):
            return SimpleNamespace(id=1, phone="12345678901", bot=False)

        async def disconnect(self):
            self.connected = False

    def build(value):
        client = Client()
        built.append(client)
        return client

    async def load():
        return "test-only-opaque-value"

    monkeypatch.setattr(client_module, "settings", SimpleNamespace(
        owner_id=1, tg_api_id=1, tg_api_hash="dummy", userbot_phone="12345678901",
        database_url=f"sqlite+aiosqlite:///{tmp_path}/test.db",
    ))
    monkeypatch.setattr(client_module, "_client", None)
    monkeypatch.setattr(client_module, "_process_lock", None)
    monkeypatch.setattr(client_module, "_build_client", build)
    monkeypatch.setattr(client_module, "_load_session_str", load)
    first, second = await asyncio.gather(client_module.get_client(), client_module.get_client())
    assert first is second and len(built) == 1
    await client_module.disconnect()
    assert client_module._process_lock is None


def test_hidden_input_never_falls_back_to_visible_input(monkeypatch):
    import getpass
    import warnings
    import userbot.login as login

    def unsafe(prompt):
        warnings.warn("cannot hide input", getpass.GetPassWarning)
        raise AssertionError("visible fallback reached")

    monkeypatch.setattr(login.getpass, "getpass", unsafe)
    with pytest.raises(getpass.GetPassWarning):
        login._hidden_input("secret: ")
