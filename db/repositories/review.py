"""Репозиторий отзывов."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import and_, func, literal, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Review, ReviewStatus
from db.base import utcnow
from db.repositories.base import BaseRepo


class ReviewRepo(BaseRepo):
    async def create(
        self,
        user_id: int,
        rating: int,
        text: str,
        is_anonymous: bool = False,
    ) -> Review:
        review = Review(
            user_id=user_id,
            rating=rating,
            text=text,
            is_anonymous=is_anonymous,
            status=ReviewStatus.PENDING.value,
        )
        self.session.add(review)
        await self.session.flush()
        return review

    async def create_if_no_recent(
        self,
        *,
        user_id: int,
        rating: int,
        text: str,
        is_anonymous: bool,
        cooldown_days: int,
    ) -> Review | None:
        """Создаёт отзыв, атомарно соблюдая cooldown пользователя."""
        cutoff = utcnow() - timedelta(days=max(0, cooldown_days))
        recent_exists = select(Review.id).where(
            Review.user_id == user_id,
            Review.created_at >= cutoff,
        ).exists()
        stmt = (
            sqlite_insert(Review)
            .from_select(
                ["user_id", "rating", "text", "is_anonymous"],
                select(
                    literal(user_id),
                    literal(rating),
                    literal(text),
                    literal(is_anonymous),
                ).where(~recent_exists),
            )
            .returning(Review.id)
        )
        review_id = (await self.session.execute(stmt)).scalar_one_or_none()
        return await self.session.get(Review, review_id) if review_id else None

    async def get_pending(self, limit: int = 50) -> list[Review]:
        result = await self.session.execute(
            select(Review)
            .where(Review.status == ReviewStatus.PENDING.value)
            .order_by(Review.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user(self, user_id: int) -> Review | None:
        result = await self.session.execute(
            select(Review)
            .where(Review.user_id == user_id)
            .order_by(Review.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def approve(self, id: int) -> Review | None:
        result = await self.session.execute(
            update(Review)
            .where(
                Review.id == id,
                Review.status == ReviewStatus.PENDING.value,
            )
            .values(status=ReviewStatus.APPROVED.value)
            .returning(Review.id)
            .execution_options(synchronize_session="fetch")
        )
        if result.scalar_one_or_none() is None:
            return None
        return await self.session.get(Review, id)

    async def reject(self, id: int, note: str | None = None) -> Review | None:
        result = await self.session.execute(
            update(Review)
            .where(
                Review.id == id,
                Review.status == ReviewStatus.PENDING.value,
            )
            .values(status=ReviewStatus.REJECTED.value, moderation_note=note)
            .returning(Review.id)
            .execution_options(synchronize_session="fetch")
        )
        if result.scalar_one_or_none() is None:
            return None
        return await self.session.get(Review, id)

    async def convert_to_ticket(self, id: int, note: str) -> Review | None:
        result = await self.session.execute(
            update(Review)
            .where(
                Review.id == id,
                Review.status == ReviewStatus.PENDING.value,
            )
            .values(status=ReviewStatus.CONVERTED.value, moderation_note=note)
            .returning(Review.id)
            .execution_options(synchronize_session="fetch")
        )
        if result.scalar_one_or_none() is None:
            return None
        return await self.session.get(Review, id)

    async def mark_published(self, id: int) -> None:
        await self.session.execute(
            update(Review)
            .where(
                Review.id == id,
                Review.status == ReviewStatus.APPROVED.value,
                Review.published_at.is_(None),
            )
            .values(published_at=utcnow())
            .execution_options(synchronize_session="fetch")
        )

    async def count_pending(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Review).where(
                Review.status == ReviewStatus.PENDING.value
            )
        )
        return result.scalar_one()

    async def count_by_rating(self) -> dict[int, int]:
        """Распределение по рейтингам для дашборда."""
        result = await self.session.execute(
            select(Review.rating, func.count())
            .where(Review.status == ReviewStatus.APPROVED.value)
            .group_by(Review.rating)
        )
        return dict(result.all())

    async def has_recent_review(self, user_id: int, days: int = 7) -> bool:
        cutoff = utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(func.count())
            .select_from(Review)
            .where(
                and_(
                    Review.user_id == user_id,
                    Review.created_at >= cutoff,
                )
            )
        )
        return result.scalar_one() > 0
