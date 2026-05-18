"""user symbol alert state

Revision ID: 0013_user_symbol_alert_state
Revises: 0012_product_alert_notifications
Create Date: 2026-05-18

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0013_user_symbol_alert_state"
down_revision: str | None = "0012_product_alert_notifications"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "user_symbol_alert_state",
        sa.Column("id", sa.Integer(), primary_key=True, comment="Internal state row id."),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            comment="User this per-symbol alert state belongs to.",
        ),
        sa.Column(
            "symbol",
            sa.String(length=32),
            nullable=False,
            comment="Lowercase coin symbol for this alert state.",
        ),
        sa.Column(
            "last_market_update_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When a Market Update was last successfully sent for this user and symbol.",
        ),
        sa.Column(
            "last_important_alert_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When an Important Alert was last successfully sent for this user and symbol.",
        ),
        sa.Column(
            "last_critical_alert_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When a Critical Alert was last successfully sent for this user and symbol.",
        ),
        sa.Column(
            "last_notification_type",
            sa.String(length=64),
            nullable=True,
            comment="Latest user-facing notification type sent for this user and symbol.",
        ),
        sa.Column(
            "last_notification_severity",
            sa.String(length=32),
            nullable=True,
            comment="Latest normalized notification severity for this user and symbol.",
        ),
        sa.Column(
            "last_notification_direction",
            sa.String(length=32),
            nullable=True,
            comment="Latest notification direction for this user and symbol.",
        ),
        sa.Column(
            "last_cumulative_movement_percent",
            sa.Float(),
            nullable=True,
            comment="Latest cumulative movement percent stored for suppression decisions.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="When this state row was created.",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="When this state row was last updated.",
        ),
        sa.UniqueConstraint(
            "user_id",
            "symbol",
            name="uq_user_symbol_alert_state_user_symbol",
        ),
        sa.CheckConstraint(
            "symbol = lower(symbol)",
            name="ck_user_symbol_alert_state_symbol_lower",
        ),
        comment="Per-user per-symbol alert timestamps used by automatic monitoring.",
    )
    op.create_index(
        "ix_user_symbol_alert_state_user_id",
        "user_symbol_alert_state",
        ["user_id"],
    )
    op.create_index(
        "ix_user_symbol_alert_state_symbol",
        "user_symbol_alert_state",
        ["symbol"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_symbol_alert_state_symbol", table_name="user_symbol_alert_state")
    op.drop_index("ix_user_symbol_alert_state_user_id", table_name="user_symbol_alert_state")
    op.drop_table("user_symbol_alert_state")
