"""Репозиторий стоп-слов."""
from __future__ import annotations

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import StopWord
from db.repositories.base import BaseRepo


class StopWordRepo(BaseRepo):
    async def get_all(self) -> list[StopWord]:
        result = await self.session.execute(select(StopWord))
        return list(result.scalars().all())

    async def get_words(self) -> list[str]:
        """Список стоп-слов для фильтрации."""
        return [w.word.lower() for w in await self.get_all()]

    async def add(self, word: str) -> StopWord:
        w = StopWord(word=word.strip().lower())
        self.session.add(w)
        await self.session.flush()
        return w

    async def remove(self, word: str) -> bool:
        result = await self.session.execute(
            delete(StopWord).where(StopWord.word == word.strip().lower())
        )
        await self.session.flush()
        return result.rowcount > 0

    async def exists(self, word: str) -> bool:
        result = await self.session.execute(
            select(StopWord).where(StopWord.word == word.strip().lower())
        )
        return result.scalar_one_or_none() is not None

    async def add_bulk(self, words: list[str]) -> int:
        """Добавить несколько слов игнорируя дубликаты."""
        added = 0
        for w in words:
            if not await self.exists(w):
                await self.add(w)
                added += 1
        return added