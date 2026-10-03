"""Durable gift queue. Refuse downgrade with real requests or audit history."""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    # Import only the new tables; exact-money migration owns existing tables.
    from db.gift_models import GiftQuote, GiftRequest, GiftAttempt, GiftAdminDecision
    bind = op.get_bind()
    for model in (GiftQuote, GiftRequest, GiftAttempt, GiftAdminDecision):
        model.__table__.create(bind)


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT count(*) FROM gift_requests")).scalar():
        raise RuntimeError("Gift requests/history exist; downgrade would destroy financial evidence")
    for name in ("gift_admin_decisions", "gift_attempts", "gift_requests", "gift_quotes"):
        op.drop_table(name)
