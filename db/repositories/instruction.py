"""Репозиторий страниц инструкции."""
from __future__ import annotations

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instruction
from db.repositories.base import BaseRepo


class InstructionRepo(BaseRepo):
    async def get_active(self) -> list[Instruction]:
        result = await self.session.execute(
            select(Instruction)
            .where(Instruction.is_active == True)
            .order_by(Instruction.sort_order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: int) -> Instruction | None:
        result = await self.session.execute(
            select(Instruction).where(Instruction.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, title: str, body: str, sort_order: int = 0) -> Instruction:
        inst = Instruction(title=title, body=body, sort_order=sort_order)
        self.session.add(inst)
        await self.session.flush()
        return inst

    async def update(self, id: int, title: str | None, body: str | None) -> Instruction | None:
        inst = await self.get_by_id(id)
        if not inst:
            return None
        if title is not None:
            inst.title = title
        if body is not None:
            inst.body = body
        await self.session.flush()
        return inst

    async def delete(self, id: int) -> bool:
        inst = await self.get_by_id(id)
        if not inst:
            return False
        inst.is_active = False
        await self.session.flush()
        return True

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Instruction).where(Instruction.is_active == True)
        )
        return result.scalar_one()