"""market reports cache

Revision ID: 0018_market_reports
Revises: 0017_llm_usage_logs
Create Date: 2026-05-21

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0018_market_reports"
down_revision: str | None = "0017_llm_usage_logs"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "market_reports",
        sa.Column("id", sa.Integer(), primary_key=True, comment="Internal market report row id."),
        sa.Column(
            "report_type",
            sa.String(length=32),
            nullable=False,
            comment="Report cadence, either daily or weekly.",
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this report generation ran.",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this cached report should be refreshed.",
        ),
        sa.Column(
            "status",
            sa.String(length=64),
            nullable=False,
            comment="Report generation state, either completed or failed.",
        ),
        sa.Column(
            "raw_input_json",
            sa.Text(),
            nullable=True,
            comment="Raw JSON input payload sent to the report LLM.",
        ),
        sa.Column(
            "raw_output_json",
            sa.Text(),
            nullable=True,
            comment="Raw JSON or text output returned by the report LLM.",
        ),
        sa.Column(
            "telegram_message",
            sa.Text(),
            nullable=True,
            comment="Sanitized Telegram report message when generation succeeded.",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Failure detail when report generation failed.",
        ),
        sa.Column(
            "provider",
            sa.String(length=64),
            nullable=True,
            comment="LLM provider used for this report generation.",
        ),
        sa.Column(
            "model",
            sa.String(length=255),
            nullable=True,
            comment="LLM model used for this report generation.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this report row was created.",
        ),
        sa.CheckConstraint(
            "report_type IN ('daily', 'weekly')",
            name="ck_market_reports_type",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_market_reports_status",
        ),
        comment="Cached AI market-wide reports generated independently of user requests.",
    )
    op.create_index(
        "ix_market_reports_type_generated_at",
        "market_reports",
        ["report_type", "generated_at"],
        unique=False,
    )
    op.create_index("ix_market_reports_report_type", "market_reports", ["report_type"])
    op.create_index("ix_market_reports_generated_at", "market_reports", ["generated_at"])
    op.create_index("ix_market_reports_expires_at", "market_reports", ["expires_at"])
    op.create_index("ix_market_reports_status", "market_reports", ["status"])


def downgrade() -> None:
    op.drop_index("ix_market_reports_status", table_name="market_reports")
    op.drop_index("ix_market_reports_expires_at", table_name="market_reports")
    op.drop_index("ix_market_reports_generated_at", table_name="market_reports")
    op.drop_index("ix_market_reports_report_type", table_name="market_reports")
    op.drop_index("ix_market_reports_type_generated_at", table_name="market_reports")
    op.drop_table("market_reports")
