"""alert delivery retries

Revision ID: 0014_alert_delivery_retries
Revises: 0013_user_symbol_alert_state
Create Date: 2026-05-19

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0014_alert_delivery_retries"
down_revision: str | None = "0013_user_symbol_alert_state"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "retry_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="Number of Telegram delivery attempts already made for this alert.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "last_error",
                sa.Text(),
                nullable=True,
                comment="Most recent Telegram delivery error for this alert.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "next_retry_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="When the next Telegram delivery retry is due, if retryable.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "final_failed_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="When Telegram delivery retries were exhausted or marked permanent.",
            )
        )
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.alter_column("retry_count", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.drop_column("final_failed_at")
        batch_op.drop_column("next_retry_at")
        batch_op.drop_column("last_error")
        batch_op.drop_column("retry_count")
