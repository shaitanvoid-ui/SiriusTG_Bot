"""ORM-модели. Подключаются по мере прохождения этапов."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin, utcnow


# ---------- enums ----------

class SponsorKind(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class SubscriptionStatus(StrEnum):
    UNKNOWN = "unknown"
    SUBSCRIBED = "subscribed"
    NOT_SUBSCRIBED = "not_subscribed"
    LEFT = "left"


class SettingType(StrEnum):
    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    JSON = "json"


class ReferralSource(StrEnum):
    DIRECT = "direct"
    UTM = "utm"
    BIO = "bio"
    PROMO = "promo"


class TicketStatus(StrEnum):
    """Жизненный цикл тикета поддержки (Этап 11).

    NEW — создан юзером, ждёт первого ответа админа.
    IN_PROGRESS — юзер дописал после ответа, снова ждёт админа.
    AWAITING — админ ответил, ждёт реакции юзера.
    CLOSED — закрыт (юзером, админом или автозакрытием).
    """

    NEW = "new"
    IN_PROGRESS = "in_progress"
    AWAITING = "awaiting"
    CLOSED = "closed"


class TicketAuthor(StrEnum):
    USER = "user"
    ADMIN = "admin"


# ---------- tables ----------

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # gates
    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captcha_passed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subs_passed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # state flags
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_shadow_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # economy (заполнится в следующих этапах)
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    debt: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ref_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confirmed_ref_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    referrer_tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    # ежедневный бонус + streak (Этап 5)
    bonus_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_bonus_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # партнёрская атрибуция (Этап 10): кто привёл юзера по UTM-ссылке
    partner_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    partner_link_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # преференции уведомлений (Этап 11): JSON {"refs": bool, "tasks": bool, "rewards": bool}.
    # NULL = всё включено (дефолт).
    notify_prefs: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subscriptions: Mapped[list["UserSubscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Sponsor(TimestampMixin, Base):
    __tablename__ = "sponsors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default=SponsorKind.PUBLIC.value)
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    invite_link: Mapped[str | None] = mapped_column(String(256), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # лимит подписок (0 = без лимита). Когда reach_limit — авто-выкл.
    subs_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subs_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    reward: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_honeypot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # партнёрский спонсор (Этап 10): чей канал, тому идёт доля с заданий
    partner_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    __table_args__ = (
        Index("ix_sponsors_required_active", "is_required", "is_active"),
    )


class UserSubscription(TimestampMixin, Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sponsor_id: Mapped[int] = mapped_column(ForeignKey("sponsors.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=SubscriptionStatus.UNKNOWN.value)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="subscriptions")
    sponsor: Mapped[Sponsor] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "sponsor_id", name="uq_user_sponsor"),
    )


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default=SettingType.STR.value)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ActionLog(Base):
    __tablename__ = "action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class Referral(TimestampMixin, Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    referred_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_rewarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_matured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    reward_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    debt_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    matured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lost_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped[str] = mapped_column(String(16), nullable=False, default=ReferralSource.DIRECT.value)

    __table_args__ = (
        UniqueConstraint("referred_user_id", name="uq_referrals_referred"),
        Index("ix_referrals_referrer", "referrer_user_id"),
        Index("ix_referrals_pending_maturation", "is_confirmed", "is_matured"),
    )


class Promo(TimestampMixin, Base):
    __tablename__ = "promos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    reward: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_activations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_honeypot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class PromoActivation(Base):
    __tablename__ = "promo_activations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    promo_id: Mapped[int] = mapped_column(
        ForeignKey("promos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reward: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_honeypot_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("promo_id", "user_id", name="uq_promo_user"),
    )


class UserTaskCompletion(Base):
    __tablename__ = "user_task_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sponsor_id: Mapped[int] = mapped_column(
        ForeignKey("sponsors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reward: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "sponsor_id", name="uq_user_task"),
    )


class ClickerDay(Base):
    """Состояние кликера на один день. Один ряд на (user, day)."""

    __tablename__ = "clicker_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    earned: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # последний клик в миллисекундах с эпохи (UTC). Для rate-limit.
    last_click_ms: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # кликов с момента последней мини-капчи. Для триггера новой.
    since_captcha: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # порог, при достижении которого срабатывает мини-капча.
    captcha_threshold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # активный токен мини-капчи (если установлен — клики блокируются до проверки).
    captcha_token: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # правильный эмодзи (тот, которого НЕТ в подсказке).
    captcha_answer: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # подсказка-список эмодзи через '|'.
    captcha_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 4 варианта на кнопках через '|'.
    captcha_choices: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_clicker_user_day"),
    )


class DailyBonusLog(Base):
    """Лог выдачи ежедневного бонуса. Один ряд на (user, day) — идемпотентность."""

    __tablename__ = "daily_bonus_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    streak: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    bio_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_daily_bonus_user_day"),
    )


class UserbotSession(TimestampMixin, Base):
    """Зашифрованная Telethon StringSession. По ряду на каждый userbot-аккаунт."""

    __tablename__ = "userbot_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    session_enc: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(32), nullable=True)


class WheelSpin(Base):
    """Лог вращения колеса фортуны. Free-спин лимитируется на (user, day)."""

    __tablename__ = "wheel_spins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    prize: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_wheel_spins_user_day", "user_id", "day"),
    )


class UserAchievement(Base):
    """Полученное достижение. Одно на (user, code) — единоразовая награда."""

    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    reward: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_user_achievement"),
    )


class LeaderboardPayout(Base):
    """Лог недельных выплат топа. Идемпотентность по (week_key, user)."""

    __tablename__ = "leaderboard_payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_key: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("week_key", "user_id", name="uq_leaderboard_payout"),
    )


# ---------- Этап 8: Инструкция + Отзывы ----------
class Instruction(Base):
    """Страница инструкции. Контент редактируется через админку."""

    __tablename__ = "instructions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"


class Review(Base):
    """Отзыв пользователя — от FSM до модерации."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ReviewStatus.PENDING.value, index=True
    )
    moderation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_reviews_status_created", "status", "created_at"),
    )


