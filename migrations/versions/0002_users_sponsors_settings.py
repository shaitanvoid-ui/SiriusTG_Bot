"""users, sponsors, user_subscriptions, settings, action_logs

Revision ID: 0002_users_sponsors_settings
Revises: 0001_initial
Create Date: 2026-05-28 11:50:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_users_sponsors_settings"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tg_id", sa.BigInteger, nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(128), nullable=True),
        sa.Column("last_name", sa.String(128), nullable=True),
        sa.Column("language_code", sa.String(8), nullable=True),
        sa.Column("is_premium", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("accepted_terms_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("captcha_passed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subs_passed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_banned", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("is_shadow_banned", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("balance", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("debt", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("ref_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("confirmed_ref_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("level", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("referrer_tg_id", sa.BigInteger, nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tg_id", name="uq_users_tg_id"),
    )
    op.create_index("ix_users_tg_id", "users", ["tg_id"])
    op.create_index("ix_users_is_banned", "users", ["is_banned"])
    op.create_index("ix_users_is_shadow_banned", "users", ["is_shadow_banned"])
    op.create_index("ix_users_referrer_tg_id", "users", ["referrer_tg_id"])

    op.create_table(
        "sponsors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(16), nullable=False, server_default="public"),
        sa.Column("chat_id", sa.BigInteger, nullable=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("invite_link", sa.String(256), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("subs_limit", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("subs_counter", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("reward", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("is_honeypot", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sponsors_chat_id", "sponsors", ["chat_id"])
    op.create_index("ix_sponsors_username", "sponsors", ["username"])
    op.create_index("ix_sponsors_is_required", "sponsors", ["is_required"])
    op.create_index("ix_sponsors_is_active", "sponsors", ["is_active"])
    op.create_index("ix_sponsors_required_active", "sponsors", ["is_required", "is_active"])

    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("sponsor_id", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sponsor_id"], ["sponsors.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "sponsor_id", name="uq_user_sponsor"),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("type", sa.String(16), nullable=False, server_default="str"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "action_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_tg_id", sa.BigInteger, nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("payload", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_action_logs_user_tg_id", "action_logs", ["user_tg_id"])
    op.create_index("ix_action_logs_action", "action_logs", ["action"])
    op.create_index("ix_action_logs_created_at", "action_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("action_logs")
    op.drop_table("settings")
    op.drop_table("user_subscriptions")
    op.drop_table("sponsors")
    op.drop_table("users")
