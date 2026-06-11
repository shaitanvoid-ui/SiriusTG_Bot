from __future__ import annotations

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message, TelegramObject

from core.config import settings


class IsAdmin(Filter):
    """Пропускает только owner и admin'ов из настроек."""

    def __init__(self, owner_only: bool = False) -> None:
        self.owner_only = owner_only

    async def __call__(self, event: TelegramObject) -> bool:
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
        if user is None:
            return False
        if self.owner_only:
            return user.id == settings.owner_id
        return user.id in settings.all_admin_ids