class StopWord(Base):
    """Стоп-слова для фильтра отзывов. Редактируются через админку."""

    __tablename__ = "stop_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class SupportTicket(Base):
    """Тикет поддержки (Этап 8: конвертация отзыва; Этап 11: полный флоу)."""

    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    review_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=TicketStatus.NEW.value, index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SupportMessage(Base):
    """Сообщение в треде тикета (Этап 11). Первое создаётся вместе с тикетом."""

    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author: Mapped[str] = mapped_column(
        String(8), nullable=False, default=TicketAuthor.USER.value
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


# ---------- Этап 10: партнёрская система ----------

class PartnerStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"


class PayoutMethod(StrEnum):
    CARD = "card"
    YOOMONEY = "yoomoney"


class PayoutStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    REJECTED = "rejected"


class Partner(TimestampMixin, Base):
    """Партнёр: ведёт трафик по UTM-ссылкам и/или даёт свои спонсорские каналы."""

    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PartnerStatus.ACTIVE.value, index=True
    )

    # персональные ставки; NULL = брать дефолт из settings (partner.*)
    reward_per_user: Mapped[float | None] = mapped_column(Float, nullable=True)
    percent_sponsor: Mapped[float | None] = mapped_column(Float, nullable=True)

    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_earned: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PartnerLink(TimestampMixin, Base):
    """UTM-ссылка партнёра: t.me/<bot>?start=p<code>."""

    __tablename__ = "partner_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(64), nullable=False)

    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    joins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PartnerPayout(TimestampMixin, Base):
    """Заявка партнёра на выплату. Курс ⭐→₽ фиксируется на момент запроса."""

    __tablename__ = "partner_payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_stars: Mapped[float] = mapped_column(Float, nullable=False)
    rate_rub: Mapped[float] = mapped_column(Float, nullable=False)
    amount_rub: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    requisites: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PayoutStatus.PENDING.value, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "Base",
    "User",
    "Sponsor",
    "UserSubscription",
    "Setting",
    "ActionLog",
    "Referral",
    "Promo",
    "PromoActivation",
    "UserTaskCompletion",
    "ClickerDay",
    "DailyBonusLog",
    "UserbotSession",
    "WheelSpin",
    "UserAchievement",
    "LeaderboardPayout",
    "Instruction",
    "Review",
    "StopWord",
    "SupportTicket",
    "Partner",
    "PartnerLink",
    "PartnerPayout",
    "PartnerStatus",
    "PayoutMethod",
    "PayoutStatus",
    "SponsorKind",
    "SubscriptionStatus",
    "SettingType",
    "ReferralSource",
    "ReviewStatus",
]
