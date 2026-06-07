"""coin topic routes

Revision ID: 0021_coin_topic_routes
Revises: 0020_news_items
Create Date: 2026-06-07 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_coin_topic_routes"
down_revision: str | None = "0020_news_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "coin_topic_routes",
        sa.Column("id", sa.Integer(), primary_key=True, comment="Internal route row id."),
        sa.Column(
            "symbol",
            sa.String(length=32),
            nullable=False,
            comment="Lowercase coin symbol routed to this forum topic.",
        ),
        sa.Column(
            "chat_id",
            sa.BigInteger(),
            nullable=False,
            comment="Telegram group chat id that owns the forum topic.",
        ),
        sa.Column(
            "message_thread_id",
            sa.BigInteger(),
            nullable=False,
            comment="Telegram forum topic message thread id for this coin.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this topic route was created.",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this topic route was last updated.",
        ),
        sa.CheckConstraint("symbol = lower(symbol)", name="ck_coin_topic_routes_symbol_lower"),
        sa.UniqueConstraint("symbol", name="uq_coin_topic_routes_symbol"),
        comment="Admin-configured Telegram forum topic destinations for coin alerts.",
    )
    op.create_index("ix_coin_topic_routes_symbol", "coin_topic_routes", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_coin_topic_routes_symbol", table_name="coin_topic_routes")
    op.drop_table("coin_topic_routes")
