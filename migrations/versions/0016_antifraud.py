"""Additive durable antifraud evidence. No existing user/sponsor rows are rewritten."""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    from db.antifraud_models import AntifraudEvent, AntifraudRateState, AntifraudSnapshot
    for model in (AntifraudRateState, AntifraudSnapshot, AntifraudEvent):
        model.__table__.create(op.get_bind())


def downgrade():
    bind = op.get_bind()
    for name in ("antifraud_events", "antifraud_snapshots", "antifraud_rate_states"):
        if bind.execute(sa.text(f"SELECT count(*) FROM {name}")).scalar():
            raise RuntimeError("Antifraud evidence/state exists; downgrade would erase safety history")
    for name in ("antifraud_events", "antifraud_snapshots", "antifraud_rate_states"):
        op.drop_table(name)
