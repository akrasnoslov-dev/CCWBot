"""migrate TON symbol rows to GRAM

Revision ID: 0024_gram_symbol
Revises: 0023_alert_outcome_decisions
Create Date: 2026-06-29

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0024_gram_symbol"
down_revision: str | None = "0023_alert_outcome_decisions"
branch_labels: str | None = None
depends_on: str | None = None


LOWER_SYMBOL_TABLES = ("user_coin_subscriptions", "user_symbol_alert_state")
UPPER_SYMBOL_TABLES = (
    "price_state",
    "price_snapshots",
    "market_events",
    "event_ai_analyses",
    "alerts",
    "alert_delivery_outcomes",
    "market_heartbeats",
    "llm_usage_logs",
)


def _newest_timestamp(left: str, right: str) -> str:
    return f"""
        CASE
            WHEN {left} IS NULL THEN {right}
            WHEN {right} IS NULL THEN {left}
            WHEN {right} > {left} THEN {right}
            ELSE {left}
        END
    """


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _has_table_and_symbol(tables: set[str], table_name: str) -> bool:
    return table_name in tables and "symbol" in _column_names(table_name)


def upgrade() -> None:
    tables = _table_names()
    if _has_table_and_symbol(tables, "user_coin_subscriptions"):
        _merge_user_coin_subscriptions()
    if _has_table_and_symbol(tables, "user_symbol_alert_state"):
        _merge_user_symbol_alert_state()
    if _has_table_and_symbol(tables, "price_state"):
        _merge_price_state()

    for table_name in UPPER_SYMBOL_TABLES:
        if table_name == "price_state":
            continue
        if _has_table_and_symbol(tables, table_name):
            op.execute(
                sa.text(f"UPDATE {table_name} SET symbol = 'GRAM' WHERE symbol = 'TON'")
            )


def downgrade() -> None:
    tables = _table_names()
    for table_name in UPPER_SYMBOL_TABLES:
        if _has_table_and_symbol(tables, table_name):
            op.execute(
                sa.text(f"UPDATE {table_name} SET symbol = 'TON' WHERE symbol = 'GRAM'")
            )
    for table_name in LOWER_SYMBOL_TABLES:
        if _has_table_and_symbol(tables, table_name):
            op.execute(sa.text(f"UPDATE {table_name} SET symbol = 'ton' WHERE symbol = 'gram'"))


def _merge_user_coin_subscriptions() -> None:
    op.execute(
        sa.text(
            """
            UPDATE user_coin_subscriptions AS gram
            SET
                is_enabled = gram.is_enabled OR ton.is_enabled,
                updated_at = CASE
                    WHEN ton.updated_at > gram.updated_at THEN ton.updated_at
                    ELSE gram.updated_at
                END
            FROM user_coin_subscriptions AS ton
            WHERE gram.user_id = ton.user_id
              AND gram.symbol = 'gram'
              AND ton.symbol = 'ton'
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM user_coin_subscriptions
            WHERE symbol = 'ton'
              AND EXISTS (
                  SELECT 1
                  FROM user_coin_subscriptions AS gram
                  WHERE gram.user_id = user_coin_subscriptions.user_id
                    AND gram.symbol = 'gram'
              )
            """
        )
    )
    op.execute(
        sa.text("UPDATE user_coin_subscriptions SET symbol = 'gram' WHERE symbol = 'ton'")
    )


def _merge_user_symbol_alert_state() -> None:
    op.execute(
        sa.text(
            """
            UPDATE user_symbol_alert_state AS gram
            SET
                last_market_update_time = """
            + _newest_timestamp(
                "gram.last_market_update_time",
                "ton.last_market_update_time",
            )
            + """,
                last_important_alert_time = """
            + _newest_timestamp(
                "gram.last_important_alert_time",
                "ton.last_important_alert_time",
            )
            + """,
                last_critical_alert_time = """
            + _newest_timestamp(
                "gram.last_critical_alert_time",
                "ton.last_critical_alert_time",
            )
            + """,
                last_notification_type = coalesce(
                    ton.last_notification_type,
                    gram.last_notification_type
                ),
                last_notification_severity = coalesce(
                    ton.last_notification_severity,
                    gram.last_notification_severity
                ),
                last_notification_direction = coalesce(
                    ton.last_notification_direction,
                    gram.last_notification_direction
                ),
                last_cumulative_movement_percent = coalesce(
                    ton.last_cumulative_movement_percent,
                    gram.last_cumulative_movement_percent
                ),
                updated_at = """
            + _newest_timestamp("gram.updated_at", "ton.updated_at")
            + """
            FROM user_symbol_alert_state AS ton
            WHERE gram.user_id = ton.user_id
              AND gram.symbol = 'gram'
              AND ton.symbol = 'ton'
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM user_symbol_alert_state
            WHERE symbol = 'ton'
              AND EXISTS (
                  SELECT 1
                  FROM user_symbol_alert_state AS gram
                  WHERE gram.user_id = user_symbol_alert_state.user_id
                    AND gram.symbol = 'gram'
              )
            """
        )
    )
    op.execute(sa.text("UPDATE user_symbol_alert_state SET symbol = 'gram' WHERE symbol = 'ton'"))


def _merge_price_state() -> None:
    op.execute(
        sa.text(
            """
            UPDATE price_state AS gram
            SET
                last_price = CASE
                    WHEN ton.last_checked_at > gram.last_checked_at THEN ton.last_price
                    ELSE gram.last_price
                END,
                last_24h_change = CASE
                    WHEN ton.last_checked_at > gram.last_checked_at THEN ton.last_24h_change
                    ELSE gram.last_24h_change
                END,
                last_checked_at = """
            + _newest_timestamp("gram.last_checked_at", "ton.last_checked_at")
            + """,
                last_alert_at = """
            + _newest_timestamp("gram.last_alert_at", "ton.last_alert_at")
            + """,
                updated_at = """
            + _newest_timestamp("gram.updated_at", "ton.updated_at")
            + """
            FROM price_state AS ton
            WHERE gram.symbol = 'GRAM'
              AND ton.symbol = 'TON'
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM price_state
            WHERE symbol = 'TON'
              AND EXISTS (
                  SELECT 1
                  FROM price_state AS gram
                  WHERE gram.symbol = 'GRAM'
              )
            """
        )
    )
    op.execute(sa.text("UPDATE price_state SET symbol = 'GRAM' WHERE symbol = 'TON'"))
