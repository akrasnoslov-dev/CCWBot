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
    "news_items": "Structured RSS news intelligence cached before alert selection.",
    "alerts": "One delivery record per recipient for a market alert.",
    "alert_delivery_outcomes": (
        "Queryable alert decision outcome for a market event, recipient, or "
        "event-level non-delivery reason."
    ),
    "market_events": "Deduplicated market movements that can trigger many deliveries.",
    "event_ai_analyses": "One reusable AI analysis for a market event and exact input payload.",
    "market_heartbeats": "Cached AI market heartbeat updates generated independently of delivery.",
    "market_reports": "Cached AI market-wide reports generated independently of user requests.",
    "llm_usage_logs": (
        "Per-call LLM usage and rate-limit telemetry captured without extra provider calls."
    ),
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
    "news_items": {
        "id": "Internal structured news row id.",
        "news_key": "Stable news identity compatible with seen_news keys.",
        "title": "Normalized RSS title for this news item.",
        "source": "Normalized publisher or feed source.",
        "url": "Normalized article URL from RSS metadata.",
        "published_at": "Publication timestamp from RSS metadata.",
        "fetched_at": "When this item was last fetched.",
        "raw_summary": "Compact RSS summary or description before LLM analysis.",
        "llm_summary": "Validated short user-facing summary returned by the LLM.",
        "llm_raw_response": "Raw compact JSON response returned by the news LLM.",
        "related_symbols": "Lowercase supported symbols related to this news item.",
        "primary_symbol": "Primary lowercase supported symbol selected for the item.",
        "category": "Validated news category such as market or regulation.",
        "impact_score": "Validated impact score from 0 to 100.",
        "impact_level": "Validated impact level such as low or high.",
        "relevance_score": "Validated relevance score from 0 to 100.",
        "dedup_group_id": "Stable group id for duplicate or similar news items.",
        "is_duplicate": "Whether this item duplicates a previously processed item.",
        "is_noise": "Whether this item is low-quality or not useful context.",
        "is_alert_worthy": "Whether intelligence considers the item alert-worthy later.",
        "llm_provider": "LLM provider used for news intelligence.",
        "llm_model": "LLM model used for news intelligence.",
        "llm_input_hash": "SHA-256 hash of the compact LLM input payload.",
        "llm_status": "News intelligence status such as success or skipped.",
        "llm_error": "Sanitized news intelligence error message, if any.",
        "created_at": "When this structured news row was created.",
        "updated_at": "When this structured news row was last updated.",
    },
    "alerts": {
        "id": "Internal alert delivery row id.",
        "symbol": "Uppercase coin symbol for this delivered alert.",
        "alert_type": "Alert category such as price movement.",
        "message": "Sanitized Telegram message sent or queued.",
        "sent_to_chat_id": "Telegram chat id targeted by this delivery.",
        "market_event_id": "Market event this delivery belongs to.",
        "market_heartbeat_id": (
            "Market heartbeat this delivery belongs to when the alert is a heartbeat."
        ),
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
    "alert_delivery_outcomes": {
        "id": "Internal alert delivery outcome row id.",
        "symbol": "Uppercase coin symbol for this alert outcome.",
        "alert_type": "Alert category this outcome belongs to.",
        "market_event_id": "Market event this outcome explains, when one exists.",
        "event_ai_analysis_id": "AI analysis this outcome explains, when one exists.",
        "alert_id": "Delivery row this outcome summarizes, when Telegram delivery was attempted.",
        "user_id": "Recipient user considered for this alert outcome, if recipient-specific.",
        "sent_to_chat_id": "Telegram chat id considered for this outcome, when available.",
        "status": "Queryable outcome status such as delivered, filtered, suppressed, or failed.",
        "reason_code": "Machine-readable reason code for this outcome.",
        "recipient_considered": "Whether a concrete recipient was evaluated for this alert.",
        "recipient_eligible": (
            "Whether the considered recipient was eligible for Telegram delivery."
        ),
        "trigger_source": "Machine-readable signal source for this outcome.",
        "event_instance_key": "Stable idempotency key for the market event.",
        "semantic_family": "Canonical semantic family used for suppression.",
        "decision_stage": "Decision stage that produced this operator-facing outcome.",
        "decision_reason": "Machine-readable event alert decision reason for operator reports.",
        "previous_alert_id": "Previous alert row considered for repeat or cooldown decisions.",
        "context_fingerprint": (
            "Safe hash of the sanitized decision context used for observability."
        ),
        "detail": "Sanitized secondary diagnostic detail for operators.",
        "created_at": "When this outcome row was created.",
    },
    "market_events": {
        "id": "Internal market event row id.",
        "symbol": "Uppercase coin symbol for the market event.",
        "event_type": "Type of market condition that was detected.",
        "event_key": "Semantic event key reported by the LLM or generated by the backend.",
        "event_instance_key": "Stable idempotency key for this concrete market event occurrence.",
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
        "market_event_id": "Market event analyzed by the LLM when an event alert is created.",
        "analysis_id": "External stable id for this LLM analysis attempt.",
        "symbol": "Uppercase coin symbol analyzed by this LLM attempt.",
        "analysis_type": "Analysis purpose such as event_analysis.",
        "provider": "LLM provider used for this analysis.",
        "model": "LLM model name used for this analysis.",
        "input_hash": "Hash of the exact AI input used for idempotency.",
        "raw_input_json": "Raw JSON input payload sent to the LLM.",
        "raw_output_json": "Raw JSON or text output returned by the LLM.",
        "parsed_result_json": "Validated JSON result fields from the LLM response.",
        "should_alert": "Whether the LLM decided this analysis should alert users.",
        "event_key": "LLM event key when should_alert is true.",
        "title": "LLM alert title for an event alert.",
        "message_body": "LLM alert body for an event alert.",
        "related_news_ids": "JSON array of candidate news ids selected by the LLM.",
        "possible_action": "Possible action text returned by the LLM.",
        "urgency": "LLM event urgency: low, normal, or high.",
        "confidence": "LLM confidence: low, medium, or high.",
        "reason_for_no_alert": "LLM explanation when no event alert should be sent.",
        "analysis_text": "Raw or legacy analysis text returned by the AI.",
        "plain_text": "Plain Telegram-safe analysis text for delivery.",
        "html_text": "HTML-formatted analysis text when available.",
        "prompt_tokens": "Prompt token count reported by the LLM provider.",
        "completion_tokens": "Completion token count reported by the LLM provider.",
        "total_tokens": "Total token count reported by the LLM provider.",
        "estimated_cost": "Estimated provider cost for this analysis.",
        "status": "Analysis state such as completed or failed.",
        "error_message": "Failure detail when analysis generation fails.",
        "error_reason": "Normalized LLM failure reason for admin status.",
        "llm_operation_id": "Opaque backend correlation id for the logical LLM operation.",
        "created_at": "When this AI analysis row was created.",
    },
    "market_heartbeats": {
        "id": "Internal market heartbeat row id.",
        "symbol": "Uppercase coin symbol this heartbeat describes.",
        "generated_at": "When this heartbeat generation ran.",
        "raw_input_json": "Raw JSON input payload sent to the LLM.",
        "raw_output_json": "Raw JSON or text output returned by the LLM.",
        "title": "LLM heartbeat title for Telegram delivery.",
        "message_body": "LLM heartbeat body for Telegram delivery.",
        "related_news_ids": "JSON array of candidate news ids selected by the LLM.",
        "possible_action": "Possible action text returned by the LLM.",
        "confidence": "LLM heartbeat confidence: low, medium, or high.",
        "status": "Heartbeat generation state such as completed or failed.",
        "error_message": "Failure detail when heartbeat generation fails.",
        "llm_operation_id": "Opaque backend correlation id for the logical LLM operation.",
        "created_at": "When this heartbeat row was created.",
    },
    "market_reports": {
        "id": "Internal market report row id.",
        "report_type": "Report cadence, either daily or weekly.",
        "generated_at": "When this report generation ran.",
        "expires_at": "When this cached report should be refreshed.",
        "status": "Report generation state, either completed or failed.",
        "raw_input_json": "Raw JSON input payload sent to the report LLM.",
        "raw_output_json": "Raw JSON or text output returned by the report LLM.",
        "telegram_message": "Sanitized Telegram report message when generation succeeded.",
        "error_message": "Failure detail when report generation failed.",
        "provider": "LLM provider used for this report generation.",
        "model": "LLM model used for this report generation.",
        "llm_operation_id": "Opaque backend correlation id for the logical LLM operation.",
        "created_at": "When this report row was created.",
    },
    "llm_usage_logs": {
        "id": "Internal LLM usage row id.",
        "created_at": "When this LLM call ran.",
        "provider": "LLM provider that handled the request.",
        "model": "Exact LLM model requested for this call.",
        "call_type": "Purpose of the LLM call such as event_analysis.",
        "symbol": "Uppercase coin symbol for this call.",
        "status": "Final call status such as success or rate_limit.",
        "prompt_tokens": "Prompt tokens reported by the provider.",
        "completion_tokens": "Completion tokens reported by the provider.",
        "total_tokens": "Total tokens reported by the provider.",
        "input_chars": "Character count of messages sent to the provider.",
        "output_chars": "Character count of the provider response body.",
        "max_tokens": "Maximum completion tokens configured for the call.",
        "rate_limit_limit_requests": "Provider request limit header value when available.",
        "rate_limit_remaining_requests": "Provider remaining requests header when available.",
        "rate_limit_reset_requests": "Provider request limit reset header when available.",
        "rate_limit_limit_tokens": "Provider token limit header value when available.",
        "rate_limit_remaining_tokens": "Provider remaining tokens header when available.",
        "rate_limit_reset_tokens": "Provider token limit reset header when available.",
        "retry_after": "Provider retry-after header when rate limited.",
        "error_reason": "Normalized safe error reason for failed calls.",
        "error_message": "Sanitized provider or parser error message.",
        "llm_operation_id": (
            "Opaque backend correlation id shared by provider attempts in one logical operation."
        ),
        "provider_request_id": (
            "Allowlisted opaque provider request id when the response exposes one."
        ),
    },
}


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _apply_comments(*, remove: bool) -> None:
    if not _is_postgresql():
        return

    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    for table_name, table_comment in TABLE_COMMENTS.items():
        if table_name not in existing_tables:
            continue
        if remove:
            op.drop_table_comment(table_name, existing_comment=table_comment)
        else:
            op.create_table_comment(table_name, table_comment, existing_comment=None)

    for table_name, columns in COLUMN_COMMENTS.items():
        if table_name not in existing_tables:
            continue
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
