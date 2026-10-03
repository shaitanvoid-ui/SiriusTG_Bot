"""Durable limiter, explainable snapshots and append-only antifraud evidence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, utcnow


class AntifraudRateState(Base):
    __tablename__ = "antifraud_rate_states"
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    accepted_times_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    click_times_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AntifraudSnapshot(Base):
    __tablename__ = "antifraud_snapshots"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    strong_signals_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (CheckConstraint("score >= 0 AND score <= 100", name="ck_antifraud_score"),)


class AntifraudEvent(Base):
    __tablename__ = "antifraud_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_key: Mapped[str | None] = mapped_column(String(192), nullable=True, unique=True)
    actor_tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        Index("ix_antifraud_event_actor_time", "tg_id", "created_at"),
        Index("ix_antifraud_event_user_time", "user_id", "created_at"),
    )
