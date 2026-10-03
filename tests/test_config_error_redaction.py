"""A failed configuration must not dump credentials into startup stderr."""
import pytest
from pydantic import ValidationError
from core.config import Settings


def test_production_configuration_error_hides_sensitive_input():
    fake_token = "1234567890:REDACTION_TEST_ONLY"
    fake_key = "INVALID_TEST_PRIVATE_KEY"
    with pytest.raises(ValidationError) as error:
        Settings(env="production", bot_token=fake_token, owner_id=1, fernet_key=fake_key)
    message = str(error.value)
    assert "FERNET_KEY" in message
    assert fake_token not in message and fake_key not in message
