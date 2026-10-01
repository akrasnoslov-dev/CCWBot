"""allow onboarding customize analytics event

Revision ID: 0031_onboarding_customize_event
Revises: 0030_event_alert_policy_cleanup
Create Date: 2026-10-01
"""

from __future__ import annotations

from alembic import op

revision = "0031_onboarding_customize_event"
down_revision = "0030_event_alert_policy_cleanup"
branch_labels = None
depends_on = None


OLD_EVENT_NAME_CHECK = (
    "event_name IN ('bot_started', 'onboarding_started', 'coin_interest_selected', "
    "'onboarding_completed', 'instant_brief_viewed', 'watchlist_updated', "
    "'trial_offered', 'trial_started', 'trial_expired', 'paywall_viewed', "
    "'checkout_started', 'payment_succeeded', 'premium_value_delivered')"
)

NEW_EVENT_NAME_CHECK = (
    "event_name IN ('bot_started', 'onboarding_started', 'onboarding_customize_opened', "
    "'coin_interest_selected', 'onboarding_completed', 'instant_brief_viewed', "
    "'watchlist_updated', 'trial_offered', 'trial_started', 'trial_expired', "
    "'paywall_viewed', 'checkout_started', 'payment_succeeded', 'premium_value_delivered')"
)


def _replace_event_name_check(expression: str) -> None:
    with op.batch_alter_table("product_events") as batch_op:
        batch_op.drop_constraint("ck_product_events_event_name", type_="check")
        batch_op.create_check_constraint("ck_product_events_event_name", expression)


def upgrade() -> None:
    _replace_event_name_check(NEW_EVENT_NAME_CHECK)


def downgrade() -> None:
    _replace_event_name_check(OLD_EVENT_NAME_CHECK)
