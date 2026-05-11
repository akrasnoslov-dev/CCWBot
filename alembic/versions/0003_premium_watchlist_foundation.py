"""premium watchlist foundation

Revision ID: 0003_premium_watchlist_foundation
Revises: 0002_async_sqlalchemy_runtime
Create Date: 2026-05-11 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_premium_watchlist_foundation"
down_revision: str | Sequence[str] | None = "0002_async_sqlalchemy_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    tables = _table_names()
    if "users" in tables and "alert_frequency_seconds" not in _column_names("users"):
        op.add_column(
            "users",
            sa.Column(
                "alert_frequency_seconds",
                sa.Integer(),
                nullable=False,
                server_default="14400",
            ),
        )

    if "user_coin_subscriptions" not in tables:
        op.create_table(
            "user_coin_subscriptions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("symbol", sa.String(length=32), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "symbol = lower(symbol)",
                name="ck_user_coin_subscriptions_symbol_lower",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "symbol",
                name="uq_user_coin_subscriptions_user_symbol",
            ),
        )
        op.create_index(
            op.f("ix_user_coin_subscriptions_user_id"),
            "user_coin_subscriptions",
            ["user_id"],
        )
        op.create_index(
            op.f("ix_user_coin_subscriptions_symbol"),
            "user_coin_subscriptions",
            ["symbol"],
        )

    if "user_premium_subscriptions" not in tables:
        op.create_table(
            "user_premium_subscriptions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("plan", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("active_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("provider", sa.String(length=64), nullable=True),
            sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
            sa.Column("last_payment_id", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_user_premium_subscriptions_user_id"),
        )
        op.create_index(
            op.f("ix_user_premium_subscriptions_user_id"),
            "user_premium_subscriptions",
            ["user_id"],
        )
        op.create_index(
            op.f("ix_user_premium_subscriptions_status"),
            "user_premium_subscriptions",
            ["status"],
        )
        op.create_index(
            op.f("ix_user_premium_subscriptions_active_until"),
            "user_premium_subscriptions",
            ["active_until"],
        )


def downgrade() -> None:
    tables = _table_names()
    if "user_premium_subscriptions" in tables:
        op.drop_table("user_premium_subscriptions")
    if "user_coin_subscriptions" in tables:
        op.drop_table("user_coin_subscriptions")
    if "users" in tables and "alert_frequency_seconds" in _column_names("users"):
        op.drop_column("users", "alert_frequency_seconds")

