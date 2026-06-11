"""0008: партнёрская система (Этап 10) + фикс support_tickets.

partners, partner_links, partner_payouts;
users.partner_id / users.partner_link_id, sponsors.partner_id;
support_tickets — таблица была в моделях с Этапа 8, но миграции не имела.

Revision: 0008
Revises: 0007
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _ts() -> sa.TextClause:
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    # --- support_tickets (фикс Этапа 8: модель есть, таблицы не было) ---
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_ts()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_ts()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])
    op.create_index("ix_support_tickets_review_id", "support_tickets", ["review_id"])

    # --- партнёры ---
    op.create_table(
        "partners",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("reward_per_user", sa.Float(), nullable=True),
        sa.Column("percent_sponsor", sa.Float(), nullable=True),
        sa.Column("balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_ts()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_ts()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_partners_status", "partners", ["status"])

    op.create_table(
        "partner_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("title", sa.String(64), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("joins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_ts()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_ts()),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_partner_links_partner_id", "partner_links", ["partner_id"])

    op.create_table(
        "partner_payouts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("amount_stars", sa.Float(), nullable=False),
        sa.Column("rate_rub", sa.Float(), nullable=False),
        sa.Column("amount_rub", sa.Float(), nullable=False),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("requisites", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_ts()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_ts()),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_partner_payouts_partner_id", "partner_payouts", ["partner_id"])
    op.create_index("ix_partner_payouts_status", "partner_payouts", ["status"])

    # --- атрибуция на существующих таблицах ---
    op.add_column("users", sa.Column("partner_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("partner_link_id", sa.Integer(), nullable=True))
    op.create_index("ix_users_partner_id", "users", ["partner_id"])

    op.add_column("sponsors", sa.Column("partner_id", sa.Integer(), nullable=True))
    op.create_index("ix_sponsors_partner_id", "sponsors", ["partner_id"])


def downgrade() -> None:
    op.drop_index("ix_sponsors_partner_id", table_name="sponsors")
    op.drop_column("sponsors", "partner_id")
    op.drop_index("ix_users_partner_id", table_name="users")
    op.drop_column("users", "partner_link_id")
    op.drop_column("users", "partner_id")
    op.drop_table("partner_payouts")
    op.drop_table("partner_links")
    op.drop_table("partners")
    op.drop_table("support_tickets")
