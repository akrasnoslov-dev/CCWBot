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


def _set_default(default: str) -> None:
    kwargs = {
        "existing_type": sa.Integer(),
        "server_default": default,
        "existing_nullable": False,
    }
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("alert_frequency_seconds", **kwargs)
        return
    op.alter_column("users", "alert_frequency_seconds", **kwargs)


def upgrade() -> None:
    _set_default("21600")


def downgrade() -> None:
    _set_default("14400")
