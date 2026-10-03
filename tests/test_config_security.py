from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.config import Settings


BASE_SETTINGS = {
    "bot_token": "1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE",
    "owner_id": 1,
}
VALID_FERNET_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


@pytest.mark.parametrize(
    "fernet_key",
    [None, "not-a-fernet-key", f" {VALID_FERNET_KEY} ", "ключ"],
)
def test_production_requires_valid_fernet_key(monkeypatch, fernet_key: str | None) -> None:
    monkeypatch.delenv("FERNET_KEY", raising=False)
    kwargs = dict(BASE_SETTINGS)
    if fernet_key is not None:
        kwargs["fernet_key"] = fernet_key

    with pytest.raises(ValidationError, match="FERNET_KEY"):
        Settings(_env_file=None, env="production", **kwargs)


def test_production_accepts_valid_fernet_key(monkeypatch) -> None:
    monkeypatch.delenv("FERNET_KEY", raising=False)
    configured = Settings(
        _env_file=None,
        env="production",
        fernet_key=VALID_FERNET_KEY,
        **BASE_SETTINGS,
    )
    assert configured.fernet_key == VALID_FERNET_KEY


def test_test_environment_can_omit_fernet_key(monkeypatch) -> None:
    monkeypatch.delenv("FERNET_KEY", raising=False)
    configured = Settings(_env_file=None, env="test", **BASE_SETTINGS)
    assert configured.fernet_key is None
