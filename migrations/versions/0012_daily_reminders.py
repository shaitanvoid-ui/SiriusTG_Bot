"""0012: durable daily notification marker, preserving every existing user."""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_daily_reminder_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_daily_reminder_date")
