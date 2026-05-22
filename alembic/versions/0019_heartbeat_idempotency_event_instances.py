"""heartbeat delivery idempotency and event instances

Revision ID: 0019_heartbeat_idempotency_event_instances
Revises: 0018_market_reports
Create Date: 2026-05-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_heartbeat_idempotency_event_instances"
down_revision: str | None = "0018_market_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "market_heartbeat_id",
                sa.Integer(),
                sa.ForeignKey("market_heartbeats.id", name="fk_alerts_market_heartbeat_id"),
                nullable=True,
                comment="Market heartbeat this delivery belongs to when the alert is a heartbeat.",
            )
        )

    with op.batch_alter_table("market_events") as batch_op:
        batch_op.add_column(
            sa.Column(
                "event_instance_key",
                sa.String(length=255),
                nullable=True,
                comment="Stable idempotency key for this concrete market event occurrence.",
            )
        )

    op.execute(
        sa.text(
            "UPDATE market_events "
            "SET event_instance_key = event_key "
            "WHERE event_instance_key IS NULL"
        )
    )

    with op.batch_alter_table("market_events") as batch_op:
        batch_op.alter_column(
            "event_instance_key",
            existing_type=sa.String(length=255),
            nullable=False,
        )

    op.drop_index("ix_market_events_event_key", table_name="market_events")
    if _is_sqlite():
        with op.batch_alter_table("market_events") as batch_op:
            batch_op.drop_constraint("uq_market_events_event_key", type_="unique")
    else:
        op.drop_constraint("uq_market_events_event_key", "market_events", type_="unique")
    op.create_index("ix_market_events_event_key", "market_events", ["event_key"])

    op.create_index(
        "ix_market_events_event_instance_key",
        "market_events",
        ["event_instance_key"],
        unique=True,
    )
    if not _is_sqlite():
        op.create_unique_constraint(
            "uq_market_events_event_instance_key",
            "market_events",
            ["event_instance_key"],
        )
    op.create_index(
        "uq_alerts_user_symbol_type_heartbeat",
        "alerts",
        ["user_id", "symbol", "alert_type", "market_heartbeat_id"],
        unique=True,
        postgresql_where=sa.text("market_heartbeat_id IS NOT NULL"),
        sqlite_where=sa.text("market_heartbeat_id IS NOT NULL"),
    )
    if not _is_sqlite():
        op.alter_column(
            "event_ai_analyses",
            "possible_action",
            existing_type=sa.Text(),
            comment="Possible action text returned by the LLM.",
        )
        op.alter_column(
            "market_heartbeats",
            "possible_action",
            existing_type=sa.Text(),
            comment="Possible action text returned by the LLM.",
        )


def downgrade() -> None:
    op.drop_index("uq_alerts_user_symbol_type_heartbeat", table_name="alerts")
    if not _is_sqlite():
        op.drop_constraint(
            "uq_market_events_event_instance_key",
            "market_events",
            type_="unique",
        )
    op.drop_index("ix_market_events_event_instance_key", table_name="market_events")
    op.drop_index("ix_market_events_event_key", table_name="market_events")
    op.create_index("ix_market_events_event_key", "market_events", ["event_key"], unique=True)
    if not _is_sqlite():
        op.create_unique_constraint(
            "uq_market_events_event_key",
            "market_events",
            ["event_key"],
        )
    with op.batch_alter_table("market_events") as batch_op:
        batch_op.drop_column("event_instance_key")
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.drop_column("market_heartbeat_id")
