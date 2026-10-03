from __future__ import annotations

import pytest

from services.settings import DEFAULTS, SettingsService
from services.settings_validation import validate_setting_change, validate_setting_value


def test_all_default_settings_are_domain_valid() -> None:
    for key, (value, _) in DEFAULTS.items():
        validate_setting_value(key, value)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("history.page_size", 0),
        ("partner.percent_sponsor_reward", 101.0),
        ("digest.hour_msk", 24),
        ("wheel.free_per_day", -1),
        ("support.max_text_length", 0),
        ("reviews_channel_id", "not-a-chat"),
    ],
)
def test_rejects_dangerous_scalar_values(key: str, value) -> None:
    with pytest.raises(ValueError):
        validate_setting_value(key, value)


def test_rejects_invalid_structured_values() -> None:
    with pytest.raises(ValueError):
        validate_setting_value("wheel.prizes", [{"value": 1, "weight": 0}])
    with pytest.raises(ValueError):
        validate_setting_value(
            "levels.config",
            [
                {
                    "level": 1,
                    "name": "A",
                    "required_refs": 10,
                    "click_mult": 1,
                    "click_daily_limit": 10,
                },
                {
                    "level": 2,
                    "name": "B",
                    "required_refs": 5,
                    "click_mult": 1,
                    "click_daily_limit": 10,
                },
            ],
        )


async def test_cross_field_validation(session) -> None:
    svc = SettingsService(session)
    assert await validate_setting_change("review.min_text_length", 999, svc)
    assert await validate_setting_change("click.captcha_every_min", 999, svc)
    assert await validate_setting_change(
        "wheel.prizes", [{"value": 10.0, "weight": 1}], svc
    )
    assert await validate_setting_change("history.page_size", 10, svc) is None
