from __future__ import annotations


class BotError(Exception):
    """Базовое исключение приложения."""


class ConfigError(BotError):
    """Ошибка конфигурации."""


class ServiceError(BotError):
    """Ошибка слоя сервисов / бизнес-логики."""


class RepositoryError(BotError):
    """Ошибка слоя репозиториев / БД."""


class UserError(BotError):
    """Ошибка, которую нужно показать пользователю."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class AntifraudBlock(BotError):
    """Действие отклонено антифродом."""


class UserbotError(BotError):
    """Ошибка userbot (Telethon)."""
