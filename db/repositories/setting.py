from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import utcnow
from db.models import Setting, SettingType
from db.repositories.base import BaseRepo


def _cast(value: str, type_: str) -> Any:
    if type_ == SettingType.INT.value:
        return int(value)
    if type_ == SettingType.FLOAT.value:
        return float(value)
    if type_ == SettingType.BOOL.value:
        return value.lower() in ("1", "true", "yes", "y", "on")
    if type_ == SettingType.JSON.value:
        return json.loads(value)
    return value


def _serialize(value: Any) -> tuple[str, str]:
    if isinstance(value, bool):
        return ("1" if value else "0"), SettingType.BOOL.value
    if isinstance(value, int):
        return str(value), SettingType.INT.value
    if isinstance(value, float):
        return str(value), SettingType.FLOAT.value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False), SettingType.JSON.value
    return str(value), SettingType.STR.value


class SettingRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_raw(self, key: str) -> Setting | None:
        res = await self.session.execute(select(Setting).where(Setting.key == key))
        return res.scalar_one_or_none()

    async def get(self, key: str, default: Any = None) -> Any:
        row = await self.get_raw(key)
        if row is None:
            return default
        try:
            return _cast(row.value, row.type)
        except Exception:
            return row.value

    async def set(self, key: str, value: Any, description: str | None = None) -> None:
        raw, type_ = _serialize(value)
        stmt = sqlite_insert(Setting).values(
            key=key,
            value=raw,
            type=type_,
            description=description,
            updated_at=utcnow(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["key"],
            set_={"value": raw, "type": type_, "updated_at": utcnow()},
        )
        await self.session.execute(stmt)

    async def all(self) -> list[Setting]:
        res = await self.session.execute(select(Setting).order_by(Setting.key))
        return list(res.scalars().all())

    async def delete(self, key: str) -> bool:
        """Физическое удаление устаревшего ключа (settings — не пользовательские данные)."""
        res = await self.session.execute(sa_delete(Setting).where(Setting.key == key))
        return bool(res.rowcount)
