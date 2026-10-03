"""Доменная валидация настроек, изменяемых из админ-панели.

Парсинг типа сам по себе недостаточен: корректные JSON и числа могут сделать
бот неработоспособным (например, ``history.page_size = 0``). Здесь собраны
ограничения, которые защищают runtime и экономику.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from services.settings import SettingsService


_NON_NEGATIVE_KEYS = {
    "gifts.daily_budget_stars",
    "ref.reward",
    "ref.daily_limit",
    "ref.maturation_days",
    "withdraw.min_amount",
    "withdraw.min_confirmed_refs",
    "withdraw.per_day_limit",
    "click.base_reward",
    "click.daily_base_limit",
    "click.captcha_every_min",
    "click.captcha_every_max",
    "bonus.base",
    "wheel.free_per_day",
    "leaderboard.min_confirmed_refs",
    "partner.reward_per_passed_user",
    "partner.min_payout_stars",
    "partner.rub_per_star",
    "support.max_tickets_per_hour",
    "support.autoclose_days",
    "review.reward",
    "review.antispam_min_refs",
    "review.antispam_cooldown_days",
}

_POSITIVE_KEYS = {
    "gifts.poll_seconds", "gifts.lease_seconds", "gifts.max_attempts",
    "daily.reminder_batch_size",
    "subrecheck.interval_hours",
    "subrecheck.sample_size",
    "click.min_interval_ms",
    "tasks_recheck.interval_min",
    "tasks_recheck.sample_size",
    "promo.max_code_length",
    "wheel.cost",
    "leaderboard.display_size",
    "backup.interval_hours",
    "partner.max_links",
    "support.autoclose_check_hours",
    "support.min_text_length",
    "support.max_text_length",
    "history.page_size",
    "review.min_text_length",
    "review.max_text_length",
}

_MAX_BY_KEY: dict[str, float] = {
    "gifts.poll_seconds": 300, "gifts.lease_seconds": 3600, "gifts.max_attempts": 20, "gifts.daily_budget_stars": 1000000000,
    "subrecheck.interval_hours": 24 * 30,
    "subrecheck.sample_size": 100_000,
    "click.min_interval_ms": 86_400_000,
    "click.captcha_every_min": 100_000,
    "click.captcha_every_max": 100_000,
    "tasks_recheck.interval_min": 24 * 60,
    "tasks_recheck.sample_size": 100_000,
    "promo.max_code_length": 64,
    "wheel.free_per_day": 100,
    "leaderboard.display_size": 100,
    "backup.interval_hours": 24 * 30,
    "partner.max_links": 100,
    "support.max_tickets_per_hour": 100,
    "support.autoclose_check_hours": 24 * 30,
    "support.min_text_length": 4_096,
    "support.max_text_length": 4_096,
    "history.page_size": 50,
    # Отзыв публикуется одной HTML-карточкой в Telegram. 600 исходных
    # символов оставляют запас даже после HTML-экранирования спецсимволов.
    "review.min_text_length": 600,
    "review.max_text_length": 600,
}


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}: ожидалось число")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label}: число должно быть конечным")
    return number


def _validate_levels(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError("Конфигурация уровней должна быть непустым списком")
    previous_level = 0
    previous_refs = -1
    seen: set[int] = set()
    for index, row in enumerate(value, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"Уровень #{index}: ожидался JSON-объект")
        try:
            level = int(row["level"])
            refs = int(row["required_refs"])
            multiplier = float(row["click_mult"])
            daily_limit = int(row["click_daily_limit"])
            name = str(row["name"]).strip()
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"Уровень #{index}: заполнены не все обязательные поля") from None
        if level <= previous_level or level in seen:
            raise ValueError("Номера уровней должны быть уникальными и возрастать")
        if refs < 0 or refs < previous_refs:
            raise ValueError("Пороги рефералов должны быть неотрицательными и возрастать")
        if multiplier <= 0 or daily_limit <= 0 or not name:
            raise ValueError("У уровня нужны имя, положительный множитель и лимит")
        previous_level, previous_refs = level, refs
        seen.add(level)


def _validate_prizes(value: Any) -> None:
    if not isinstance(value, list) or not value or len(value) > 100:
        raise ValueError("Нужно указать от 1 до 100 секторов колеса")
    for index, row in enumerate(value, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"Сектор #{index}: ожидался JSON-объект")
        try:
            prize = _number(row["value"], f"Сектор #{index}")
            weight = _number(row["weight"], f"Вес сектора #{index}")
        except KeyError:
            raise ValueError(f"Сектор #{index}: нужны поля value и weight") from None
        if prize < 0 or weight <= 0:
            raise ValueError("Приз не может быть отрицательным, а вес должен быть больше нуля")


def _validate_achievements(value: Any) -> None:
    allowed_metrics = {"confirmed_refs", "clicks_total", "bonus_streak", "tasks_done"}
    if not isinstance(value, list) or not value or len(value) > 100:
        raise ValueError("Нужно указать от 1 до 100 достижений")
    codes: set[str] = set()
    for index, row in enumerate(value, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"Достижение #{index}: ожидался JSON-объект")
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        metric = str(row.get("metric", ""))
        try:
            threshold = _number(row.get("threshold"), f"Порог достижения #{index}")
            reward = _number(row.get("reward", 0), f"Награда достижения #{index}")
        except ValueError as exc:
            raise ValueError(str(exc)) from None
        if not code or not name or code in codes:
            raise ValueError("У достижений должны быть уникальные code и непустые name")
        if metric not in allowed_metrics:
            raise ValueError(f"Достижение #{index}: неизвестная метрика {metric!r}")
        if threshold <= 0 or reward < 0:
            raise ValueError("Порог должен быть положительным, награда — неотрицательной")
        codes.add(code)


def _validate_faq(value: Any) -> None:
    if not isinstance(value, list) or len(value) > 50:
        raise ValueError("FAQ должен быть списком максимум из 50 пунктов")
    for index, row in enumerate(value, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"FAQ #{index}: ожидался JSON-объект")
        question = str(row.get("q", "")).strip()
        answer = str(row.get("a", "")).strip()
        if not question or not answer:
            raise ValueError(f"FAQ #{index}: вопрос и ответ не могут быть пустыми")
        if len(question) > 200 or len(answer) > 3_500:
            raise ValueError(f"FAQ #{index}: текст превышает безопасную длину Telegram")


def validate_setting_value(key: str, value: Any) -> None:
    if key == "gifts.lease_seconds" and _number(value, key) < 120:
        raise ValueError("Lease очереди подарков должен быть не меньше 120 секунд")
    """Проверяет автономные ограничения одного значения."""
    if key == "daily.reminder_hour_msk" and not 10 <= _number(value, key) <= 21:
        raise ValueError("Напоминания разрешены с 10 до 21 часа по Москве")
    if key == "daily.reminder_batch_size" and _number(value, key) > 1000:
        raise ValueError("Максимум 1000 напоминаний за запуск")
    if key in _NON_NEGATIVE_KEYS and _number(value, key) < 0:
        raise ValueError("Значение не может быть отрицательным")
    if key in _POSITIVE_KEYS and _number(value, key) <= 0:
        raise ValueError("Значение должно быть больше нуля")
    if key in _MAX_BY_KEY and _number(value, key) > _MAX_BY_KEY[key]:
        raise ValueError(f"Значение слишком велико; максимум {_MAX_BY_KEY[key]:g}")
    if key == "partner.percent_sponsor_reward":
        number = _number(value, key)
        if not 0 <= number <= 100:
            raise ValueError("Процент партнёра должен быть от 0 до 100")
    if key == "digest.hour_msk":
        number = _number(value, key)
        if number != int(number) or not 0 <= number <= 23:
            raise ValueError("Час дайджеста должен быть целым числом от 0 до 23 МСК")
    if key in {"brand.name", "brand.tagline"}:
        if not str(value).strip() or len(str(value)) > 64:
            raise ValueError("Название должно содержать от 1 до 64 символов")
    if key == "channel.url":
        url = str(value).strip()
        if url and not url.startswith(("https://", "http://")):
            raise ValueError("Ссылка должна начинаться с https:// или http://")
    if key == "reviews_channel_id":
        raw = str(value).strip()
        if raw and not raw.lstrip("-").isdigit():
            raise ValueError("ID канала должен быть целым числом или пустой строкой")
    if key == "bonus.streak":
        if not isinstance(value, Mapping) or not value:
            raise ValueError("Лесенка бонусов должна быть непустым JSON-объектом")
        for day, reward in value.items():
            try:
                if int(day) <= 0 or _number(reward, "Награда streak") < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError("Дни streak должны быть положительными, награды — неотрицательными") from None
    elif key == "levels.config":
        _validate_levels(value)
    elif key == "wheel.prizes":
        _validate_prizes(value)
    elif key == "achievements.config":
        _validate_achievements(value)
    elif key == "leaderboard.weekly_rewards":
        if not isinstance(value, list) or not value or len(value) > 100:
            raise ValueError("Список наград должен содержать от 1 до 100 мест")
        if any(_number(v, "Награда топа") < 0 for v in value):
            raise ValueError("Награды топа не могут быть отрицательными")
    elif key == "support.faq":
        _validate_faq(value)


async def validate_setting_change(
    key: str, value: Any, settings: SettingsService
) -> str | None:
    """Возвращает человеко-читаемую ошибку либо ``None``."""
    try:
        validate_setting_value(key, value)

        async def candidate(other_key: str) -> Any:
            if other_key == key:
                return value
            return await settings.get(other_key)

        pairs = (
            ("click.captcha_every_min", "click.captcha_every_max", "Минимум мини-капчи не может быть больше максимума"),
            ("support.min_text_length", "support.max_text_length", "Минимальная длина обращения не может быть больше максимальной"),
            ("review.min_text_length", "review.max_text_length", "Минимальная длина отзыва не может быть больше максимальной"),
        )
        for low_key, high_key, message in pairs:
            if key not in {low_key, high_key}:
                continue
            low = _number(await candidate(low_key), low_key)
            high = _number(await candidate(high_key), high_key)
            if low > high:
                raise ValueError(message)

        if key in {"wheel.cost", "wheel.prizes"}:
            cost = _number(await candidate("wheel.cost"), "wheel.cost")
            prizes = await candidate("wheel.prizes")
            _validate_prizes(prizes)
            total_weight = sum(float(row["weight"]) for row in prizes)
            expected = sum(float(row["value"]) * float(row["weight"]) for row in prizes) / total_weight
            if expected >= cost:
                raise ValueError(
                    "Средний приз колеса должен быть меньше стоимости платного вращения"
                )
    except (TypeError, ValueError) as exc:
        return str(exc) or "Некорректное значение"
    return None


__all__ = ["validate_setting_change", "validate_setting_value"]
