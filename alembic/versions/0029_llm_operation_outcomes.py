"""add generic logical LLM operation outcomes

Revision ID: 0029_llm_operation_outcomes
Revises: 0028_premium_trials
Create Date: 2026-09-09
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0029_llm_operation_outcomes"
down_revision: str | None = "0028_premium_trials"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "llm_operation_outcomes",
        sa.Column(
            "id", sa.Integer(), nullable=False, comment="Internal logical LLM outcome row id."
        ),
        sa.Column(
            "llm_operation_id",
            sa.String(length=36),
            nullable=False,
            comment="Opaque backend correlation id shared by the operation's provider attempts.",
        ),
        sa.Column(
            "call_type",
            sa.String(length=64),
            nullable=False,
            comment="Logical LLM feature type such as news_intelligence.",
        ),
        sa.Column(
            "symbol",
            sa.String(length=32),
            nullable=True,
            comment="Optional uppercase market symbol for the operation.",
        ),
        sa.Column(
            "status",
            sa.String(length=64),
            nullable=False,
            comment="Sanitized terminal logical status such as success or failed.",
        ),
        sa.Column(
            "error_reason",
            sa.String(length=64),
            nullable=True,
            comment="Sanitized terminal failure category, if any.",
        ),
        sa.Column(
            "provider",
            sa.String(length=64),
            nullable=True,
            comment="Provider that produced the terminal outcome.",
        ),
        sa.Column(
            "model",
            sa.String(length=255),
            nullable=True,
            comment="Model that produced the terminal outcome.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the logical LLM operation finished.",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "llm_operation_id", name="uq_llm_operation_outcomes_operation_id"
        ),
        comment=(
            "Sanitized final outcomes for logical LLM operations without a dedicated "
            "feature table."
        ),
    )
    op.create_index(
        "ix_llm_operation_outcomes_call_type_created_at",
        "llm_operation_outcomes",
        ["call_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_llm_operation_outcomes_call_type_created_at",
        table_name="llm_operation_outcomes",
    )
    op.drop_table("llm_operation_outcomes")
