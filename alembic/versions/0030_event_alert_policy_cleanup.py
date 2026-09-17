"""remove Event Alert movement policy state and preserve full price precision

Revision ID: 0030_event_alert_policy_cleanup
Revises: 0029_llm_operation_outcomes
Create Date: 2026-09-17
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0030_event_alert_policy_cleanup"
down_revision = "0029_llm_operation_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        for name in (
            "btc_alert_threshold_percent",
            "major_movement_threshold_percent",
            "alt_movement_threshold_percent",
            "major_24h_medium_threshold_percent",
            "major_24h_high_threshold_percent",
            "alt_24h_medium_threshold_percent",
            "alt_24h_high_threshold_percent",
        ):
            batch_op.drop_column(name)
    with op.batch_alter_table("user_settings") as batch_op:
        batch_op.drop_column("price_move_alert_percent")
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.drop_column("thresholds_used")
    with op.batch_alter_table("price_state") as batch_op:
        batch_op.alter_column(
            "last_price",
            existing_type=sa.Float(),
            type_=sa.Numeric(38, 18),
            postgresql_using="last_price::numeric(38,18)",
        )
    with op.batch_alter_table("price_snapshots") as batch_op:
        batch_op.alter_column(
            "price",
            existing_type=sa.Float(),
            type_=sa.Numeric(38, 18),
            postgresql_using="price::numeric(38,18)",
        )
    with op.batch_alter_table("market_events") as batch_op:
        batch_op.alter_column(
            "price",
            existing_type=sa.Float(),
            type_=sa.Numeric(38, 18),
            postgresql_using="price::numeric(38,18)",
        )
        batch_op.alter_column(
            "previous_price",
            existing_type=sa.Float(),
            type_=sa.Numeric(38, 18),
            postgresql_using="previous_price::numeric(38,18)",
        )
    with op.batch_alter_table("event_ai_analyses") as batch_op:
        batch_op.add_column(
            sa.Column(
                "context_fingerprint",
                sa.String(128),
                nullable=True,
                comment="Hash of the exact semantic Event Analysis input used for pre-LLM reuse.",
            )
        )
        batch_op.create_index("ix_event_ai_analyses_context_fingerprint", ["context_fingerprint"])


def downgrade() -> None:
    with op.batch_alter_table("event_ai_analyses") as batch_op:
        batch_op.drop_index("ix_event_ai_analyses_context_fingerprint")
        batch_op.drop_column("context_fingerprint")
    with op.batch_alter_table("market_events") as batch_op:
        batch_op.alter_column("previous_price", existing_type=sa.Numeric(38, 18), type_=sa.Float())
        batch_op.alter_column("price", existing_type=sa.Numeric(38, 18), type_=sa.Float())
    with op.batch_alter_table("price_snapshots") as batch_op:
        batch_op.alter_column("price", existing_type=sa.Numeric(38, 18), type_=sa.Float())
    with op.batch_alter_table("price_state") as batch_op:
        batch_op.alter_column("last_price", existing_type=sa.Numeric(38, 18), type_=sa.Float())
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.add_column(sa.Column("thresholds_used", sa.Text(), nullable=True))
    with op.batch_alter_table("user_settings") as batch_op:
        batch_op.add_column(
            sa.Column("price_move_alert_percent", sa.Float(), nullable=False, server_default="2.0")
        )
    with op.batch_alter_table("app_settings") as batch_op:
        for name, default in (
            ("btc_alert_threshold_percent", "2.0"),
            ("major_movement_threshold_percent", "1.0"),
            ("alt_movement_threshold_percent", "2.0"),
            ("major_24h_medium_threshold_percent", "3.0"),
            ("major_24h_high_threshold_percent", "5.0"),
            ("alt_24h_medium_threshold_percent", "5.0"),
            ("alt_24h_high_threshold_percent", "8.0"),
        ):
            batch_op.add_column(sa.Column(name, sa.Float(), nullable=False, server_default=default))
