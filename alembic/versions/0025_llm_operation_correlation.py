"""add durable logical LLM operation correlation

Revision ID: 0025_llm_operation_correlation
Revises: 0024_gram_symbol
Create Date: 2026-08-30
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0025_llm_operation_correlation"
down_revision: str | None = "0024_gram_symbol"
branch_labels: str | None = None
depends_on: str | None = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return _has_table(table_name) and any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def _has_index(table_name: str, index_name: str) -> bool:
    return _has_table(table_name) and any(
        index["name"] == index_name
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    )


def upgrade() -> None:
    for table_name in ("event_ai_analyses", "market_heartbeats", "market_reports"):
        if not _has_table(table_name):
            continue
        if not _has_column(table_name, "llm_operation_id"):
            op.add_column(
                table_name,
                sa.Column(
                    "llm_operation_id",
                    sa.String(length=36),
                    nullable=True,
                    comment="Opaque backend correlation id for the logical LLM operation.",
                ),
            )
        index_name = f"ix_{table_name}_llm_operation_id"
        if not _has_index(table_name, index_name):
            op.create_index(index_name, table_name, ["llm_operation_id"])

    if _has_table("llm_usage_logs"):
        if not _has_column("llm_usage_logs", "llm_operation_id"):
            op.add_column(
                "llm_usage_logs",
                sa.Column(
                    "llm_operation_id",
                    sa.String(length=36),
                    nullable=True,
                    comment=(
                        "Opaque backend correlation id shared by provider attempts in one "
                        "logical operation."
                    ),
                ),
            )
        if not _has_column("llm_usage_logs", "provider_request_id"):
            op.add_column(
                "llm_usage_logs",
                sa.Column(
                    "provider_request_id",
                    sa.String(length=128),
                    nullable=True,
                    comment="Allowlisted opaque provider request id when the response exposes one.",
                ),
            )
        if not _has_index("llm_usage_logs", "ix_llm_usage_logs_operation_id"):
            op.create_index(
                "ix_llm_usage_logs_operation_id", "llm_usage_logs", ["llm_operation_id"]
            )


def downgrade() -> None:
    if _has_index("llm_usage_logs", "ix_llm_usage_logs_operation_id"):
        op.drop_index("ix_llm_usage_logs_operation_id", table_name="llm_usage_logs")
    if _has_column("llm_usage_logs", "provider_request_id"):
        op.drop_column("llm_usage_logs", "provider_request_id")
    if _has_column("llm_usage_logs", "llm_operation_id"):
        op.drop_column("llm_usage_logs", "llm_operation_id")
    for table_name in ("market_reports", "market_heartbeats", "event_ai_analyses"):
        index_name = f"ix_{table_name}_llm_operation_id"
        if _has_index(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
        if _has_column(table_name, "llm_operation_id"):
            op.drop_column(table_name, "llm_operation_id")
