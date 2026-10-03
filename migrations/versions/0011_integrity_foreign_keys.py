"""0011: отсутствовавшие внешние ключи этапов 10–11.

Revision: 0011
Revises: 0010
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # user_id не nullable: тихо удалять пользовательские тикеты нельзя. Проверяем
    # инвариант до любых DDL/изменений, чтобы fail-fast не оставлял частичный upgrade.
    orphan_ticket_count = int(
        op.get_bind()
        .execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM support_tickets
                WHERE NOT EXISTS (
                    SELECT 1 FROM users WHERE users.id = support_tickets.user_id
                )
                """
            )
        )
        .scalar_one()
    )
    if orphan_ticket_count:
        raise RuntimeError(
            "0011: cannot add support_tickets.user_id foreign key: "
            f"found {orphan_ticket_count} orphan ticket(s); restore or quarantine them first"
        )

    with op.batch_alter_table("partner_payouts") as batch:
        batch.alter_column(
            "requisites",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=False,
        )

    # 0008 добавила эти поля без FK, поэтому перед включением
    # ограничений нормализуем возможные сиротские ссылки из старой БД.
    op.execute(
        """
        UPDATE users
        SET partner_id = NULL
        WHERE partner_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM partners WHERE partners.id = users.partner_id
          )
        """
    )
    op.execute(
        """
        UPDATE users
        SET partner_link_id = NULL
        WHERE partner_link_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM partner_links
              WHERE partner_links.id = users.partner_link_id
          )
        """
    )
    op.execute(
        """
        UPDATE sponsors
        SET partner_id = NULL
        WHERE partner_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM partners WHERE partners.id = sponsors.partner_id
          )
        """
    )
    op.execute(
        """
        UPDATE support_tickets
        SET review_id = NULL
        WHERE review_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM reviews WHERE reviews.id = support_tickets.review_id
          )
        """
    )
    with op.batch_alter_table("users") as batch:
        batch.create_foreign_key(
            "fk_users_partner_id_partners",
            "partners",
            ["partner_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_users_partner_link_id_partner_links",
            "partner_links",
            ["partner_link_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("sponsors") as batch:
        batch.create_foreign_key(
            "fk_sponsors_partner_id_partners",
            "partners",
            ["partner_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("support_tickets") as batch:
        batch.create_foreign_key(
            "fk_support_tickets_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_foreign_key(
            "fk_support_tickets_review_id_reviews",
            "reviews",
            ["review_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("support_tickets") as batch:
        batch.drop_constraint(
            "fk_support_tickets_review_id_reviews", type_="foreignkey"
        )
        batch.drop_constraint(
            "fk_support_tickets_user_id_users", type_="foreignkey"
        )
    with op.batch_alter_table("sponsors") as batch:
        batch.drop_constraint(
            "fk_sponsors_partner_id_partners", type_="foreignkey"
        )
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint(
            "fk_users_partner_link_id_partner_links", type_="foreignkey"
        )
        batch.drop_constraint("fk_users_partner_id_partners", type_="foreignkey")
    with op.batch_alter_table("partner_payouts") as batch:
        batch.alter_column(
            "requisites",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=False,
        )
