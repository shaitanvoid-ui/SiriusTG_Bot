"""Репозиторий отзывов."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Review, ReviewStatus
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
            select(Review).where(Review.user_id == user_id).order_by(Review.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def approve(self, id: int) -> Review | None:
        review = await self.session.get(Review, id)
        if not review or review.status != ReviewStatus.PENDING.value:
            return None
        review.status = ReviewStatus.APPROVED.value
        review.published_at = datetime.utcnow()
        await self.session.flush()
        return review

    async def reject(self, id: int, note: str | None = None) -> Review | None:
        review = await self.session.get(Review, id)
        if not review or review.status != ReviewStatus.PENDING.value:
            return None
        review.status = ReviewStatus.REJECTED.value
        review.moderation_note = note
        await self.session.flush()
        return review

    async def convert_to_ticket(self, id: int, note: str) -> Review | None:
        review = await self.session.get(Review, id)
        if not review:
            return None
        review.status = ReviewStatus.CONVERTED.value
        review.moderation_note = note
        await self.session.flush()
        return review

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
        cutoff = datetime.utcnow() - timedelta(days=days)
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