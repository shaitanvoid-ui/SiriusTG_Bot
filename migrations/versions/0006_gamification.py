"""wheel spins + achievements + leaderboard payouts

Revision ID: 0006_gamification
Revises: 0005_userbot_bonus
Create Date: 2026-05-29 16:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006_gamification"
down_revision: Union[str, None] = "0005_userbot_bonus"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- wheel_spins ----------
    op.create_table(
        "wheel_spins",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column("prize", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("cost", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("is_free", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_wheel_spins_user_id", "wheel_spins", ["user_id"])
    op.create_index("ix_wheel_spins_day", "wheel_spins", ["day"])
    op.create_index("ix_wheel_spins_user_day", "wheel_spins", ["user_id", "day"])

    # ---------- user_achievements ----------
    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("reward", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "code", name="uq_user_achievement"),
    )
    op.create_index("ix_user_achievements_user_id", "user_achievements", ["user_id"])

    # ---------- leaderboard_payouts ----------
    op.create_table(
        "leaderboard_payouts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("week_key", sa.String(16), nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("rank", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("amount", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("week_key", "user_id", name="uq_leaderboard_payout"),
    )
    op.create_index("ix_leaderboard_payouts_week_key", "leaderboard_payouts", ["week_key"])
    op.create_index("ix_leaderboard_payouts_user_id", "leaderboard_payouts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_leaderboard_payouts_user_id", table_name="leaderboard_payouts")
    op.drop_index("ix_leaderboard_payouts_week_key", table_name="leaderboard_payouts")
    op.drop_table("leaderboard_payouts")

    op.drop_index("ix_user_achievements_user_id", table_name="user_achievements")
    op.drop_table("user_achievements")

    op.drop_index("ix_wheel_spins_user_day", table_name="wheel_spins")
    op.drop_index("ix_wheel_spins_day", table_name="wheel_spins")
    op.drop_index("ix_wheel_spins_user_id", table_name="wheel_spins")
    op.drop_table("wheel_spins")
