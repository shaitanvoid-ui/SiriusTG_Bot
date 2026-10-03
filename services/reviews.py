"""Сервис отзывов: фильтры, валидация, модерация, публикация."""
from __future__ import annotations

import re
from typing import Any

from aiogram import Bot, html
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.review import ReviewRepo
from db.repositories.stop_word import StopWordRepo
from db.repositories.user import UserRepo
from db.repositories.support import TicketRepo
from db.models import Review, TicketAuthor, User
from db.money import from_units, settlement_units
from locales.ru import T
from services.notifications import NotificationService
from services.settings import SettingsService
from core.logger import get_logger


log = get_logger(__name__)


class ReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReviewRepo(session)
        self.stop_repo = StopWordRepo(session)
        self._stop_words: list[str] | None = None

    async def _get_stop_words(self) -> list[str]:
        if self._stop_words is None:
            self._stop_words = await self.stop_repo.get_words()
        return self._stop_words

    async def check_antispam(self, user: User) -> tuple[bool, str]:
        """Антиспам: лимит рефов, кулдаун, shadow-ban."""
        s = SettingsService(self.session)
        min_refs = await s.get_int("review.antispam_min_refs", 3)
        cooldown_days = await s.get_int("review.antispam_cooldown_days", 7)

        if user.confirmed_ref_count < min_refs:
            return False, f"Нужно минимум {min_refs} подтверждённых рефералов"

        if not await UserRepo(self.session).rewards_allowed(user.id):
            return False, "Доступ временно ограничен"

        if await self.repo.has_recent_review(user.id, cooldown_days):
            return False, f"Следующий отзыв можно оставить через {cooldown_days} дней"

        return True, ""

    async def filter_text(self, text: str) -> tuple[bool, str]:
        """Авто-фильтры текста. Возвращает (passed, reason)."""
        s = SettingsService(self.session)
        min_len = await s.get_int("review.min_text_length", 30)
        max_len = await s.get_int("review.max_text_length", 500)

        if len(text) < min_len:
            return False, f"Слишком коротко (минимум {min_len} символов)"
        if len(text) > max_len:
            return False, f"Слишком длинно (максимум {max_len} символов)"

        if re.search(r"https?://|t\.me/|@", text):
            return False, "Ссылки запрещены"

        upper = sum(1 for c in text if c.isupper())
        total = sum(1 for c in text if c.isalpha())
        if total > 10 and upper / total > 0.3:
            return False, "Слишком много заглавных букв"

        stop_words = await self._get_stop_words()
        text_lower = text.lower()
        for w in stop_words:
            if w in text_lower:
                return False, "Текст содержит запрещённые слова"

        emoji_pattern = re.compile(r"([\U0001F300-\U0001F9FF])\1{2,}")
        if emoji_pattern.search(text):
            return False, "Повторяющиеся эмодзи запрещены"

        return True, ""

    async def create_review(
        self,
        user: User,
        rating: int,
        text: str,
        is_anonymous: bool,
    ) -> tuple[Review | None, str]:
        """Создать отзыв. Возвращает (review, error_msg)."""
        ok, reason = await self.check_antispam(user)
        if not ok:
            return None, reason

        ok, reason = await self.filter_text(text)
        if not ok:
            return None, reason

        cooldown_days = await SettingsService(self.session).get_int(
            "review.antispam_cooldown_days", 7
        )
        review = await self.repo.create_if_no_recent(
            user_id=user.id,
            rating=rating,
            text=text,
            is_anonymous=is_anonymous,
            cooldown_days=cooldown_days,
        )
        if review is None:
            return None, f"Следующий отзыв можно оставить через {cooldown_days} дней"
        return review, ""

    async def moderate(
        self,
        review_id: int,
        action: str,
        note: str | None = None,
    ) -> tuple[Review | None, str]:
        """Модерация отзыва. Возвращает (review, action_key)."""
        user_repo = UserRepo(self.session)

        if action == "approve":
            candidate = await self.session.get(Review, review_id)
            if candidate is not None and not await user_repo.lock_rewards_allowed(candidate.user_id):
                return None, "blocked"
            review = await self.repo.approve(review_id)
            if review is None:
                return None, "pending"
            s = SettingsService(self.session)
            reward = float(from_units(settlement_units(await s.get_float("review.reward", 1.0))))
            if reward > 0:
                await user_repo.add_balance(review.user_id, reward, reason="review_reward")
            return review, "approved"

        elif action == "reject":
            review = await self.repo.reject(review_id, note)
            if review is None:
                return None, "pending"
            return review, "rejected"

        elif action == "convert":
            review = await self.repo.convert_to_ticket(review_id, note or "")
            if review is None:
                return None, "pending"
            stars = "⭐" * review.rating
            stars_line = f"{stars} {review.rating}/5"
            ticket_repo = TicketRepo(self.session)
            ticket = await ticket_repo.create(
                user_id=review.user_id,
                subject=f"Отзыв #{review.id} ({stars_line}) — конвертирован",
                text=f"Рейтинг: {stars_line}\n\nОтзыв:\n{review.text}\n\nМодератор: {note or 'без комментария'}",
                review_id=review.id,
            )
            # первое сообщение треда — чтобы переписка рендерилась (Этап 11)
            await ticket_repo.add_message(ticket, TicketAuthor.USER, ticket.text)
            return review, "converted"

        return None, "pending"

    async def publish_review(self, bot: Bot, review: Review) -> None:
        """Публикация одобренного отзыва в канал отзывов (если настроен)."""
        s = SettingsService(self.session)
        channel_id = (await s.get_str("reviews_channel_id", "")).strip()
        if not channel_id:
            return

        author = T.review_channel_anon
        if not review.is_anonymous:
            db_user = await UserRepo(self.session).get_by_id(review.user_id)
            if db_user and db_user.username:
                author = f"@{db_user.username}"
            elif db_user and db_user.first_name:
                author = db_user.first_name

        try:
            await bot.send_message(
                int(channel_id),
                T.review_channel_post.format(
                    stars="⭐" * review.rating,
                    text=html.quote(review.text),
                    author=html.quote(author),
                ),
            )
            await self.repo.mark_published(review.id)
        except (TelegramAPIError, ValueError) as exc:
            log.warning(
                "review_publish_failed",
                review_id=review.id,
                error=str(exc),
            )

    async def notify_user_approved(self, bot: Bot, review: Review, reward: float) -> None:
        """DM юзеру: отзыв опубликован (+ награда, если была)."""
        db_user = await UserRepo(self.session).get_by_id(review.user_id)
        if db_user is None:
            return
        if not NotificationService.is_enabled(db_user, "rewards"):
            return
        reward_line = (
            T.notify_review_reward_part.format(reward=f"{reward:.2f}") if reward > 0 else ""
        )
        try:
            await bot.send_message(
                db_user.tg_id,
                T.notify_review_approved.format(reward_line=reward_line),
            )
        except TelegramAPIError:
            pass

    async def notify_log(self, bot: Bot, review: Review, action_key: str) -> None:
        """Отправить уведомление об действии модератора в LOG_CHANNEL_ID."""
        from core.config import settings

        if not settings.log_channel_id:
            return

        user_repo = UserRepo(self.session)
        db_user = await user_repo.get_by_id(review.user_id)
        stars = "⭐" * review.rating

        if action_key == "approved":
            text = T.log_review_approved.format(id=review.id)
        elif action_key == "rejected":
            text = T.log_review_rejected.format(id=review.id)
        else:
            text = T.log_review_converted.format(id=review.id)

        try:
            await bot.send_message(
                settings.log_channel_id,
                f"{text}\n━━━━━━━━━━━━━━━\n"
                f"Юзер: {f'@{db_user.username}' if db_user and db_user.username else (db_user.tg_id if db_user else '?')}\n"
                f"Рейтинг: {stars} {review.rating}/5\n"
                f"Текст: {html.quote(review.text[:200])}",
            )
        except TelegramAPIError:
            pass


async def get_review_stats(session: AsyncSession) -> dict[str, Any]:
    """Статистика отзывов для дашборда."""
    repo = ReviewRepo(session)
    by_rating = await repo.count_by_rating()
    pending = await repo.count_pending()

    total_approved = sum(by_rating.values())
    avg_rating = (
        sum(r * c for r, c in by_rating.items()) / total_approved
        if total_approved > 0
        else 0.0
    )

    return {
        "pending": pending,
        "total_approved": total_approved,
        "avg_rating": round(avg_rating, 2),
        "by_rating": by_rating,
    }
