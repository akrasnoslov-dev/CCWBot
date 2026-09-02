"""set the Market Heartbeat default to six hours

Revision ID: 0027_market_heartbeat_defaults
Revises: 0026_growth_analytics
Create Date: 2026-09-01
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0027_market_heartbeat_defaults"
down_revision: str | None = "0026_growth_analytics"
branch_labels: str | None = None
depends_on: str | None = None

PREVIOUS_ALERT_FREQUENCY_COMMENT = "User's selected minimum interval between alert deliveries."
MARKET_HEARTBEAT_FREQUENCY_COMMENT = (
    "User's selected Market Heartbeat delivery interval in seconds."
)


def _has_alert_frequency_column() -> bool:
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        return False
    return "alert_frequency_seconds" in {
        column["name"] for column in inspector.get_columns("users")
    }


def _set_default(default: str, *, comment: str, existing_comment: str) -> None:
    if not _has_alert_frequency_column():
        return
    kwargs = {
        "existing_type": sa.Integer(),
        "server_default": default,
        "existing_nullable": False,
    }
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("alert_frequency_seconds", **kwargs)
        return
    kwargs["comment"] = comment
    kwargs["existing_comment"] = existing_comment
    op.alter_column("users", "alert_frequency_seconds", **kwargs)


def upgrade() -> None:
    _set_default(
        "21600",
        comment=MARKET_HEARTBEAT_FREQUENCY_COMMENT,
        existing_comment=PREVIOUS_ALERT_FREQUENCY_COMMENT,
    )


def downgrade() -> None:
    _set_default(
        "14400",
        comment=PREVIOUS_ALERT_FREQUENCY_COMMENT,
        existing_comment=MARKET_HEARTBEAT_FREQUENCY_COMMENT,
    )
