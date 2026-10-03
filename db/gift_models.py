"""Durable gift intents, attempts and owner decisions; no network state in FSM."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base, TimestampMixin


class GiftQuote(TimestampMixin, Base):
    __tablename__ = "gift_quotes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    recipient_tg_id: Mapped[int] = mapped_column(BigInteger)
    gift_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(128))
    route: Mapped[str] = mapped_column(String(16), default="regular")
    stars: Mapped[int] = mapped_column(BigInteger)
    cost_units: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GiftRequest(TimestampMixin, Base):
    __tablename__ = "gift_requests"
    __table_args__ = (
        CheckConstraint("stars > 0 AND cost_units > 0", name="ck_gift_positive_cost"),
        CheckConstraint("status IN ('pending','waiting_funds','processing','succeeded','failed','cancelled','reconciliation_required')", name="ck_gift_status"),
        CheckConstraint("reserve_state IN ('held','released','consumed')", name="ck_gift_reserve"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey("gift_quotes.id", ondelete="RESTRICT"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    recipient_tg_id: Mapped[int] = mapped_column(BigInteger)
    gift_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(128))
    route: Mapped[str] = mapped_column(String(16), default="regular")
    stars: Mapped[int] = mapped_column(BigInteger)
    cost_units: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    reserve_state: Mapped[str] = mapped_column(String(16), default="held")
    worker_token: Mapped[str | None] = mapped_column(String(32))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    confirmation_kind: Mapped[str | None] = mapped_column(String(32))
    proof: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_status: Mapped[str | None] = mapped_column(String(32))
    notification_error: Mapped[str | None] = mapped_column(String(64))
    alerted_key: Mapped[str | None] = mapped_column(String(128))


class GiftAttempt(TimestampMixin, Base):
    __tablename__ = "gift_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("gift_requests.id", ondelete="RESTRICT"), index=True)
    worker_token: Mapped[str] = mapped_column(String(32), unique=True)
    phase: Mapped[str] = mapped_column(String(32), default="preparing")
    sender_tg_id: Mapped[int | None] = mapped_column(BigInteger)
    form_id: Mapped[int | None] = mapped_column(BigInteger)
    error_code: Mapped[str | None] = mapped_column(String(64))
    proof: Mapped[str | None] = mapped_column(Text)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GiftAdminDecision(TimestampMixin, Base):
    __tablename__ = "gift_admin_decisions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("gift_requests.id", ondelete="RESTRICT"), index=True)
    actor_tg_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[str | None] = mapped_column(Text)
