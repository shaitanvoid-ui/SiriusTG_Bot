"""0009: поддержка + уведомления (Этап 11).

support_tickets.status / closed_at; support_messages (тред);
users.notify_prefs (JSON-преференции уведомлений).

Revision: 0009
Revises: 0008
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _ts() -> sa.TextClause:
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.add_column(
        "support_tickets",
        sa.Column("status", sa.String(16), nullable=False, server_default="new"),
    )
    op.add_column(
        "support_tickets",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])

    op.create_table(
        "support_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(8), nullable=False, server_default="user"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_ts()),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_messages_ticket_id", "support_messages", ["ticket_id"])

    op.add_column("users", sa.Column("notify_prefs", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "notify_prefs")
    op.drop_table("support_messages")
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_column("support_tickets", "closed_at")
    op.drop_column("support_tickets", "status")
