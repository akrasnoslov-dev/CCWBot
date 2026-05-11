"""telegram stars payments

Revision ID: 0005_telegram_stars_payments
Revises: 0004_multicoin_delivery
Create Date: 2026-05-11

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0005_telegram_stars_payments"
down_revision: str | None = "0004_multicoin_delivery"
branch_labels: str | None = None
depends_on: str | None = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    if "payments" in _table_names():
        return
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=False),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("telegram_payment_charge_id", sa.String(length=255), nullable=True),
        sa.Column("provider_payment_charge_id", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_payment_id",
            name="uq_payments_provider_payment_id",
        ),
    )
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False)
    op.create_index(op.f("ix_payments_provider"), "payments", ["provider"], unique=False)
    op.create_index(op.f("ix_payments_currency"), "payments", ["currency"], unique=False)
    op.create_index(op.f("ix_payments_payload"), "payments", ["payload"], unique=False)
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)


def downgrade() -> None:
    if "payments" in _table_names():
        op.drop_table("payments")
