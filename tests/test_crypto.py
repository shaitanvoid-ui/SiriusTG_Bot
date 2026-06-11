"""Fernet-обёртка: roundtrip + защита от повреждения."""

from __future__ import annotations

import pytest

from core.crypto import CryptoError, decrypt, encrypt


def test_roundtrip():
    secret = "1BVtsOH...string-session-payload...=="
    token = encrypt(secret)
    assert token != secret
    assert decrypt(token) == secret


def test_tampered_token_raises():
    token = encrypt("hello")
    i = len(token) // 2
    flipped = "A" if token[i] != "A" else "B"
    tampered = token[:i] + flipped + token[i + 1:]
    with pytest.raises(CryptoError):
        decrypt(tampered)


def test_garbage_raises():
    with pytest.raises(CryptoError):
        decrypt("not-a-valid-fernet-token")
