"""0014: integer liabilities and auditable conversion of historical floats.

All amounts use 10,000 parts, Decimal(str(old)) and HALF_EVEN at four places.
No exchange rate changes. Every old amount has a recorded rounding difference;
opening journal rows establish balances and debts without replaying old awards.
Downgrade fails closed after any financial activity or while reserves exist.
"""
from decimal import Decimal, ROUND_HALF_EVEN

from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

FIELDS = {
    "users": ["balance", "debt"],
    "sponsors": ["reward"],
    "referrals": ["reward_amount", "debt_amount"],
    "promos": ["reward"],
    "promo_activations": ["reward"],
    "user_task_completions": ["reward"],
    "clicker_days": ["earned"],
    "daily_bonus_log": ["amount"],
    "wheel_spins": ["prize", "cost"],
    "user_achievements": ["reward"],
    "leaderboard_payouts": ["amount"],
    "partners": ["reward_per_user", "balance", "total_earned"],
    "partner_payouts": ["amount_stars", "rate_rub", "amount_rub"],
}


def upgrade() -> None:
    connection = op.get_bind()
    # Validate everything before the first DDL (SQLite DDL may autocommit).
    converted = []
    for table, fields in FIELDS.items():
        for row in connection.execute(sa.text(f'SELECT id, {", ".join(fields)} FROM "{table}"')).mappings():
            for field in fields:
                value = row[field]
                if value is None:
                    if table != "partners" or field != "reward_per_user":
                        raise RuntimeError(f"invalid NULL money: {table}.{field}#{row['id']}")
                    continue
                exact = Decimal(str(value))
                if not exact.is_finite() or exact < 0:
                    raise RuntimeError(f"invalid historical money: {table}.{field}#{row['id']}")
                rounded = exact.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
                units = int(rounded * 10_000)
                if units > 2**63 - 1:
                    raise RuntimeError(f"historical money exceeds integer storage: {table}.{field}")
                converted.append((table, row["id"], field, str(exact), units, str(rounded-exact)))

    op.create_table(
        "money_migration_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_name", sa.String(64), nullable=False),
        sa.Column("row_id", sa.Integer(), nullable=False),
        sa.Column("column_name", sa.String(64), nullable=False),
        sa.Column("original_value", sa.Text(), nullable=False),
        sa.Column("rounded_units", sa.BigInteger(), nullable=False),
        sa.Column("rounding_delta", sa.Text(), nullable=False),
        sa.UniqueConstraint("table_name", "row_id", "column_name", name="uq_money_migration_field"),
    )
    for table, fields in FIELDS.items():
        for field in fields:
            nullable = table == "partners" and field == "reward_per_user"
            op.add_column(table, sa.Column(f"{field}_units", sa.BigInteger(), nullable=nullable, server_default=None if nullable else "0"))
    op.add_column("users", sa.Column("reserved_units", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("partners", sa.Column("reserved_units", sa.BigInteger(), nullable=False, server_default="0"))
    for table, row_id, field, original, units, delta in converted:
        connection.execute(sa.text(f'UPDATE "{table}" SET "{field}_units"=:units WHERE id=:id'), {"units": units, "id": row_id})
        connection.execute(sa.text(
            "INSERT INTO money_migration_audit (table_name,row_id,column_name,original_value,rounded_units,rounding_delta) "
            "VALUES (:table,:id,:field,:original,:units,:delta)"
        ), {"table": table, "id": row_id, "field": field, "original": original, "units": units, "delta": delta})
    connection.execute(sa.text("UPDATE partners SET reserved_units=COALESCE((SELECT SUM(amount_stars_units) FROM partner_payouts WHERE partner_id=partners.id AND status='pending'),0)"))
    # Native DROP avoids recreating FK-connected tables and preserves row IDs,
    # unrelated constraints, indexes and triggers (SQLite >= 3.35).
    for table, fields in FIELDS.items():
        for field in fields:
            connection.execute(sa.text(f'ALTER TABLE "{table}" DROP COLUMN "{field}"'))
    op.create_table(
        "money_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_kind", sa.String(16), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id", ondelete="RESTRICT")),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("reference", sa.String(192), unique=True),
        sa.Column("balance_delta_units", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("debt_delta_units", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("reserved_delta_units", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("balance_after_units", sa.BigInteger(), nullable=False),
        sa.Column("debt_after_units", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("reserved_after_units", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    for field in ["user_id", "partner_id", "created_at"]:
        op.create_index(f"ix_money_operations_{field}", "money_operations", [field])
    connection.execute(sa.text(
        "INSERT INTO money_operations (account_kind,user_id,reason,reference,balance_delta_units,debt_delta_units,balance_after_units,debt_after_units) "
        "SELECT 'user',id,'migration_opening','opening:user:'||id,balance_units,debt_units,balance_units,debt_units FROM users"
    ))
    connection.execute(sa.text(
        "INSERT INTO money_operations (account_kind,partner_id,reason,reference,balance_delta_units,reserved_delta_units,balance_after_units,reserved_after_units) "
        "SELECT 'partner',id,'migration_opening','opening:partner:'||id,balance_units,reserved_units,balance_units,reserved_units FROM partners"
    ))
    for table, fields in FIELDS.items():
        for field in fields:
            mismatch = connection.execute(sa.text(
                f'SELECT COUNT(*) FROM money_migration_audit a JOIN "{table}" t ON t.id=a.row_id '
                f'WHERE a.table_name=:table AND a.column_name=:field AND t."{field}_units"!=a.rounded_units'
            ), {"table": table, "field": field}).scalar_one()
            if mismatch:
                raise RuntimeError("integer conversion audit failed")


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT COUNT(*) FROM money_operations WHERE reason != 'migration_opening'")).scalar_one():
        raise RuntimeError("0014 downgrade refused: financial operations exist; restore an encrypted pre-migration backup")
    if connection.execute(sa.text("SELECT COUNT(*) FROM users WHERE reserved_units != 0")).scalar_one():
        raise RuntimeError("0014 downgrade refused: active reserves exist")
    for table in ["users", "partners"]:
        current = "user_id" if table == "users" else "partner_id"
        extra = " OR t.debt_units != o.debt_after_units" if table == "users" else " OR t.reserved_units != o.reserved_after_units"
        if connection.execute(sa.text(
            f'SELECT COUNT(*) FROM "{table}" t JOIN money_operations o ON o.{current}=t.id '
            f'WHERE o.reason=\'migration_opening\' AND (t.balance_units != o.balance_after_units{extra})'
        )).scalar_one():
            raise RuntimeError("0014 downgrade refused: balances changed without journal")
    for table, fields in FIELDS.items():
        for field in fields:
            nullable = table == "partners" and field == "reward_per_user"
            op.add_column(table, sa.Column(field, sa.Float(), nullable=nullable, server_default=None if nullable else "0"))
            connection.execute(sa.text(f'UPDATE "{table}" SET "{field}"=CAST("{field}_units" AS REAL)/10000.0'))
            # Original binary floats are recovered exactly on an untouched copy.
            originals = connection.execute(sa.text(
                "SELECT row_id,original_value,rounded_units FROM money_migration_audit WHERE table_name=:table AND column_name=:field"
            ), {"table": table, "field": field}).all()
            for row_id, original, units in originals:
                connection.execute(sa.text(
                    f'UPDATE "{table}" SET "{field}"=:original WHERE id=:id AND "{field}_units"=:units'
                ), {"original": float(original), "id": row_id, "units": units})
            connection.execute(sa.text(f'ALTER TABLE "{table}" DROP COLUMN "{field}_units"'))
    connection.execute(sa.text('ALTER TABLE "users" DROP COLUMN "reserved_units"'))
    connection.execute(sa.text('ALTER TABLE "partners" DROP COLUMN "reserved_units"'))
    op.drop_table("money_operations")
    op.drop_table("money_migration_audit")
