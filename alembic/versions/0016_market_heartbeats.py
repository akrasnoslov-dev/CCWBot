"""market heartbeats

Revision ID: 0016_market_heartbeats
Revises: 0015_llm_event_analysis
Create Date: 2026-05-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_market_heartbeats"
down_revision: str | None = "0015_llm_event_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_heartbeats",
        sa.Column("id", sa.Integer(), nullable=False, comment="Internal market heartbeat row id."),
        sa.Column(
            "symbol",
            sa.String(length=32),
            nullable=False,
            comment="Uppercase coin symbol this heartbeat describes.",
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this heartbeat generation ran.",
        ),
        sa.Column(
            "raw_input_json",
            sa.Text(),
            nullable=True,
            comment="Raw JSON input payload sent to the LLM.",
        ),
        sa.Column(
            "raw_output_json",
            sa.Text(),
            nullable=True,
            comment="Raw JSON or text output returned by the LLM.",
        ),
        sa.Column(
            "title",
            sa.Text(),
            nullable=True,
            comment="LLM heartbeat title for Telegram delivery.",
        ),
        sa.Column(
            "message_body",
            sa.Text(),
            nullable=True,
            comment="LLM heartbeat body for Telegram delivery.",
        ),
        sa.Column(
            "related_news_ids",
            sa.Text(),
            nullable=True,
            comment="JSON array of candidate news ids selected by the LLM.",
        ),
        sa.Column(
            "possible_action",
            sa.Text(),
            nullable=True,
            comment="Cautious non-prescriptive possible action from the LLM.",
        ),
        sa.Column(
            "confidence",
            sa.String(length=32),
            nullable=True,
            comment="LLM heartbeat confidence: low, medium, or high.",
        ),
        sa.Column(
            "status",
            sa.String(length=64),
            nullable=False,
            comment="Heartbeat generation state such as completed or failed.",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Failure detail when heartbeat generation fails.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this heartbeat row was created.",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Cached AI market heartbeat updates generated independently of delivery.",
    )
    op.create_index("ix_market_heartbeats_symbol", "market_heartbeats", ["symbol"])
    op.create_index("ix_market_heartbeats_generated_at", "market_heartbeats", ["generated_at"])
    op.create_index("ix_market_heartbeats_status", "market_heartbeats", ["status"])
    op.create_index(
        "ix_market_heartbeats_symbol_generated_at",
        "market_heartbeats",
        ["symbol", "generated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_market_heartbeats_symbol_generated_at", table_name="market_heartbeats")
    op.drop_index("ix_market_heartbeats_status", table_name="market_heartbeats")
    op.drop_index("ix_market_heartbeats_generated_at", table_name="market_heartbeats")
    op.drop_index("ix_market_heartbeats_symbol", table_name="market_heartbeats")
    op.drop_table("market_heartbeats")
