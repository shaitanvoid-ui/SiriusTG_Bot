"""0013: one paid spin per confirmation token, retaining all historical spins."""

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wheel_spins", sa.Column("request_token", sa.String(32), nullable=True))
    op.create_index("uq_wheel_paid_request", "wheel_spins", ["user_id", "request_token"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_wheel_paid_request", table_name="wheel_spins")
    op.drop_column("wheel_spins", "request_token")
