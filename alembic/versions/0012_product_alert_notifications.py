"""product alert notification fields

Revision ID: 0012_product_alert_notifications
Revises: 0011_blocked_user_delivery_state
Create Date: 2026-05-18

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0012_product_alert_notifications"
down_revision: str | None = "0011_blocked_user_delivery_state"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("price_snapshots") as batch_op:
        batch_op.add_column(
            sa.Column(
                "change_7d",
                sa.Float(),
                nullable=True,
                comment="7 day percentage change captured with this snapshot.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "source",
                sa.String(length=64),
                nullable=False,
                server_default="coingecko",
                comment="Market data provider for this snapshot.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="When this snapshot row was created.",
            )
        )

    op.execute("UPDATE price_snapshots SET created_at = checked_at WHERE created_at IS NULL")
    with op.batch_alter_table("price_snapshots") as batch_op:
        batch_op.alter_column("created_at", nullable=False)

    with op.batch_alter_table("alerts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "trigger_source",
                sa.String(length=64),
                nullable=True,
                comment="Machine-readable signal source for this alert.",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.drop_column("trigger_source")

    with op.batch_alter_table("price_snapshots") as batch_op:
        batch_op.drop_column("created_at")
        batch_op.drop_column("source")
        batch_op.drop_column("change_7d")
