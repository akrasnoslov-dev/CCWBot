"""alert decision context and price snapshots

Revision ID: 0010_alert_decision_context
Revises: 0009_error_file_logging_toggle
Create Date: 2026-05-16

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0010_alert_decision_context"
down_revision: str | None = "0009_error_file_logging_toggle"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "major_movement_threshold_percent",
                sa.Float(),
                nullable=False,
                server_default="1.0",
                comment="Admin-controlled movement percent threshold for BTC and ETH alerts.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "alt_movement_threshold_percent",
                sa.Float(),
                nullable=False,
                server_default="2.0",
                comment=(
                    "Admin-controlled movement percent threshold for non-BTC and "
                    "non-ETH alerts."
                ),
            )
        )
        batch_op.add_column(
            sa.Column(
                "major_24h_medium_threshold_percent",
                sa.Float(),
                nullable=False,
                server_default="3.0",
                comment="Admin-controlled 24 hour medium trend threshold for BTC and ETH alerts.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "major_24h_high_threshold_percent",
                sa.Float(),
                nullable=False,
                server_default="5.0",
                comment="Admin-controlled 24 hour high trend threshold for BTC and ETH alerts.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "alt_24h_medium_threshold_percent",
                sa.Float(),
                nullable=False,
                server_default="5.0",
                comment="Admin-controlled 24 hour medium trend threshold for altcoin alerts.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "alt_24h_high_threshold_percent",
                sa.Float(),
                nullable=False,
                server_default="8.0",
                comment="Admin-controlled 24 hour high trend threshold for altcoin alerts.",
            )
        )

    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, comment="Internal price snapshot row id."),
        sa.Column(
            "symbol",
            sa.String(length=32),
            nullable=False,
            index=True,
            comment="Uppercase coin symbol for this market snapshot.",
        ),
        sa.Column(
            "price",
            sa.Float(),
            nullable=False,
            comment="Market price captured at this snapshot time.",
        ),
        sa.Column(
            "change_24h",
            sa.Float(),
            nullable=True,
            comment="24 hour percentage change captured with this snapshot.",
        ),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
            comment="When this market snapshot was captured.",
        ),
        comment="Historical market snapshots used for user-frequency alert windows.",
    )
    op.create_index(
        "ix_price_snapshots_symbol_checked_at",
        "price_snapshots",
        ["symbol", "checked_at"],
    )

    with op.batch_alter_table("alerts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "trigger_reason",
                sa.Text(),
                nullable=True,
                comment="Concise reason that triggered this delivered alert.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "numeric_context",
                sa.Text(),
                nullable=True,
                comment="JSON numeric market context used for this alert decision.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "thresholds_used",
                sa.Text(),
                nullable=True,
                comment="JSON alert thresholds used for this alert decision.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "llm_severity",
                sa.String(length=32),
                nullable=True,
                comment="Severity selected or accepted for this alert.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "llm_reasoning_summary",
                sa.Text(),
                nullable=True,
                comment="Short reasoning summary from the LLM or backend fallback.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "fallback_mode",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
                comment=(
                    "Whether this delivery used a deterministic fallback instead of "
                    "AI analysis."
                ),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.drop_column("fallback_mode")
        batch_op.drop_column("llm_reasoning_summary")
        batch_op.drop_column("llm_severity")
        batch_op.drop_column("thresholds_used")
        batch_op.drop_column("numeric_context")
        batch_op.drop_column("trigger_reason")

    op.drop_index("ix_price_snapshots_symbol_checked_at", table_name="price_snapshots")
    op.drop_table("price_snapshots")

    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.drop_column("alt_24h_high_threshold_percent")
        batch_op.drop_column("alt_24h_medium_threshold_percent")
        batch_op.drop_column("major_24h_high_threshold_percent")
        batch_op.drop_column("major_24h_medium_threshold_percent")
        batch_op.drop_column("alt_movement_threshold_percent")
        batch_op.drop_column("major_movement_threshold_percent")
