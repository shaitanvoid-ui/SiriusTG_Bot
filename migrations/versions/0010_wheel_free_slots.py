"""0010: атомарные дневные слоты колеса.

Revision: 0010
Revises: 0009
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "partner_rewarded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # До появления флага CPA считался выданным по факту прохождения gate.
    # Помечаем исторические атрибуции, чтобы recheck не начислил CPA повторно.
    op.execute(
        """
        UPDATE users
        SET partner_rewarded = 1
        WHERE partner_id IS NOT NULL
          AND subs_passed_at IS NOT NULL
        """
    )
    op.add_column("wheel_spins", sa.Column("free_slot", sa.Integer(), nullable=True))
    # Сохраняем историю: существующим бесплатным вращениям назначаем
    # последовательные слоты внутри (user, day), платные остаются NULL.
    op.execute(
        """
        UPDATE wheel_spins
        SET free_slot = (
            SELECT COUNT(*)
            FROM wheel_spins AS older
            WHERE older.user_id = wheel_spins.user_id
              AND older.day = wheel_spins.day
              AND older.is_free = 1
              AND older.id <= wheel_spins.id
        )
        WHERE is_free = 1
        """
    )
    with op.batch_alter_table("wheel_spins") as batch:
        batch.create_unique_constraint(
            "uq_wheel_free_slot", ["user_id", "day", "free_slot"]
        )


def downgrade() -> None:
    with op.batch_alter_table("wheel_spins") as batch:
        batch.drop_constraint("uq_wheel_free_slot", type_="unique")
        batch.drop_column("free_slot")
    op.drop_column("users", "partner_rewarded")
