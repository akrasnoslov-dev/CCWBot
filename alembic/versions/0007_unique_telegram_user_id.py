"""unique telegram user id

Revision ID: 0007_unique_telegram_user_id
Revises: 0006_payment_recurring_metadata
Create Date: 2026-05-12

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0007_unique_telegram_user_id"
down_revision: str | None = "0006_payment_recurring_metadata"
branch_labels: str | None = None
depends_on: str | None = None


def _constraint_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    duplicate_user_ids = bind.execute(
        sa.text(
            """
            SELECT telegram_user_id
            FROM users
            GROUP BY telegram_user_id
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate_user_ids is not None:
        raise RuntimeError(
            "Cannot add uq_users_telegram_user_id while duplicate users exist. "
            "Merge duplicate users before running this migration."
        )

    if "uq_users_telegram_user_id" not in _constraint_names("users"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.create_unique_constraint(
                "uq_users_telegram_user_id",
                ["telegram_user_id"],
            )


def downgrade() -> None:
    if "uq_users_telegram_user_id" in _constraint_names("users"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_constraint("uq_users_telegram_user_id", type_="unique")
