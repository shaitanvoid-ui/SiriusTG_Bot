"""0007: instructions, reviews, stop_words.

Revision: 0007
Revises: 0006_gamification
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006_gamification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("instructions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Reviews
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="'pending'"),
        sa.Column("moderation_note", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_reviews_status_created", "status", "created_at"),
    )

    # Stop words
    op.create_table(
        "stop_words",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("word", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP"),
        sa.UniqueConstraint("word"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed-данные для инструкций засеим через сервис (settings.py seed_defaults)


def downgrade() -> None:
    op.drop_table("stop_words")
    op.drop_table("reviews")
    op.drop_table("instructions")
