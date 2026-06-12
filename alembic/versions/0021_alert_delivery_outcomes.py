"""alert delivery outcomes

Revision ID: 0021_alert_delivery_outcomes
Revises: 0020_news_items
Create Date: 2026-06-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_alert_delivery_outcomes"
down_revision: str | None = "0020_news_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alert_delivery_outcomes",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
            comment="Internal alert delivery outcome row id.",
        ),
        sa.Column(
            "symbol",
            sa.String(length=32),
            nullable=False,
            comment="Uppercase coin symbol for this alert outcome.",
        ),
        sa.Column(
            "alert_type",
            sa.String(length=64),
            nullable=False,
            comment="Alert category this outcome belongs to.",
        ),
        sa.Column(
            "market_event_id",
            sa.Integer(),
            nullable=True,
            comment="Market event this outcome explains, when one exists.",
        ),
        sa.Column(
            "event_ai_analysis_id",
            sa.Integer(),
            nullable=True,
            comment="AI analysis this outcome explains, when one exists.",
        ),
        sa.Column(
            "alert_id",
            sa.Integer(),
            nullable=True,
            comment="Delivery row this outcome summarizes, when Telegram delivery was attempted.",
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=True,
            comment="Recipient user considered for this alert outcome, if recipient-specific.",
        ),
        sa.Column(
            "sent_to_chat_id",
            sa.BigInteger(),
            nullable=True,
            comment="Telegram chat id considered for this outcome, when available.",
        ),
        sa.Column(
            "status",
            sa.String(length=64),
            nullable=False,
            comment="Queryable outcome status such as delivered, filtered, suppressed, or failed.",
        ),
        sa.Column(
            "reason_code",
            sa.String(length=64),
            nullable=False,
            comment="Machine-readable reason code for this outcome.",
        ),
        sa.Column(
            "recipient_considered",
            sa.Boolean(),
            nullable=False,
            comment="Whether a concrete recipient was evaluated for this alert.",
        ),
        sa.Column(
            "recipient_eligible",
            sa.Boolean(),
            nullable=True,
            comment="Whether the considered recipient was eligible for Telegram delivery.",
        ),
        sa.Column(
            "trigger_source",
            sa.String(length=64),
            nullable=True,
            comment="Machine-readable signal source for this outcome.",
        ),
        sa.Column(
            "event_instance_key",
            sa.String(length=255),
            nullable=True,
            comment="Stable idempotency key for the market event.",
        ),
        sa.Column(
            "semantic_family",
            sa.String(length=128),
            nullable=True,
            comment="Canonical semantic family used for suppression.",
        ),
        sa.Column(
            "detail",
            sa.Text(),
            nullable=True,
            comment="Sanitized secondary diagnostic detail for operators.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this outcome row was created.",
        ),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.ForeignKeyConstraint(["event_ai_analysis_id"], ["event_ai_analyses.id"]),
        sa.ForeignKeyConstraint(["market_event_id"], ["market_events.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment=(
            "Queryable alert decision outcome for a market event, recipient, or "
            "event-level non-delivery reason."
        ),
    )
    op.create_index(
        "ix_alert_delivery_outcomes_alert_id",
        "alert_delivery_outcomes",
        ["alert_id"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_alert_type",
        "alert_delivery_outcomes",
        ["alert_type"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_event_ai_analysis_id",
        "alert_delivery_outcomes",
        ["event_ai_analysis_id"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_event_status",
        "alert_delivery_outcomes",
        ["market_event_id", "status"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_market_event_id",
        "alert_delivery_outcomes",
        ["market_event_id"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_reason_code",
        "alert_delivery_outcomes",
        ["reason_code"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_sent_to_chat_id",
        "alert_delivery_outcomes",
        ["sent_to_chat_id"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_status",
        "alert_delivery_outcomes",
        ["status"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_symbol",
        "alert_delivery_outcomes",
        ["symbol"],
    )
    op.create_index(
        "ix_alert_delivery_outcomes_user_id",
        "alert_delivery_outcomes",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_alert_delivery_outcomes_user_id", table_name="alert_delivery_outcomes")
    op.drop_index("ix_alert_delivery_outcomes_symbol", table_name="alert_delivery_outcomes")
    op.drop_index("ix_alert_delivery_outcomes_status", table_name="alert_delivery_outcomes")
    op.drop_index(
        "ix_alert_delivery_outcomes_sent_to_chat_id",
        table_name="alert_delivery_outcomes",
    )
    op.drop_index("ix_alert_delivery_outcomes_reason_code", table_name="alert_delivery_outcomes")
    op.drop_index(
        "ix_alert_delivery_outcomes_market_event_id",
        table_name="alert_delivery_outcomes",
    )
    op.drop_index("ix_alert_delivery_outcomes_event_status", table_name="alert_delivery_outcomes")
    op.drop_index(
        "ix_alert_delivery_outcomes_event_ai_analysis_id",
        table_name="alert_delivery_outcomes",
    )
    op.drop_index("ix_alert_delivery_outcomes_alert_type", table_name="alert_delivery_outcomes")
    op.drop_index("ix_alert_delivery_outcomes_alert_id", table_name="alert_delivery_outcomes")
    op.drop_table("alert_delivery_outcomes")
