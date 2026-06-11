"""userbot sessions + daily bonus + streak

Revision ID: 0005_userbot_bonus
Revises: 0004_clicker_promos_tasks
Create Date: 2026-05-29 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_userbot_bonus"
down_revision: Union[str, None] = "0004_clicker_promos_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- users: streak-поля ----------
    op.add_column(
        "users",
        sa.Column("bonus_streak", sa.Integer, nullable=False, server_default=sa.text("0")),
    )
    op.add_column("users", sa.Column("last_bonus_date", sa.Date, nullable=True))

    # ---------- daily_bonus_log ----------
    op.create_table(
        "daily_bonus_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column("amount", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("streak", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("bio_ok", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "day", name="uq_daily_bonus_user_day"),
    )
    op.create_index("ix_daily_bonus_log_user_id", "daily_bonus_log", ["user_id"])
    op.create_index("ix_daily_bonus_log_day", "daily_bonus_log", ["day"])

    # ---------- userbot_sessions ----------
    op.create_table(
        "userbot_sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("session_enc", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("label", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_userbot_sessions_phone", "userbot_sessions", ["phone"], unique=True)
    op.create_index("ix_userbot_sessions_is_active", "userbot_sessions", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_userbot_sessions_is_active", table_name="userbot_sessions")
    op.drop_index("ix_userbot_sessions_phone", table_name="userbot_sessions")
    op.drop_table("userbot_sessions")

    op.drop_index("ix_daily_bonus_log_day", table_name="daily_bonus_log")
    op.drop_index("ix_daily_bonus_log_user_id", table_name="daily_bonus_log")
    op.drop_table("daily_bonus_log")

    op.drop_column("users", "last_bonus_date")
    op.drop_column("users", "bonus_streak")
