"""clicker + promos + task completions

Revision ID: 0004_clicker_promos_tasks
Revises: 0003_referrals
Create Date: 2026-05-28 20:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004_clicker_promos_tasks"
down_revision: Union[str, None] = "0003_referrals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- promos ----------
    op.create_table(
        "promos",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("reward", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("max_activations", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("used_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_honeypot", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_promos_code", "promos", ["code"], unique=True)
    op.create_index("ix_promos_is_active", "promos", ["is_active"])

    # ---------- promo_activations ----------
    op.create_table(
        "promo_activations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("promo_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("reward", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("is_honeypot_hit", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["promo_id"], ["promos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("promo_id", "user_id", name="uq_promo_user"),
    )
    op.create_index("ix_promo_activations_promo_id", "promo_activations", ["promo_id"])
    op.create_index("ix_promo_activations_user_id", "promo_activations", ["user_id"])

    # ---------- user_task_completions ----------
    op.create_table(
        "user_task_completions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("sponsor_id", sa.Integer, nullable=False),
        sa.Column("reward", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sponsor_id"], ["sponsors.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "sponsor_id", name="uq_user_task"),
    )
    op.create_index("ix_user_task_completions_user_id", "user_task_completions", ["user_id"])
    op.create_index("ix_user_task_completions_sponsor_id", "user_task_completions", ["sponsor_id"])

    # ---------- clicker_days ----------
    op.create_table(
        "clicker_days",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column("clicks", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("earned", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("last_click_ms", sa.BigInteger, nullable=False, server_default=sa.text("0")),
        sa.Column("since_captcha", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("captcha_threshold", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("captcha_token", sa.String(32), nullable=True),
        sa.Column("captcha_answer", sa.String(16), nullable=True),
        sa.Column("captcha_hint", sa.String(64), nullable=True),
        sa.Column("captcha_choices", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "day", name="uq_clicker_user_day"),
    )
    op.create_index("ix_clicker_days_user_id", "clicker_days", ["user_id"])
    op.create_index("ix_clicker_days_day", "clicker_days", ["day"])


def downgrade() -> None:
    op.drop_index("ix_clicker_days_day", table_name="clicker_days")
    op.drop_index("ix_clicker_days_user_id", table_name="clicker_days")
    op.drop_table("clicker_days")

    op.drop_index("ix_user_task_completions_sponsor_id", table_name="user_task_completions")
    op.drop_index("ix_user_task_completions_user_id", table_name="user_task_completions")
    op.drop_table("user_task_completions")

    op.drop_index("ix_promo_activations_user_id", table_name="promo_activations")
    op.drop_index("ix_promo_activations_promo_id", table_name="promo_activations")
    op.drop_table("promo_activations")

    op.drop_index("ix_promos_is_active", table_name="promos")
    op.drop_index("ix_promos_code", table_name="promos")
    op.drop_table("promos")
