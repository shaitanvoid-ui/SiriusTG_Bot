from __future__ import annotations

from aiogram.types import User as TgUser

from core.logger import get_logger
from db.models import User
from db.repositories.user import UserRepo


log = get_logger(__name__)


class UserService:
    def __init__(self, repo: UserRepo) -> None:
        self.repo = repo

    async def upsert_from_tg(
        self,
        tg_user: TgUser,
        *,
        referrer_tg_id: int | None = None,
    ) -> tuple[User, bool]:
        user, created = await self.repo.upsert_from_tg(
            tg_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            language_code=tg_user.language_code,
            is_premium=bool(getattr(tg_user, "is_premium", False)),
            referrer_tg_id=referrer_tg_id,
        )
        if created:
            log.info("user_created", tg_id=tg_user.id, username=tg_user.username)
        return user, created
