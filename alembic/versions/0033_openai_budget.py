"""Add durable OpenAI monthly budget reservations."""

import sqlalchemy as sa

from alembic import op

revision = "0033_openai_budget"
down_revision = "0032_alert_sent_at"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "openai_budget_reservations",
        sa.Column(
            "id", sa.String(length=36), nullable=False, comment="Opaque reservation identifier."
        ),
        sa.Column(
            "month_start",
            sa.Date(),
            nullable=False,
            comment="UTC calendar month owning this charge.",
        ),
        sa.Column(
            "model",
            sa.String(length=255),
            nullable=False,
            comment="OpenAI model authorized for this reservation.",
        ),
        sa.Column(
            "call_type",
            sa.String(length=64),
            nullable=False,
            comment="Feature family requesting the paid fallback.",
        ),
        sa.Column(
            "reserved_usd",
            sa.Numeric(18, 10),
            nullable=False,
            comment="Conservative maximum authorized before HTTP.",
        ),
        sa.Column(
            "input_rate_usd_per_million",
            sa.Numeric(18, 10),
            nullable=False,
            comment="Verified input-token price used for admission.",
        ),
        sa.Column(
            "output_rate_usd_per_million",
            sa.Numeric(18, 10),
            nullable=False,
            comment="Verified output-token price used for admission.",
        ),
        sa.Column(
            "actual_usd",
            sa.Numeric(18, 10),
            nullable=True,
            comment="Provider-usage charge when safely known.",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            comment="reserved, settled, conservative, or cap_breach.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the reservation was authorized.",
        ),
        sa.Column(
            "settled_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When known usage was reconciled.",
        ),
        sa.CheckConstraint("reserved_usd >= 0", name="ck_openai_budget_reserved_nonnegative"),
        sa.CheckConstraint(
            "actual_usd IS NULL OR actual_usd >= 0", name="ck_openai_budget_actual_nonnegative"
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Durable conservative reservations and reconciled charges for CCWBot OpenAI calls.",
    )
    op.create_index(
        "ix_openai_budget_month_created",
        "openai_budget_reservations",
        ["month_start", "created_at"],
    )


def downgrade():
    op.drop_index("ix_openai_budget_month_created", table_name="openai_budget_reservations")
    op.drop_table("openai_budget_reservations")
