"""blocked user delivery state

Revision ID: 0011_blocked_user_delivery_state
Revises: 0010_alert_decision_context
Create Date: 2026-05-18

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0011_blocked_user_delivery_state"
down_revision: str | None = "0010_alert_decision_context"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "bot_blocked",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
                comment="Whether Telegram reported that this user blocked the bot.",
            )
        )
        batch_op.add_column(
            sa.Column(
                "blocked_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="When Telegram first reported that this user blocked the bot.",
            )
        )

    op.execute(
        sa.text(
            """
            UPDATE users
            SET
                is_active = false,
                bot_blocked = true,
                blocked_at = COALESCE(
                    blocked_at,
                    (
                        SELECT MIN(alerts.created_at)
                        FROM alerts
                        WHERE alerts.error_message IS NOT NULL
                          AND lower(alerts.error_message) LIKE '%bot was blocked by the user%'
                          AND (
                              alerts.user_id = users.id
                              OR alerts.sent_to_chat_id = users.telegram_chat_id
                          )
                    )
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE EXISTS (
                SELECT 1
                FROM alerts
                WHERE alerts.error_message IS NOT NULL
                  AND lower(alerts.error_message) LIKE '%bot was blocked by the user%'
                  AND (
                      alerts.user_id = users.id
                      OR alerts.sent_to_chat_id = users.telegram_chat_id
                  )
            )
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("blocked_at")
        batch_op.drop_column("bot_blocked")
