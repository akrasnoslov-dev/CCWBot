"""llm event analysis

Revision ID: 0015_llm_event_analysis
Revises: 0014_alert_delivery_retries
Create Date: 2026-05-20

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0015_llm_event_analysis"
down_revision: str | None = "0014_alert_delivery_retries"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("event_ai_analyses") as batch_op:
        batch_op.alter_column("market_event_id", nullable=True)
        batch_op.add_column(
            sa.Column(
                "analysis_id",
                sa.String(length=128),
                nullable=True,
                comment="External stable id for this LLM analysis attempt.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "symbol",
                sa.String(length=32),
                nullable=True,
                comment="Uppercase coin symbol analyzed by this LLM attempt.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "analysis_type",
                sa.String(length=64),
                nullable=True,
                comment="Analysis purpose such as event_analysis.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "raw_input_json",
                sa.Text(),
                nullable=True,
                comment="Raw JSON input payload sent to the LLM.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "raw_output_json",
                sa.Text(),
                nullable=True,
                comment="Raw JSON or text output returned by the LLM.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "parsed_result_json",
                sa.Text(),
                nullable=True,
                comment="Validated JSON result fields from the LLM response.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "should_alert",
                sa.Boolean(),
                nullable=True,
                comment="Whether the LLM decided this analysis should alert users.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "event_key",
                sa.String(length=255),
                nullable=True,
                comment="LLM event key when should_alert is true.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "title",
                sa.Text(),
                nullable=True,
                comment="LLM alert title for an event alert.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "message_body",
                sa.Text(),
                nullable=True,
                comment="LLM alert body for an event alert.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "related_news_ids",
                sa.Text(),
                nullable=True,
                comment="JSON array of candidate news ids selected by the LLM.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "possible_action",
                sa.Text(),
                nullable=True,
                comment="Possible action text returned by the LLM.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "urgency",
                sa.String(length=32),
                nullable=True,
                comment="LLM event urgency: low, normal, or high.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "confidence",
                sa.String(length=32),
                nullable=True,
                comment="LLM confidence: low, medium, or high.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "reason_for_no_alert",
                sa.Text(),
                nullable=True,
                comment="LLM explanation when no event alert should be sent.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "error_reason",
                sa.String(length=64),
                nullable=True,
                comment="Normalized LLM failure reason for admin status.",
            )
        )

    op.execute(
        """
        UPDATE event_ai_analyses
        SET analysis_type = 'legacy_alert_analysis'
        WHERE analysis_type IS NULL
        """
    )
    op.create_index(
        "ix_event_ai_analyses_analysis_id",
        "event_ai_analyses",
        ["analysis_id"],
        unique=True,
    )
    op.create_index("ix_event_ai_analyses_symbol", "event_ai_analyses", ["symbol"])
    op.create_index("ix_event_ai_analyses_analysis_type", "event_ai_analyses", ["analysis_type"])
    op.create_index("ix_event_ai_analyses_event_key", "event_ai_analyses", ["event_key"])


def downgrade() -> None:
    op.drop_index("ix_event_ai_analyses_event_key", table_name="event_ai_analyses")
    op.drop_index("ix_event_ai_analyses_analysis_type", table_name="event_ai_analyses")
    op.drop_index("ix_event_ai_analyses_symbol", table_name="event_ai_analyses")
    op.drop_index("ix_event_ai_analyses_analysis_id", table_name="event_ai_analyses")
    with op.batch_alter_table("event_ai_analyses") as batch_op:
        batch_op.drop_column("error_reason")
        batch_op.drop_column("reason_for_no_alert")
        batch_op.drop_column("confidence")
        batch_op.drop_column("urgency")
        batch_op.drop_column("possible_action")
        batch_op.drop_column("related_news_ids")
        batch_op.drop_column("message_body")
        batch_op.drop_column("title")
        batch_op.drop_column("event_key")
        batch_op.drop_column("should_alert")
        batch_op.drop_column("parsed_result_json")
        batch_op.drop_column("raw_output_json")
        batch_op.drop_column("raw_input_json")
        batch_op.drop_column("analysis_type")
        batch_op.drop_column("symbol")
        batch_op.drop_column("analysis_id")
        batch_op.alter_column("market_event_id", nullable=False)
