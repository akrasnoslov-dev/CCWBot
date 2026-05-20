"""database comments

Revision ID: 0008_database_comments
Revises: 0007_unique_telegram_user_id
Create Date: 2026-05-13

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0008_database_comments"
down_revision: str | None = "0007_unique_telegram_user_id"
branch_labels: str | None = None
depends_on: str | None = None


TABLE_COMMENTS = {
    "users": "Telegram users known to the bot and their delivery profile.",
    "user_settings": "Legacy per-user alert settings retained for compatibility.",
    "user_coin_subscriptions": "Per-user watchlist choices for automatic coin alerts.",
    "user_premium_subscriptions": "Source of truth for each user's bot Premium entitlement.",
    "user_symbol_alert_state": (
        "Per-user per-symbol alert timestamps used by automatic monitoring."
    ),
    "payments": "Payment events processed for Premium entitlement activation.",
    "app_settings": "Global bot settings controlled by admins.",
    "price_state": "Latest stored market snapshot used to detect price movements.",
    "price_snapshots": "Historical market snapshots used for user-frequency alert windows.",
    "seen_news": "RSS/news items already processed for deduplication.",
    "alerts": "One delivery record per recipient for a market alert.",
    "market_events": "Deduplicated market movements that can trigger many deliveries.",
    "event_ai_analyses": "One reusable AI analysis for a market event and exact input payload.",
}

COLUMN_COMMENTS = {
    "users": {
        "id": "Internal user row id.",
        "telegram_user_id": "Telegram user id that identifies the person using the bot.",
        "telegram_chat_id": "Telegram chat id where the bot sends messages for this user.",
        "username": "Latest Telegram username seen for the user.",
        "first_name": "Latest Telegram first name seen for the user.",
        "role": "Bot authorization role such as user or admin.",
        "is_active": "Whether the user may receive automatic bot messages.",
        "bot_blocked": "Whether Telegram reported that this user blocked the bot.",
        "blocked_at": "When Telegram first reported that this user blocked the bot.",
        "alert_frequency_seconds": "User's selected minimum interval between alert deliveries.",
        "created_at": "When this user row was created.",
        "updated_at": "When this user row was last updated.",
    },
    "user_settings": {
        "id": "Internal settings row id.",
        "user_id": "User these legacy settings belong to.",
        "price_move_alert_percent": "Legacy per-user price movement threshold percent.",
        "automatic_check_interval_seconds": (
            "Legacy per-user automatic price check interval in seconds."
        ),
        "created_at": "When this settings row was created.",
        "updated_at": "When this settings row was last updated.",
    },
    "user_coin_subscriptions": {
        "id": "Internal watchlist row id.",
        "user_id": "User who owns this coin alert choice.",
        "symbol": "Lowercase coin symbol controlled by this watchlist row.",
        "is_enabled": "Whether automatic alerts are enabled for this coin.",
        "created_at": "When this watchlist row was created.",
        "updated_at": "When this watchlist row was last updated.",
    },
    "user_premium_subscriptions": {
        "id": "Internal Premium row id.",
        "user_id": "User whose Premium entitlement this records.",
        "plan": "Premium plan name granted to the user.",
        "status": "Current Premium lifecycle status for operator visibility.",
        "active_until": (
            "Source of truth for bot Premium access; active only while this is in the future."
        ),
        "started_at": "When Premium access first started.",
        "cancelled_at": "When Premium access was revoked or ended.",
        "provider": "Payment or grant source that last set this entitlement.",
        "provider_subscription_id": "Provider subscription identifier when one is supplied.",
        "last_payment_id": "Latest provider payment id used to extend Premium.",
        "created_at": "When this Premium row was created.",
        "updated_at": "When this Premium row was last updated.",
    },
    "user_symbol_alert_state": {
        "id": "Internal state row id.",
        "user_id": "User this per-symbol alert state belongs to.",
        "symbol": "Lowercase coin symbol for this alert state.",
        "last_market_update_time": (
            "When a Market Update was last successfully sent for this user and symbol."
        ),
        "last_important_alert_time": (
            "When an Important Alert was last successfully sent for this user and symbol."
        ),
        "last_critical_alert_time": (
            "When a Critical Alert was last successfully sent for this user and symbol."
        ),
        "last_notification_type": (
            "Latest user-facing notification type sent for this user and symbol."
        ),
        "last_notification_severity": (
            "Latest normalized notification severity for this user and symbol."
        ),
        "last_notification_direction": "Latest notification direction for this user and symbol.",
        "last_cumulative_movement_percent": (
            "Latest cumulative movement percent stored for suppression decisions."
        ),
        "created_at": "When this state row was created.",
        "updated_at": "When this state row was last updated.",
    },
    "payments": {
        "id": "Internal payment row id.",
        "user_id": "User whose Premium access this payment affects.",
        "provider": "Payment provider namespace, such as telegram_stars.",
        "provider_payment_id": (
            "Bot idempotency key for this provider payment; Telegram Stars uses the Telegram "
            "charge id."
        ),
        "provider_subscription_id": "Provider subscription id if Telegram supplies one.",
        "telegram_payment_charge_id": "Telegram's own charge id from successful_payment.",
        "provider_payment_charge_id": (
            "Underlying payment provider charge id passed through by Telegram."
        ),
        "is_recurring": "Telegram metadata indicating whether the payment is recurring.",
        "is_first_recurring": (
            "Telegram metadata indicating the first payment in a recurring sequence."
        ),
        "subscription_expiration_date": (
            "Provider/Telegram subscription metadata; not the source of truth for Premium access."
        ),
        "amount": "Payment amount in the provider currency unit.",
        "currency": "Payment currency code received from Telegram.",
        "payload": "Validated invoice payload tying payment to a Telegram user.",
        "status": "Stored processing status for this payment event.",
        "created_at": "When this payment row was created.",
        "updated_at": "When this payment row was last updated.",
    },
    "app_settings": {
        "id": "Internal settings row id.",
        "btc_alert_threshold_percent": (
            "Global BTC movement percent that triggers automatic alerts."
        ),
        "major_movement_threshold_percent": (
            "Admin-controlled movement percent threshold for BTC and ETH alerts."
        ),
        "alt_movement_threshold_percent": (
            "Admin-controlled movement percent threshold for non-BTC and non-ETH alerts."
        ),
        "major_24h_medium_threshold_percent": (
            "Admin-controlled 24 hour medium trend threshold for BTC and ETH alerts."
        ),
        "major_24h_high_threshold_percent": (
            "Admin-controlled 24 hour high trend threshold for BTC and ETH alerts."
        ),
        "alt_24h_medium_threshold_percent": (
            "Admin-controlled 24 hour medium trend threshold for altcoin alerts."
        ),
        "alt_24h_high_threshold_percent": (
            "Admin-controlled 24 hour high trend threshold for altcoin alerts."
        ),
        "automatic_check_interval_seconds": "Global automatic market check interval in seconds.",
        "error_file_logging_enabled": (
            "Whether admins enabled persistent WARNING and ERROR file logging."
        ),
        "created_at": "When this global settings row was created.",
        "updated_at": "When this global settings row was last updated.",
    },
    "price_state": {
        "id": "Internal price state row id.",
        "symbol": "Uppercase coin symbol for this market state.",
        "last_price": "Most recent market price stored for movement detection.",
        "last_24h_change": "Most recent 24 hour percentage change from market data.",
        "last_checked_at": "When market data was last checked.",
        "last_alert_at": "When an automatic alert was last sent.",
        "updated_at": "When this market state row was last updated.",
    },
    "price_snapshots": {
        "id": "Internal price snapshot row id.",
        "symbol": "Uppercase coin symbol for this market snapshot.",
        "price": "Market price captured at this snapshot time.",
        "change_24h": "24 hour percentage change captured with this snapshot.",
        "change_7d": "7 day percentage change captured with this snapshot.",
        "source": "Market data provider for this snapshot.",
        "checked_at": "When this market snapshot was captured.",
        "created_at": "When this snapshot row was created.",
    },
    "seen_news": {
        "id": "Internal news row id.",
        "news_key": "Stable deduplication key for the news item.",
        "title": "News title shown or analyzed by the bot.",
        "link": "Canonical link for the news item.",
        "source": "Publisher or feed source for the news item.",
        "seen_at": "When the news item was first stored.",
    },
    "alerts": {
        "id": "Internal alert delivery row id.",
        "symbol": "Uppercase coin symbol for this delivered alert.",
        "alert_type": "Alert category such as price movement.",
        "message": "Sanitized Telegram message sent or queued.",
        "sent_to_chat_id": "Telegram chat id targeted by this delivery.",
        "market_event_id": "Market event this delivery belongs to.",
        "event_ai_analysis_id": "AI analysis reused for this delivery.",
        "user_id": "Recipient user row for this delivery.",
        "status": "Delivery state such as pending, sent, or failed.",
        "error_message": "Failure detail for a failed delivery, if any.",
        "retry_count": "Number of Telegram delivery attempts already made for this alert.",
        "last_error": "Most recent Telegram delivery error for this alert.",
        "next_retry_at": "When the next Telegram delivery retry is due, if retryable.",
        "final_failed_at": "When Telegram delivery retries were exhausted or marked permanent.",
        "trigger_reason": "Concise reason that triggered this delivered alert.",
        "trigger_source": "Machine-readable signal source for this alert.",
        "numeric_context": "JSON numeric market context used for this alert decision.",
        "thresholds_used": "JSON alert thresholds used for this alert decision.",
        "llm_severity": "Severity selected or accepted for this alert.",
        "llm_reasoning_summary": "Short reasoning summary from the LLM or backend fallback.",
        "fallback_mode": (
            "Whether this delivery used a deterministic fallback instead of AI analysis."
        ),
        "created_at": "When this delivery row was created.",
    },
    "market_events": {
        "id": "Internal market event row id.",
        "symbol": "Uppercase coin symbol for the market event.",
        "event_type": "Type of market condition that was detected.",
        "event_key": "Stable idempotency key for this market event.",
        "price": "Current price captured for the event.",
        "previous_price": "Previous stored price used to calculate movement.",
        "price_change_percent": "Percentage move from previous price to current price.",
        "last_24h_change": "24 hour percentage change at detection time.",
        "last_7d_change": "7 day percentage change at detection time.",
        "detected_at": "When the market event was detected.",
        "created_at": "When this market event row was created.",
    },
    "event_ai_analyses": {
        "id": "Internal AI analysis row id.",
        "market_event_id": "Market event analyzed by the LLM.",
        "provider": "LLM provider used for this analysis.",
        "model": "LLM model name used for this analysis.",
        "input_hash": "Hash of the exact AI input used for idempotency.",
        "analysis_text": "Raw or legacy analysis text returned by the AI.",
        "plain_text": "Plain Telegram-safe analysis text for delivery.",
        "html_text": "HTML-formatted analysis text when available.",
        "prompt_tokens": "Prompt token count reported by the LLM provider.",
        "completion_tokens": "Completion token count reported by the LLM provider.",
        "total_tokens": "Total token count reported by the LLM provider.",
        "estimated_cost": "Estimated provider cost for this analysis.",
        "status": "Analysis state such as completed or failed.",
        "error_message": "Failure detail when analysis generation fails.",
        "created_at": "When this AI analysis row was created.",
    },
}


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _apply_comments(*, remove: bool) -> None:
    if not _is_postgresql():
        return

    for table_name, table_comment in TABLE_COMMENTS.items():
        if remove:
            op.drop_table_comment(table_name, existing_comment=table_comment)
        else:
            op.create_table_comment(table_name, table_comment, existing_comment=None)

    for table_name, columns in COLUMN_COMMENTS.items():
        existing_columns = _column_names(table_name)
        for column_name, column_comment in columns.items():
            if column_name not in existing_columns:
                continue
            op.alter_column(
                table_name,
                column_name,
                comment=None if remove else column_comment,
                existing_comment=column_comment if remove else None,
            )


def upgrade() -> None:
    _apply_comments(remove=False)


def downgrade() -> None:
    _apply_comments(remove=True)
