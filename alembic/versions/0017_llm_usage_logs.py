"""llm usage logs

Revision ID: 0017_llm_usage_logs
Revises: 0016_market_heartbeats
Create Date: 2026-05-21

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0017_llm_usage_logs"
down_revision: str | None = "0016_market_heartbeats"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True, comment="Internal LLM usage row id."),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this LLM call ran.",
        ),
        sa.Column(
            "provider",
            sa.String(64),
            nullable=False,
            comment="LLM provider that handled the request.",
        ),
        sa.Column(
            "model",
            sa.String(255),
            nullable=False,
            comment="Exact LLM model requested for this call.",
        ),
        sa.Column(
            "call_type",
            sa.String(64),
            nullable=False,
            comment="Purpose of the LLM call such as event_analysis.",
        ),
        sa.Column(
            "symbol",
            sa.String(32),
            nullable=True,
            comment="Uppercase coin symbol for this call.",
        ),
        sa.Column(
            "status",
            sa.String(64),
            nullable=False,
            comment="Final call status such as success or rate_limit.",
        ),
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            nullable=True,
            comment="Prompt tokens reported by the provider.",
        ),
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=True,
            comment="Completion tokens reported by the provider.",
        ),
        sa.Column(
            "total_tokens",
            sa.Integer(),
            nullable=True,
            comment="Total tokens reported by the provider.",
        ),
        sa.Column(
            "input_chars",
            sa.Integer(),
            nullable=True,
            comment="Character count of messages sent to the provider.",
        ),
        sa.Column(
            "output_chars",
            sa.Integer(),
            nullable=True,
            comment="Character count of the provider response body.",
        ),
        sa.Column(
            "max_tokens",
            sa.Integer(),
            nullable=True,
            comment="Maximum completion tokens configured for the call.",
        ),
        sa.Column(
            "rate_limit_limit_requests",
            sa.String(128),
            nullable=True,
            comment="Provider request limit header value when available.",
        ),
        sa.Column(
            "rate_limit_remaining_requests",
            sa.String(128),
            nullable=True,
            comment="Provider remaining requests header when available.",
        ),
        sa.Column(
            "rate_limit_reset_requests",
            sa.String(128),
            nullable=True,
            comment="Provider request limit reset header when available.",
        ),
        sa.Column(
            "rate_limit_limit_tokens",
            sa.String(128),
            nullable=True,
            comment="Provider token limit header value when available.",
        ),
        sa.Column(
            "rate_limit_remaining_tokens",
            sa.String(128),
            nullable=True,
            comment="Provider remaining tokens header when available.",
        ),
        sa.Column(
            "rate_limit_reset_tokens",
            sa.String(128),
            nullable=True,
            comment="Provider token limit reset header when available.",
        ),
        sa.Column(
            "retry_after",
            sa.String(128),
            nullable=True,
            comment="Provider retry-after header when rate limited.",
        ),
        sa.Column(
            "error_reason",
            sa.String(64),
            nullable=True,
            comment="Normalized safe error reason for failed calls.",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Sanitized provider or parser error message.",
        ),
        comment=(
            "Per-call LLM usage and rate-limit telemetry captured without extra provider calls."
        ),
    )
    op.create_index("ix_llm_usage_logs_created_at", "llm_usage_logs", ["created_at"])
    op.create_index("ix_llm_usage_logs_model", "llm_usage_logs", ["model"])
    op.create_index("ix_llm_usage_logs_call_type", "llm_usage_logs", ["call_type"])
    op.create_index("ix_llm_usage_logs_symbol", "llm_usage_logs", ["symbol"])
    op.create_index("ix_llm_usage_logs_status", "llm_usage_logs", ["status"])
    op.create_index(
        "ix_llm_usage_logs_call_type_model_status",
        "llm_usage_logs",
        ["call_type", "model", "status"],
    )
    op.create_index(
        "ix_llm_usage_logs_symbol_created_at",
        "llm_usage_logs",
        ["symbol", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_usage_logs_symbol_created_at", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_call_type_model_status", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_status", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_symbol", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_call_type", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_model", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_created_at", table_name="llm_usage_logs")
    op.drop_table("llm_usage_logs")
