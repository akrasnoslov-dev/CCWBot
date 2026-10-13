"""Record successful automatic delivery time independently of reservation time."""

import sqlalchemy as sa

from alembic import op

revision = "0032_alert_sent_at"
down_revision = "0031_onboarding_customize_event"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column(
            "users",
            "alert_frequency_seconds",
            comment="Deprecated heartbeat interval preference; ignored by automatic delivery.",
        )
    op.add_column(
        "alerts",
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When Telegram successfully accepted this delivery, after any retries.",
        ),
    )
    # Delivered outcomes supply real completion evidence. Legacy heartbeats have
    # none; start a conservative rollout window rather than trust reservation time.
    op.execute(
        sa.text("""
        UPDATE alerts SET sent_at = COALESCE(
            (SELECT MAX(o.created_at) FROM alert_delivery_outcomes o
             WHERE o.alert_id = alerts.id AND o.status = 'delivered'),
            CURRENT_TIMESTAMP
        ) WHERE status = 'sent'
    """)
    )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column(
            "users",
            "alert_frequency_seconds",
            comment="User's selected Market Heartbeat delivery interval in seconds.",
        )
    op.drop_column("alerts", "sent_at")
