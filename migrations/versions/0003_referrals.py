"""referrals

Revision ID: 0003_referrals
Revises: 0002_users_sponsors_settings
Create Date: 2026-05-28 18:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003_referrals"
down_revision: Union[str, None] = "0002_users_sponsors_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("referrer_user_id", sa.Integer, nullable=False),
        sa.Column("referred_user_id", sa.Integer, nullable=False),
        sa.Column("is_confirmed", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("is_rewarded", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("is_matured", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("reward_amount", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("debt_amount", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("matured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lost_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="direct"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["referrer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referred_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("referred_user_id", name="uq_referrals_referred"),
    )
    op.create_index("ix_referrals_referrer", "referrals", ["referrer_user_id"])
    op.create_index(
        "ix_referrals_pending_maturation", "referrals", ["is_confirmed", "is_matured"]
    )


def downgrade() -> None:
    op.drop_index("ix_referrals_pending_maturation", table_name="referrals")
    op.drop_index("ix_referrals_referrer", table_name="referrals")
    op.drop_table("referrals")
