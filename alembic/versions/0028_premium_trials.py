"""add durable one-time Premium trials

Revision ID: 0028_premium_trials
Revises: 0027_market_heartbeat_defaults
Create Date: 2026-09-01
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0028_premium_trials"
down_revision: str | None = "0027_market_heartbeat_defaults"
branch_labels: str | None = None
depends_on: str | None = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("user_premium_trials"):
        return
    op.create_table(
        "user_premium_trials",
        sa.Column("id", sa.Integer(), nullable=False, comment="Internal Premium trial row id."),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
            comment="User who used this one-time Premium trial.",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the seven-day Premium trial started.",
        ),
        sa.Column(
            "active_until",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Exclusive end time for this Premium trial.",
        ),
        sa.Column(
            "expired_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When trial expiry was processed exactly once.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this trial row was created.",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this trial row was last updated.",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_premium_trials_user_id"),
        comment="One-time Premium trial history and expiry state for each user.",
    )
    op.create_index("ix_user_premium_trials_user_id", "user_premium_trials", ["user_id"])
    op.create_index("ix_user_premium_trials_active_until", "user_premium_trials", ["active_until"])


def downgrade() -> None:
    if _has_table("user_premium_trials"):
        op.drop_index("ix_user_premium_trials_active_until", table_name="user_premium_trials")
        op.drop_index("ix_user_premium_trials_user_id", table_name="user_premium_trials")
        op.drop_table("user_premium_trials")
