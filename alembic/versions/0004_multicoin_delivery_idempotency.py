"""multicoin delivery idempotency

Revision ID: 0004_multicoin_delivery
Revises: 0003_premium_watchlist
Create Date: 2026-05-11

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0004_multicoin_delivery"
down_revision: str | None = "0003_premium_watchlist"
branch_labels: str | None = None
depends_on: str | None = None


def _unique_constraint_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name)}


def upgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM price_state "
            "WHERE id NOT IN (SELECT MIN(id) FROM price_state GROUP BY symbol)"
        )
    )
    constraints = _unique_constraint_names("price_state")
    if "uq_price_state_symbol" not in constraints:
        with op.batch_alter_table("price_state") as batch_op:
            batch_op.create_unique_constraint("uq_price_state_symbol", ["symbol"])

    op.execute(
        sa.text(
            "DELETE FROM alerts "
            "WHERE user_id IS NOT NULL "
            "AND market_event_id IS NOT NULL "
            "AND id NOT IN ("
            "SELECT COALESCE(MAX(CASE WHEN status = 'sent' THEN id END), MIN(id)) "
            "FROM alerts "
            "WHERE user_id IS NOT NULL "
            "AND market_event_id IS NOT NULL "
            "GROUP BY user_id, symbol, market_event_id"
            ")"
        )
    )
    constraints = _unique_constraint_names("alerts")
    if "uq_alerts_user_symbol_market_event" not in constraints:
        with op.batch_alter_table("alerts") as batch_op:
            batch_op.create_unique_constraint(
                "uq_alerts_user_symbol_market_event",
                ["user_id", "symbol", "market_event_id"],
            )


def downgrade() -> None:
    constraints = _unique_constraint_names("alerts")
    if "uq_alerts_user_symbol_market_event" in constraints:
        with op.batch_alter_table("alerts") as batch_op:
            batch_op.drop_constraint("uq_alerts_user_symbol_market_event", type_="unique")

    constraints = _unique_constraint_names("price_state")
    if "uq_price_state_symbol" in constraints:
        with op.batch_alter_table("price_state") as batch_op:
            batch_op.drop_constraint("uq_price_state_symbol", type_="unique")
