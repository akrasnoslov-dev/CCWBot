"""alert outcome decision observability

Revision ID: 0023_alert_outcome_decisions
Revises: 0022_unique_event_analysis
Create Date: 2026-06-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023_alert_outcome_decisions"
down_revision: str | None = "0022_unique_event_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "alert_delivery_outcomes",
        sa.Column(
            "decision_stage",
            sa.String(length=64),
            nullable=True,
            comment="Decision stage that produced this operator-facing outcome.",
        ),
    )
    op.add_column(
        "alert_delivery_outcomes",
        sa.Column(
            "decision_reason",
            sa.String(length=64),
            nullable=True,
            comment="Machine-readable event alert decision reason for operator reports.",
        ),
    )
    op.add_column(
        "alert_delivery_outcomes",
        sa.Column(
            "previous_alert_id",
            sa.Integer(),
            nullable=True,
            comment="Previous alert row considered for repeat or cooldown decisions.",
        ),
    )
    op.add_column(
        "alert_delivery_outcomes",
        sa.Column(
            "context_fingerprint",
            sa.String(length=128),
            nullable=True,
            comment="Safe hash of the sanitized decision context used for observability.",
        ),
    )
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_alert_delivery_outcomes_previous_alert_id_alerts",
            "alert_delivery_outcomes",
            "alerts",
            ["previous_alert_id"],
            ["id"],
        )
    op.create_index(
        "ix_alert_delivery_outcomes_decision_stage",
        "alert_delivery_outcomes",
        ["decision_stage"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_decision_reason",
        "alert_delivery_outcomes",
        ["decision_reason"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_previous_alert_id",
        "alert_delivery_outcomes",
        ["previous_alert_id"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_context_fingerprint",
        "alert_delivery_outcomes",
        ["context_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_alert_delivery_outcomes_context_fingerprint",
        table_name="alert_delivery_outcomes",
    )
    op.drop_index(
        "ix_alert_delivery_outcomes_previous_alert_id",
        table_name="alert_delivery_outcomes",
    )
    op.drop_index(
        "ix_alert_delivery_outcomes_decision_reason",
        table_name="alert_delivery_outcomes",
    )
    op.drop_index(
        "ix_alert_delivery_outcomes_decision_stage",
        table_name="alert_delivery_outcomes",
    )
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint(
            "fk_alert_delivery_outcomes_previous_alert_id_alerts",
            "alert_delivery_outcomes",
            type_="foreignkey",
        )
    op.drop_column("alert_delivery_outcomes", "context_fingerprint")
    op.drop_column("alert_delivery_outcomes", "previous_alert_id")
    op.drop_column("alert_delivery_outcomes", "decision_reason")
    op.drop_column("alert_delivery_outcomes", "decision_stage")
