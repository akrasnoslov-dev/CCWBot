"""add growth analytics and onboarding state

Revision ID: 0026_growth_analytics
Revises: 0025_llm_operation_correlation
Create Date: 2026-09-01
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0026_growth_analytics"
down_revision: str | None = "0025_llm_operation_correlation"
branch_labels: str | None = None
depends_on: str | None = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return _has_table(table_name) and any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def upgrade() -> None:
    if _has_table("users") and not _has_column("users", "onboarding_completed_at"):
        op.add_column(
            "users",
            sa.Column(
                "onboarding_completed_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="When this user completed the current first-time onboarding flow.",
            ),
        )
        op.execute(
            sa.text(
                "UPDATE users SET onboarding_completed_at = created_at "
                "WHERE onboarding_completed_at IS NULL"
            )
        )

    if not _has_table("user_acquisition_attributions"):
        op.create_table(
            "user_acquisition_attributions",
            sa.Column("id", sa.Integer(), nullable=False, comment="Internal attribution row id."),
            sa.Column(
                "user_id",
                sa.Integer(),
                nullable=False,
                comment="Internal user associated with this attribution.",
            ),
            sa.Column(
                "source",
                sa.String(length=32),
                nullable=False,
                comment="Allowlisted acquisition source from a validated deep link.",
            ),
            sa.Column(
                "campaign",
                sa.String(length=32),
                nullable=True,
                comment="Bounded campaign code from a validated deep link.",
            ),
            sa.Column(
                "creative",
                sa.String(length=32),
                nullable=True,
                comment="Bounded creative code from a validated deep link.",
            ),
            sa.Column(
                "referrer_code",
                sa.String(length=32),
                nullable=True,
                comment="Bounded opaque referrer code when a deep link supplies one.",
            ),
            sa.Column(
                "captured_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="When first-touch attribution was captured.",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_user_acquisition_attributions_user_id"),
            comment="First-touch acquisition attribution captured from validated bot deep links.",
        )
        op.create_index(
            "ix_user_acquisition_attributions_user_id",
            "user_acquisition_attributions",
            ["user_id"],
        )
        op.create_index(
            "ix_user_acquisition_attribution_source_campaign",
            "user_acquisition_attributions",
            ["source", "campaign"],
        )

    if not _has_table("acquisition_links"):
        op.create_table(
            "acquisition_links",
            sa.Column(
                "id",
                sa.Integer(),
                nullable=False,
                comment="Internal acquisition link row id.",
            ),
            sa.Column(
                "link_code",
                sa.String(length=48),
                nullable=False,
                comment="Opaque Telegram-safe deep-link code without user data.",
            ),
            sa.Column(
                "source",
                sa.String(length=32),
                nullable=False,
                comment="Allowlisted acquisition source configured by an operator.",
            ),
            sa.Column(
                "campaign",
                sa.String(length=32),
                nullable=True,
                comment="Bounded campaign code configured by an operator.",
            ),
            sa.Column(
                "creative",
                sa.String(length=32),
                nullable=True,
                comment="Bounded creative code configured by an operator.",
            ),
            sa.Column(
                "referrer_code",
                sa.String(length=32),
                nullable=True,
                comment="Bounded opaque referrer code configured by an operator.",
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
                comment="Whether this acquisition link may still be attributed.",
            ),
            sa.Column(
                "expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Optional time after which this link is ignored.",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="When this acquisition link was configured.",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("link_code", name="uq_acquisition_links_link_code"),
            comment="Operator-managed opaque deep links resolved to allowlisted acquisition data.",
        )
        op.create_index("ix_acquisition_links_link_code", "acquisition_links", ["link_code"])
        op.create_index(
            "ix_acquisition_links_active_expires",
            "acquisition_links",
            ["is_active", "expires_at"],
        )

    if not _has_table("product_events"):
        op.create_table(
            "product_events",
            sa.Column("id", sa.Integer(), nullable=False, comment="Internal product event row id."),
            sa.Column(
                "user_id",
                sa.Integer(),
                nullable=False,
                comment="Internal user who performed this product action.",
            ),
            sa.Column(
                "event_name",
                sa.String(length=64),
                nullable=False,
                comment="Allowlisted product funnel event name.",
            ),
            sa.Column(
                "event_key",
                sa.String(length=128),
                nullable=True,
                comment="Opaque bounded idempotency key for retryable lifecycle events.",
            ),
            sa.Column(
                "symbol",
                sa.String(length=32),
                nullable=True,
                comment="Selected lowercase supported coin when this event concerns one coin.",
            ),
            sa.Column(
                "selected_coin_count",
                sa.Integer(),
                nullable=True,
                comment="Selected supported-coin count when the event changes a watchlist.",
            ),
            sa.Column(
                "payment_id",
                sa.Integer(),
                nullable=True,
                comment="Internal payment linked to a successful conversion.",
            ),
            sa.Column(
                "occurred_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="When the product action occurred.",
            ),
            sa.CheckConstraint(
                "event_name IN ('bot_started', 'onboarding_started', 'coin_interest_selected', "
                "'onboarding_completed', 'instant_brief_viewed', 'watchlist_updated', "
                "'trial_offered', 'trial_started', 'trial_expired', 'paywall_viewed', "
                "'checkout_started', 'payment_succeeded', 'premium_value_delivered')",
                name="ck_product_events_event_name",
            ),
            sa.CheckConstraint(
                "symbol IS NULL OR symbol = lower(symbol)", name="ck_product_events_symbol_lower"
            ),
            sa.CheckConstraint(
                "selected_coin_count IS NULL OR selected_coin_count BETWEEN 0 AND 4",
                name="ck_product_events_selected_coin_count",
            ),
            sa.CheckConstraint(
                "payment_id IS NULL OR event_name = 'payment_succeeded'",
                name="ck_product_events_payment_event",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id", "event_name", "event_key", name="uq_product_events_user_event_key"
            ),
            sa.UniqueConstraint("payment_id", name="uq_product_events_payment_id"),
            comment="Allowlisted durable product funnel events linked to internal users.",
        )
        op.create_index("ix_product_events_user_id", "product_events", ["user_id"])
        op.create_index("ix_product_events_event_name", "product_events", ["event_name"])
        op.create_index("ix_product_events_occurred_at", "product_events", ["occurred_at"])
        op.create_index(
            "ix_product_events_user_occurred_at", "product_events", ["user_id", "occurred_at"]
        )
        op.create_index(
            "ix_product_events_name_occurred_at", "product_events", ["event_name", "occurred_at"]
        )


def downgrade() -> None:
    if _has_table("product_events"):
        for index_name in (
            "ix_product_events_name_occurred_at",
            "ix_product_events_user_occurred_at",
            "ix_product_events_occurred_at",
            "ix_product_events_event_name",
            "ix_product_events_user_id",
        ):
            op.drop_index(index_name, table_name="product_events")
        op.drop_table("product_events")
    if _has_table("acquisition_links"):
        op.drop_index("ix_acquisition_links_active_expires", table_name="acquisition_links")
        op.drop_index("ix_acquisition_links_link_code", table_name="acquisition_links")
        op.drop_table("acquisition_links")
    if _has_table("user_acquisition_attributions"):
        op.drop_index(
            "ix_user_acquisition_attribution_source_campaign",
            table_name="user_acquisition_attributions",
        )
        op.drop_index(
            "ix_user_acquisition_attributions_user_id",
            table_name="user_acquisition_attributions",
        )
        op.drop_table("user_acquisition_attributions")
    if _has_table("users") and _has_column("users", "onboarding_completed_at"):
        op.drop_column("users", "onboarding_completed_at")
