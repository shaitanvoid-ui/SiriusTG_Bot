"""Преференции уведомлений (Этап 11).

Юзер выбирает в профиле, какие категории DM получать. Преференции живут в
User.notify_prefs (JSON-словарь категория→bool); NULL = всё включено.

Сервисные сообщения (потеря доступа, ответы поддержки) преференциями
НЕ гасятся — они отправляются всегда.
"""

from __future__ import annotations

import json

from db.models import User
from locales.ru import T

# код категории → (эмодзи, название, описание для экрана настроек)
CATEGORIES: dict[str, tuple[str, str, str]] = {
    "refs": ("👥", "Рефералы", "Награды за друзей и отвалы"),
    "tasks": ("🎯", "Задания", "Списания при отписке от каналов"),
    "rewards": ("🏆", "Награды", "Топ недели, отзывы, выплаты"),
    "daily": ("☀", T.daily_notification_name, T.daily_notification_hint),
}


class NotificationService:
    """Чтение/переключение преференций. Работает с уже загруженным User."""

    @staticmethod
    def prefs_of(user: User) -> dict[str, bool]:
        prefs = {code: code != "daily" for code in CATEGORIES}
        raw = user.notify_prefs
        if not raw:
            return prefs
        try:
            stored = json.loads(raw)
        except (TypeError, ValueError):
            return prefs
        if isinstance(stored, dict):
            for code in CATEGORIES:
                if isinstance(stored.get(code), bool):
                    prefs[code] = stored[code]
        return prefs

    @classmethod
    def is_enabled(cls, user: User, category: str) -> bool:
        if category not in CATEGORIES:
            return True
        return cls.prefs_of(user).get(category, True)

    @classmethod
    def toggle(cls, user: User, category: str) -> dict[str, bool]:
        """Инвертирует категорию и сохраняет в ORM-объект. Возвращает новые prefs."""
        prefs = cls.prefs_of(user)
        if category in prefs:
            prefs[category] = not prefs[category]
            user.notify_prefs = json.dumps(prefs)
        return prefs
