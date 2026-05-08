"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-08 00:00:00.000000
"""

from collections.abc import Sequence
from datetime import datetime, timezone

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_telegram_user_id"), "users", ["telegram_user_id"])
    op.create_index(op.f("ix_users_telegram_chat_id"), "users", ["telegram_chat_id"])


def _create_user_settings() -> None:
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("price_move_alert_percent", sa.Float(), nullable=False),
        sa.Column("automatic_check_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_settings_user_id"), "user_settings", ["user_id"])


def _create_app_settings() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("btc_alert_threshold_percent", sa.Float(), nullable=False),
        sa.Column("automatic_check_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_price_state() -> None:
    op.create_table(
        "price_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("last_price", sa.Float(), nullable=False),
        sa.Column("last_24h_change", sa.Float(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_alert_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_price_state_symbol"), "price_state", ["symbol"])


def _create_seen_news() -> None:
    op.create_table(
        "seen_news",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("news_key", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("link", sa.String(length=2000), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_seen_news_news_key"), "seen_news", ["news_key"], unique=True)


def _create_alerts() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sent_to_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("market_event_id", sa.Integer(), nullable=True),
        sa.Column("event_ai_analysis_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_symbol"), "alerts", ["symbol"])
    op.create_index(op.f("ix_alerts_alert_type"), "alerts", ["alert_type"])
    op.create_index(op.f("ix_alerts_sent_to_chat_id"), "alerts", ["sent_to_chat_id"])


def _create_market_events() -> None:
    op.create_table(
        "market_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_key", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("previous_price", sa.Float(), nullable=True),
        sa.Column("price_change_percent", sa.Float(), nullable=False),
        sa.Column("last_24h_change", sa.Float(), nullable=True),
        sa.Column("last_7d_change", sa.Float(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key", name="uq_market_events_event_key"),
    )
    op.create_index(op.f("ix_market_events_symbol"), "market_events", ["symbol"])
    op.create_index(op.f("ix_market_events_event_type"), "market_events", ["event_type"])
    op.create_index(op.f("ix_market_events_event_key"), "market_events", ["event_key"], unique=True)


def _create_event_ai_analyses() -> None:
    op.create_table(
        "event_ai_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("market_event_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("analysis_text", sa.Text(), nullable=True),
        sa.Column("plain_text", sa.Text(), nullable=True),
        sa.Column("html_text", sa.Text(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["market_event_id"], ["market_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "market_event_id",
            "input_hash",
            name="uq_event_ai_analyses_market_event_input_hash",
        ),
    )
    op.create_index(
        op.f("ix_event_ai_analyses_market_event_id"),
        "event_ai_analyses",
        ["market_event_id"],
    )
    op.create_index(op.f("ix_event_ai_analyses_input_hash"), "event_ai_analyses", ["input_hash"])
    op.create_index(op.f("ix_event_ai_analyses_status"), "event_ai_analyses", ["status"])


def _replace_legacy_app_settings() -> None:
    columns = _column_names("app_settings")
    if {"btc_alert_threshold_percent", "automatic_check_interval_seconds"}.issubset(columns):
        return
    if not {"setting_key", "setting_value"}.issubset(columns):
        raise RuntimeError(
            "app_settings exists but does not contain the current global settings columns."
        )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT setting_key, setting_value FROM app_settings "
            "WHERE setting_key IN ("
            "'btc_alert_threshold_percent', "
            "'automatic_check_interval_seconds'"
            ")"
        )
    ).mappings()
    values = {str(row["setting_key"]): str(row["setting_value"]) for row in rows}
    threshold = float(values.get("btc_alert_threshold_percent", "2"))
    interval = int(values.get("automatic_check_interval_seconds", "300"))

    op.drop_table("app_settings")
    _create_app_settings()
    app_settings = sa.table(
        "app_settings",
        sa.column("btc_alert_threshold_percent", sa.Float()),
        sa.column("automatic_check_interval_seconds", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        app_settings,
        [
            {
                "btc_alert_threshold_percent": threshold,
                "automatic_check_interval_seconds": interval,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )


def _add_missing_alert_delivery_columns() -> None:
    columns = _column_names("alerts")
    column_definitions = {
        "market_event_id": sa.Column("market_event_id", sa.Integer(), nullable=True),
        "event_ai_analysis_id": sa.Column("event_ai_analysis_id", sa.Integer(), nullable=True),
        "user_id": sa.Column("user_id", sa.Integer(), nullable=True),
        "status": sa.Column("status", sa.String(length=64), nullable=True),
        "error_message": sa.Column("error_message", sa.Text(), nullable=True),
    }
    for column_name, column in column_definitions.items():
        if column_name not in columns:
            op.add_column("alerts", column)


def upgrade() -> None:
    existing_tables = _table_names()

    if "users" not in existing_tables:
        _create_users()
    if "user_settings" not in existing_tables:
        _create_user_settings()
    if "app_settings" not in existing_tables:
        _create_app_settings()
    else:
        _replace_legacy_app_settings()
    if "price_state" not in existing_tables:
        _create_price_state()
    if "seen_news" not in existing_tables:
        _create_seen_news()
    if "alerts" not in existing_tables:
        _create_alerts()
    else:
        _add_missing_alert_delivery_columns()
    if "market_events" not in existing_tables:
        _create_market_events()
    if "event_ai_analyses" not in existing_tables:
        _create_event_ai_analyses()


def downgrade() -> None:
    for table_name in [
        "event_ai_analyses",
        "market_events",
        "alerts",
        "seen_news",
        "price_state",
        "app_settings",
        "user_settings",
        "users",
    ]:
        if table_name in _table_names():
            op.drop_table(table_name)
