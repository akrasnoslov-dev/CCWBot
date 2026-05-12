"""payment recurring metadata

Revision ID: 0006_payment_recurring_metadata
Revises: 0005_telegram_stars_payments
Create Date: 2026-05-12

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0006_payment_recurring_metadata"
down_revision: str | None = "0005_telegram_stars_payments"
branch_labels: str | None = None
depends_on: str | None = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("payments")
    if not columns:
        return
    if "is_recurring" not in columns:
        op.add_column("payments", sa.Column("is_recurring", sa.Boolean(), nullable=True))
    if "is_first_recurring" not in columns:
        op.add_column("payments", sa.Column("is_first_recurring", sa.Boolean(), nullable=True))
    if "subscription_expiration_date" not in columns:
        op.add_column(
            "payments",
            sa.Column("subscription_expiration_date", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    columns = _column_names("payments")
    if "subscription_expiration_date" in columns:
        op.drop_column("payments", "subscription_expiration_date")
    if "is_first_recurring" in columns:
        op.drop_column("payments", "is_first_recurring")
    if "is_recurring" in columns:
        op.drop_column("payments", "is_recurring")
