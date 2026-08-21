# ruff: noqa: E501
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DbQuery:
    name: str
    evidence_file: str
    sql: str


ACTIVE_SYMBOLS = ("btc", "eth", "gram", "sol")
ACTIVE_SYMBOL_VALUES_SQL = "VALUES " + ", ".join(
    f"('{symbol}')" for symbol in ACTIVE_SYMBOLS
)
MARKET_DATA_FRESHNESS_GRACE_SECONDS = 120
EFFECTIVE_EVENT_ANALYSIS_INTERVAL_SECONDS = 1800
DAILY_REPORT_RUNTIME_INTERVAL_SECONDS = 14400
WEEKLY_REPORT_RUNTIME_INTERVAL_SECONDS = 86400
DAILY_REPORT_FRESHNESS_GRACE_SECONDS = 3600
WEEKLY_REPORT_FRESHNESS_GRACE_SECONDS = 3600
DAILY_REPORT_FRESHNESS_THRESHOLD_SECONDS = (
    DAILY_REPORT_RUNTIME_INTERVAL_SECONDS + DAILY_REPORT_FRESHNESS_GRACE_SECONDS
)
WEEKLY_REPORT_FRESHNESS_THRESHOLD_SECONDS = (
    WEEKLY_REPORT_RUNTIME_INTERVAL_SECONDS + WEEKLY_REPORT_FRESHNESS_GRACE_SECONDS
)
REPORT_FRESHNESS_VALUES_SQL = (
    "VALUES "
    f"('daily', {DAILY_REPORT_FRESHNESS_THRESHOLD_SECONDS}, "
    f"{DAILY_REPORT_RUNTIME_INTERVAL_SECONDS}), "
    f"('weekly', {WEEKLY_REPORT_FRESHNESS_THRESHOLD_SECONDS}, "
    f"{WEEKLY_REPORT_RUNTIME_INTERVAL_SECONDS})"
)
# Count of candidate news items inside an event analysis raw input payload (event analysis
# uses key "news"; older payloads used "candidate_news"). The first-char guard skips
# obviously non-JSON values and non-array shapes yield NULL (unknown); rows are written by
# json.dumps, and a malformed row would fail only this one isolated query.
RELATED_NEWS_CANDIDATES_COUNT_SQL = (
    "(CASE WHEN left(ltrim(coalesce(raw_input_json, '')), 1) = '{' THEN "
    "coalesce("
    "CASE WHEN jsonb_typeof(raw_input_json::jsonb->'news') = 'array' "
    "THEN jsonb_array_length(raw_input_json::jsonb->'news') END, "
    "CASE WHEN jsonb_typeof(raw_input_json::jsonb->'candidate_news') = 'array' "
    "THEN jsonb_array_length(raw_input_json::jsonb->'candidate_news') END"
    ") END)"
)


QUERIES: tuple[DbQuery, ...] = (
    DbQuery("schema_version", "evidence/db/aggregate_metrics.json", "SELECT version_num FROM alembic_version"),
    DbQuery(
        "app_settings",
        "evidence/db/aggregate_metrics.json",
        "SELECT btc_alert_threshold_percent, major_movement_threshold_percent, "
        "alt_movement_threshold_percent, automatic_check_interval_seconds, "
        "error_file_logging_enabled, updated_at FROM app_settings ORDER BY id DESC LIMIT 1",
    ),
    DbQuery(
        "user_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT count(*) AS total_users, count(*) FILTER (WHERE is_active) AS active_users, "
        "count(*) FILTER (WHERE bot_blocked) AS blocked_users, "
        "count(*) FILTER (WHERE role = 'admin') AS admins, "
        "count(*) FILTER (WHERE created_at >= :since AND created_at < :until) AS new_users "
        "FROM users",
    ),
    DbQuery(
        "user_impact_summary",
        "evidence/db/aggregate_metrics.json",
        "WITH period_alerts AS ("
        "SELECT a.user_id, a.alert_type, a.status, a.market_heartbeat_id, a.market_event_id, "
        "a.message, me.price_change_percent, me.last_24h_change, me.last_7d_change "
        "FROM alerts a LEFT JOIN market_events me ON me.id = a.market_event_id "
        "WHERE a.created_at >= :since AND a.created_at < :until), "
        "duplicate_delivery_users AS ("
        "SELECT user_id FROM period_alerts WHERE market_event_id IS NOT NULL "
        "GROUP BY user_id, market_event_id HAVING count(*) > 1) "
        "SELECT count(DISTINCT u.id) FILTER (WHERE u.is_active) AS active_users_current, "
        "count(DISTINCT pa.user_id) FILTER (WHERE pa.alert_type = 'event_alert') AS users_received_event_alerts, "
        "count(DISTINCT pa.user_id) FILTER (WHERE pa.market_heartbeat_id IS NOT NULL OR pa.alert_type = 'heartbeat') AS users_received_heartbeats, "
        "count(DISTINCT pa.user_id) FILTER (WHERE pa.status IN ('failed', 'retry_pending')) AS users_affected_by_delivery_failures, "
        "(SELECT count(DISTINCT user_id) FROM duplicate_delivery_users) AS users_affected_by_duplicate_alerts, "
        "count(DISTINCT pa.user_id) FILTER (WHERE pa.alert_type = 'event_alert' AND ("
        "lower(coalesce(pa.message, '')) LIKE '%n/a%' "
        "OR lower(coalesce(pa.message, '')) LIKE '%unknown%' "
        "OR lower(coalesce(pa.message, '')) LIKE '%unavailable%' "
        "OR lower(coalesce(pa.message, '')) LIKE '%null%' "
        "OR lower(coalesce(pa.message, '')) LIKE '%since last btc alert%' "
        "OR lower(coalesce(pa.message, '')) LIKE '%analysed-window change%' "
        "OR coalesce(pa.message, '') ~* '(^|\\n)[[:space:]]*([•*\\-][[:space:]]*)?price change[[:space:]]*:'"
        ")) AS users_affected_by_content_quality_issues "
        "FROM users u LEFT JOIN period_alerts pa ON pa.user_id = u.id",
    ),
    DbQuery(
        "watchlist_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT symbol, is_enabled, count(*) AS users FROM user_coin_subscriptions "
        "GROUP BY symbol, is_enabled ORDER BY symbol, is_enabled",
    ),
    DbQuery(
        "event_alert_llm_estimates",
        "evidence/db/aggregate_metrics.json",
        "WITH settings AS ("
        "SELECT event_analysis_interval_seconds FROM ("
        f"(SELECT {EFFECTIVE_EVENT_ANALYSIS_INTERVAL_SECONDS} AS event_analysis_interval_seconds, 0 AS priority "
        "FROM app_settings ORDER BY id DESC LIMIT 1) "
        "UNION ALL "
        f"(SELECT {EFFECTIVE_EVENT_ANALYSIS_INTERVAL_SECONDS} AS event_analysis_interval_seconds, 1 AS priority "
        "WHERE NOT EXISTS (SELECT 1 FROM app_settings))"
        ") rows ORDER BY priority LIMIT 1), "
        "active_symbols(symbol) AS ("
        f"{ACTIVE_SYMBOL_VALUES_SQL}"
        "), eligible_subscription_symbols AS ("
        "SELECT DISTINCT lower(ucs.symbol) AS symbol "
        "FROM user_coin_subscriptions ucs "
        "JOIN users u ON u.id = ucs.user_id "
        "LEFT JOIN user_premium_subscriptions ups ON ups.user_id = u.id "
        "WHERE u.telegram_chat_id IS NOT NULL AND u.is_active = true AND u.bot_blocked = false "
        "AND ucs.is_enabled = true "
        "AND (lower(ucs.symbol) = 'btc' OR ups.active_until > :until)) "
        ", eligible_symbol_counts AS ("
        "SELECT count(*) AS configured_symbols, "
        "count(*) FILTER (WHERE es.symbol IN (SELECT symbol FROM active_symbols)) AS active_symbols, "
        "count(*) FILTER (WHERE es.symbol NOT IN (SELECT symbol FROM active_symbols)) "
        "AS inactive_configured_symbols FROM eligible_subscription_symbols es) "
        "SELECT s.event_analysis_interval_seconds, 6 AS payload_points, "
        "ceil((s.event_analysis_interval_seconds * 6) / 60.0)::integer AS analysed_window_minutes, "
        "coalesce(e.configured_symbols, 0) AS configured_eligible_symbols, "
        "coalesce(e.active_symbols, 0) AS active_eligible_symbols, "
        "coalesce(e.inactive_configured_symbols, 0) AS inactive_configured_eligible_symbols, "
        "coalesce(e.active_symbols, 0) AS eligible_symbols, "
        "round((coalesce(e.active_symbols, 0) * 3600.0 / s.event_analysis_interval_seconds)::numeric, 2) "
        "AS estimated_event_alert_llm_calls_per_hour, "
        "round((coalesce(e.active_symbols, 0) * 86400.0 / s.event_analysis_interval_seconds)::numeric, 2) "
        "AS estimated_event_alert_llm_calls_per_day "
        "FROM settings s CROSS JOIN eligible_symbol_counts e",
    ),
    DbQuery(
        "premium_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT status, count(*) AS subscriptions, "
        "count(*) FILTER (WHERE active_until >= :until) AS active_count, "
        "count(*) FILTER (WHERE active_until < :until) AS expired_count, "
        "count(*) FILTER (WHERE active_until >= :since AND active_until < :until) AS expiring_in_period "
        "FROM user_premium_subscriptions GROUP BY status ORDER BY status",
    ),
    DbQuery(
        "premium_payment_inconsistencies",
        "evidence/db/anomalies.json",
        "WITH duplicate_provider_payment_ids AS ("
        "SELECT 'duplicate_provider_payment_ids' AS anomaly, p.user_id, p.provider, "
        "p.provider_payment_id, NULL::integer AS payment_id, NULL::text AS details "
        "FROM payments p JOIN ("
        "SELECT provider, provider_payment_id FROM payments "
        "GROUP BY provider, provider_payment_id HAVING count(*) > 1"
        ") dup ON dup.provider = p.provider AND dup.provider_payment_id = p.provider_payment_id), "
        "duplicate_charge_ids AS ("
        "SELECT 'duplicate_charge_ids' AS anomaly, p.user_id, p.provider, "
        "coalesce(p.telegram_payment_charge_id, p.provider_payment_charge_id, p.provider_subscription_id) "
        "AS provider_payment_id, p.id AS payment_id, 'duplicate non-null charge/subscription id' AS details "
        "FROM payments p WHERE p.telegram_payment_charge_id IN ("
        "SELECT telegram_payment_charge_id FROM payments WHERE telegram_payment_charge_id IS NOT NULL "
        "GROUP BY telegram_payment_charge_id HAVING count(*) > 1"
        ") OR p.provider_payment_charge_id IN ("
        "SELECT provider_payment_charge_id FROM payments WHERE provider_payment_charge_id IS NOT NULL "
        "GROUP BY provider_payment_charge_id HAVING count(*) > 1"
        ") OR p.provider_subscription_id IN ("
        "SELECT provider_subscription_id FROM payments WHERE provider_subscription_id IS NOT NULL "
        "GROUP BY provider_subscription_id HAVING count(*) > 1"
        ")), "
        "paid_without_premium AS ("
        "SELECT 'paid_without_premium' AS anomaly, p.user_id, p.provider, p.provider_payment_id, "
        "p.id AS payment_id, 'paid payment lacks active premium row' AS details "
        "FROM payments p LEFT JOIN user_premium_subscriptions ups ON ups.user_id = p.user_id "
        "WHERE p.status = 'paid' AND p.created_at >= :since AND p.created_at < :until "
        "AND (ups.id IS NULL OR ups.active_until IS NULL OR ups.active_until < p.created_at + interval '29 days') "
        "AND ups.cancelled_at IS NULL), "
        "expired_active_subscriptions AS ("
        "SELECT 'expired_active_subscription' AS anomaly, ups.user_id, ups.provider, "
        "ups.last_payment_id AS provider_payment_id, NULL::integer AS payment_id, "
        "'status active but active_until is expired' AS details "
        "FROM user_premium_subscriptions ups "
        "WHERE ups.status = 'active' AND (ups.active_until IS NULL OR ups.active_until <= :until)), "
        "premium_access_status_mismatch AS ("
        "SELECT 'premium_access_status_mismatch' AS anomaly, ups.user_id, ups.provider, "
        "ups.last_payment_id AS provider_payment_id, NULL::integer AS payment_id, "
        "'active_until grants access but lifecycle status/cancelled_at disagrees' AS details "
        "FROM user_premium_subscriptions ups "
        "WHERE ups.active_until > :until AND (ups.status != 'active' OR ups.cancelled_at IS NOT NULL)), "
        "active_premium_without_trail AS ("
        "SELECT 'active_premium_without_trail' AS anomaly, ups.user_id, ups.provider, "
        "ups.last_payment_id AS provider_payment_id, NULL::integer AS payment_id, "
        "'active premium has no payment or manual grant trail' AS details "
        "FROM user_premium_subscriptions ups "
        "LEFT JOIN payments p ON p.user_id = ups.user_id AND p.id::text = ups.last_payment_id "
        "WHERE ups.status = 'active' AND ups.active_until > :until "
        "AND (ups.provider IS NULL OR ups.provider NOT IN ('manual', 'telegram_stars') "
        "OR (ups.provider = 'telegram_stars' AND (ups.last_payment_id IS NULL OR p.id IS NULL)))), "
        "payment_payload_user_mismatch AS ("
        "SELECT 'payment_payload_user_mismatch' AS anomaly, p.user_id, p.provider, "
        "p.provider_payment_id, p.id AS payment_id, 'invoice payload does not match Telegram user' AS details "
        "FROM payments p JOIN users u ON u.id = p.user_id "
        "WHERE p.provider = 'telegram_stars' "
        "AND p.payload != concat('ccwbot-premium-v1:u', u.telegram_user_id)), "
        "charge_id_mismatch AS ("
        "SELECT 'charge_id_mismatch' AS anomaly, p.user_id, p.provider, p.provider_payment_id, "
        "p.id AS payment_id, 'provider payment id differs from Telegram charge id' AS details "
        "FROM payments p WHERE p.provider = 'telegram_stars' "
        "AND p.telegram_payment_charge_id IS NOT NULL "
        "AND p.provider_payment_id != p.telegram_payment_charge_id) "
        "SELECT * FROM duplicate_provider_payment_ids UNION ALL SELECT * FROM duplicate_charge_ids "
        "UNION ALL SELECT * FROM paid_without_premium UNION ALL SELECT * FROM expired_active_subscriptions "
        "UNION ALL SELECT * FROM premium_access_status_mismatch "
        "UNION ALL SELECT * FROM active_premium_without_trail "
        "UNION ALL SELECT * FROM payment_payload_user_mismatch UNION ALL SELECT * FROM charge_id_mismatch "
        "LIMIT :anomaly_limit",
    ),
    DbQuery(
        "payments_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT provider, currency, status, count(*) AS payments, sum(amount) AS amount_total "
        "FROM payments WHERE created_at >= :since AND created_at < :until "
        "GROUP BY provider, currency, status ORDER BY provider, currency, status",
    ),
    DbQuery(
        "price_state_current",
        "evidence/db/aggregate_metrics.json",
        "SELECT symbol, last_price, last_24h_change, last_checked_at, last_alert_at "
        f"FROM price_state WHERE lower(symbol) IN (SELECT column1 FROM ({ACTIVE_SYMBOL_VALUES_SQL}) active_symbols) "
        "ORDER BY symbol",
    ),
    DbQuery(
        "legacy_inactive_price_state",
        "evidence/db/aggregate_metrics.json",
        "SELECT symbol, last_checked_at, 'legacy_inactive_symbol' AS classification "
        f"FROM price_state WHERE lower(symbol) NOT IN (SELECT column1 FROM ({ACTIVE_SYMBOL_VALUES_SQL}) active_symbols) "
        "ORDER BY symbol LIMIT :limit",
    ),
    DbQuery(
        "price_snapshots_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT symbol, count(*) AS snapshots, min(price) AS min_price, max(price) AS max_price, "
        "avg(price) AS avg_price, avg(change_24h) AS avg_change_24h, avg(change_7d) AS avg_change_7d, "
        "min(checked_at) AS first_checked_at, max(checked_at) AS last_checked_at "
        "FROM price_snapshots WHERE checked_at >= :since AND checked_at < :until "
        "GROUP BY symbol ORDER BY symbol",
    ),
    DbQuery(
        "market_events_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT symbol, event_type, event_key, count(*) AS events, min(detected_at) AS first_detected_at, "
        "max(detected_at) AS last_detected_at, max(abs(price_change_percent)) AS max_abs_move "
        "FROM market_events WHERE detected_at >= :since AND detected_at < :until "
        "GROUP BY symbol, event_type, event_key ORDER BY events DESC, symbol LIMIT :limit",
    ),
    DbQuery(
        "market_events_recent",
        "evidence/db/recent_market_events.json",
        "SELECT id AS market_event_id, symbol, event_type, event_key, price, previous_price, "
        "price_change_percent, last_24h_change, last_7d_change, detected_at "
        "FROM market_events WHERE detected_at >= :since AND detected_at < :until "
        "ORDER BY detected_at DESC, id DESC LIMIT :sample_limit",
    ),
    DbQuery(
        "duplicate_market_event_buckets",
        "evidence/db/anomalies.json",
        "WITH bucketed_events AS ("
        "SELECT symbol, event_type, event_key, "
        "floor(extract(epoch FROM detected_at) / (:duplicate_bucket_minutes * 60)) AS bucket_id, "
        "count(*) AS group_size, min(detected_at) AS first_detected_at, "
        "max(detected_at) AS last_detected_at, "
        "(array_agg(id ORDER BY detected_at ASC, id ASC))[1:5] AS sample_market_event_ids "
        "FROM market_events WHERE detected_at >= :since AND detected_at < :until "
        "GROUP BY symbol, event_type, event_key, "
        "floor(extract(epoch FROM detected_at) / (:duplicate_bucket_minutes * 60)) "
        "HAVING count(*) > 1) "
        "SELECT symbol, event_type, event_key, group_size, first_detected_at, last_detected_at, "
        "sample_market_event_ids FROM bucketed_events "
        "ORDER BY group_size DESC, last_detected_at DESC LIMIT :anomaly_limit",
    ),
    DbQuery(
        "event_ai_analysis_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT coalesce(symbol, 'UNKNOWN') AS symbol, coalesce(status, 'unknown') AS status, "
        "should_alert, error_reason, count(*) AS analyses, sum(total_tokens) AS total_tokens, "
        "max(created_at) AS latest_attempt_at FROM event_ai_analyses "
        "WHERE created_at >= :since AND created_at < :until "
        "GROUP BY coalesce(symbol, 'UNKNOWN'), coalesce(status, 'unknown'), should_alert, error_reason "
        "ORDER BY analyses DESC LIMIT :limit",
    ),
    DbQuery(
        "event_ai_analysis_invariant_checks",
        "evidence/db/anomalies.json",
        "SELECT 'multiple_event_ai_analyses_for_event' AS anomaly, symbol, market_event_id, "
        "count(*) AS analysis_count, count(DISTINCT input_hash) AS input_hashes, "
        "(array_agg(id ORDER BY created_at ASC, id ASC))[1:5] AS sample_analysis_ids "
        "FROM event_ai_analyses WHERE market_event_id IS NOT NULL "
        "AND coalesce(analysis_type, 'event_analysis') = 'event_analysis' "
        "AND status IN ('success', 'completed') "
        "AND created_at >= :since AND created_at < :until "
        "GROUP BY symbol, market_event_id HAVING count(*) > 1 OR count(DISTINCT input_hash) > 1 "
        "ORDER BY analysis_count DESC LIMIT :anomaly_limit",
    ),
    DbQuery(
        "event_ai_analysis_samples",
        "evidence/db/recent_llm_failures.json",
        "SELECT id, market_event_id, symbol, analysis_type, provider, model, status, should_alert, "
        "error_reason, left(error_message, 300) AS error_message, created_at, "
        # Sanitized signal: how many candidate news items the analysis input contained
        # (a count only, never news content), so "no relevant news existed" is
        # distinguishable from "news-attach path broken".
        f"{RELATED_NEWS_CANDIDATES_COUNT_SQL} AS related_news_candidates_count "
        "FROM event_ai_analyses WHERE created_at >= :since AND created_at < :until "
        "AND status NOT IN ('success', 'completed') ORDER BY created_at DESC, id DESC LIMIT :sample_limit",
    ),
    DbQuery(
        "event_analysis_news_candidates_summary",
        "evidence/db/aggregate_metrics.json",
        # Counts only (no news content): distinguishes analyses that genuinely had zero
        # candidate news in their input from should_alert=true analyses that had
        # candidates available but attached none (possible news-attach gap).
        "WITH analysis_news AS ("
        "SELECT coalesce(symbol, 'UNKNOWN') AS symbol, should_alert, related_news_ids, "
        f"{RELATED_NEWS_CANDIDATES_COUNT_SQL} AS related_news_candidates_count "
        "FROM event_ai_analyses "
        "WHERE created_at >= :since AND created_at < :until "
        "AND coalesce(analysis_type, 'event_analysis') = 'event_analysis') "
        "SELECT symbol, count(*) AS analyses, "
        "count(*) FILTER (WHERE related_news_candidates_count = 0) AS zero_candidate_analyses, "
        "count(*) FILTER (WHERE related_news_candidates_count > 0) AS with_candidates_analyses, "
        "count(*) FILTER (WHERE related_news_candidates_count IS NULL) AS unknown_candidates_analyses, "
        "count(*) FILTER (WHERE related_news_candidates_count > 0 AND should_alert = true "
        "AND (related_news_ids IS NULL OR related_news_ids::text IN ('[]', 'null', ''))) "
        "AS alerts_with_candidates_but_no_attached_news "
        "FROM analysis_news GROUP BY symbol ORDER BY symbol",
    ),
    DbQuery(
        "alerts_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT symbol, alert_type, coalesce(status, 'unknown') AS status, trigger_source, fallback_mode, "
        "count(*) AS deliveries, count(*) FILTER (WHERE status = 'sent') AS sent, "
        "count(*) FILTER (WHERE status IN ('failed', 'retry_pending') OR final_failed_at IS NOT NULL) AS failed "
        "FROM alerts WHERE created_at >= :since AND created_at < :until "
        "GROUP BY symbol, alert_type, coalesce(status, 'unknown'), trigger_source, fallback_mode "
        "ORDER BY deliveries DESC LIMIT :limit",
    ),
    DbQuery(
        "telegram_delivery_failure_summary",
        "evidence/db/aggregate_metrics.json",
        "WITH failures AS ("
        "SELECT CASE WHEN lower(coalesce(last_error, error_message, '')) LIKE '%bot was blocked%' "
        "OR lower(coalesce(last_error, error_message, '')) LIKE '%chat not found%' "
        "OR lower(coalesce(last_error, error_message, '')) LIKE '%user is deactivated%' "
        "OR lower(coalesce(last_error, error_message, '')) LIKE '%forbidden%' "
        "THEN 'blocked_user' WHEN status = 'retry_pending' THEN 'retry_pending_actionable' "
        "ELSE 'unexplained_telegram_failure' END AS failure_category "
        "FROM alerts WHERE created_at >= :since AND created_at < :until "
        "AND (status IN ('failed', 'retry_pending') OR final_failed_at IS NOT NULL)) "
        "SELECT count(*) AS failed_or_retry_pending_total, "
        "count(*) FILTER (WHERE failure_category = 'blocked_user') AS blocked_user, "
        "count(*) FILTER (WHERE failure_category = 'retry_pending_actionable') "
        "AS retry_pending_actionable, "
        "count(*) FILTER (WHERE failure_category = 'unexplained_telegram_failure') "
        "AS unexplained_telegram_failure FROM failures",
    ),
    DbQuery(
        "delivery_funnel",
        "evidence/db/aggregate_metrics.json",
        "SELECT "
        "(SELECT count(*) FROM market_events WHERE detected_at >= :since AND detected_at < :until) AS market_events, "
        "(SELECT count(*) FROM event_ai_analyses WHERE created_at >= :since AND created_at < :until) AS ai_analyses, "
        "(SELECT count(*) FROM event_ai_analyses WHERE created_at >= :since AND created_at < :until AND should_alert = true) AS should_alert_true, "
        "(SELECT count(*) FROM alerts WHERE created_at >= :since AND created_at < :until AND alert_type = 'event_alert') AS alert_records_created, "
        "(SELECT count(*) FROM alerts WHERE created_at >= :since AND created_at < :until AND alert_type = 'event_alert') AS telegram_delivery_attempts, "
        "(SELECT count(*) FROM alerts WHERE created_at >= :since AND created_at < :until AND alert_type = 'event_alert' AND status = 'sent') AS telegram_delivered, "
        "(SELECT count(*) FROM alerts WHERE created_at >= :since AND created_at < :until "
        "AND alert_type = 'event_alert' "
        "AND (status IN ('failed', 'retry_pending') OR final_failed_at IS NOT NULL)) AS telegram_failed",
    ),
    DbQuery(
        "event_alert_delivered_event_ratio",
        "evidence/db/aggregate_metrics.json",
        "WITH should_alert_events AS ("
        "SELECT DISTINCT market_event_id FROM event_ai_analyses "
        "WHERE created_at >= :since AND created_at < :until "
        "AND should_alert = true AND market_event_id IS NOT NULL) "
        "SELECT "
        "(SELECT count(*) FROM should_alert_events) AS should_alert_true_events, "
        "(SELECT count(DISTINCT a.market_event_id) FROM alerts a "
        "WHERE a.market_event_id IN (SELECT market_event_id FROM should_alert_events) "
        "AND a.alert_type = 'event_alert' AND a.status = 'sent') AS delivered_events",
    ),
    DbQuery(
        "alert_quality_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT lower(coalesce(a.symbol, 'unknown')) AS symbol, "
        "coalesce(a.trigger_source, 'unknown') AS trigger_source, "
        "coalesce(a.alert_type, 'unknown') AS alert_type, "
        "count(*) AS deliveries, "
        "count(DISTINCT a.user_id) AS affected_users, "
        "count(*) FILTER (WHERE coalesce(a.message, '') ~* '(^|[^a-z0-9])n/a([^a-z0-9]|$)') AS contains_n_a, "
        "count(*) FILTER (WHERE coalesce(a.message, '') ~* '(^|[^a-z0-9])unknown([^a-z0-9]|$)') AS contains_unknown, "
        "count(*) FILTER (WHERE coalesce(a.message, '') ~* '(^|[^a-z0-9])unavailable([^a-z0-9]|$)') AS contains_unavailable, "
        "count(*) FILTER (WHERE coalesce(a.message, '') ~* '(^|[^a-z0-9])null([^a-z0-9]|$)') AS contains_null, "
        "count(*) FILTER (WHERE a.alert_type = 'event_alert' "
        "AND lower(coalesce(a.message, '')) LIKE '%since last btc alert%') AS old_since_last_btc_alert_label, "
        "count(*) FILTER (WHERE a.alert_type = 'event_alert' "
        "AND lower(coalesce(a.message, '')) LIKE '%analysed-window change%') AS old_analysed_window_change_label, "
        "count(*) FILTER (WHERE a.alert_type = 'event_alert' "
        "AND coalesce(a.message, '') ~* '(^|\\n)[[:space:]]*([•*\\-][[:space:]]*)?price change[[:space:]]*:') AS old_generic_price_change_label, "
        "count(*) FILTER (WHERE a.alert_type = 'event_alert' AND ("
        "eai.related_news_ids IS NULL OR eai.related_news_ids::text IN ('[]', 'null', '')"
        ")) AS empty_related_context, "
        "count(*) FILTER (WHERE a.message IS NULL OR length(trim(a.message)) = 0) AS malformed_formatting "
        "FROM alerts a "
        "LEFT JOIN market_events me ON me.id = a.market_event_id "
        "LEFT JOIN event_ai_analyses eai ON eai.id = a.event_ai_analysis_id "
        "WHERE a.created_at >= :since AND a.created_at < :until "
        "GROUP BY lower(coalesce(a.symbol, 'unknown')), coalesce(a.trigger_source, 'unknown'), coalesce(a.alert_type, 'unknown') "
        "ORDER BY deliveries DESC LIMIT :limit",
    ),
    DbQuery(
        "event_alert_delivery_explanation_gaps",
        "evidence/db/anomalies.json",
        "WITH candidate_analyses AS ("
        "SELECT id, market_event_id, symbol, event_key, created_at FROM event_ai_analyses "
        "WHERE created_at >= :since AND created_at < :until "
        "AND market_event_id IS NOT NULL "
        "AND coalesce(analysis_type, 'event_analysis') = 'event_analysis' "
        "AND status IN ('success', 'completed') AND should_alert = true), "
        "sent_delivery AS ("
        "SELECT event_ai_analysis_id, market_event_id, count(*) AS sent_count "
        "FROM alerts WHERE alert_type = 'event_alert' AND status = 'sent' "
        "AND created_at >= :since AND created_at < :until "
        "GROUP BY event_ai_analysis_id, market_event_id), "
        "explained_outcomes AS ("
        "SELECT event_ai_analysis_id, market_event_id, count(*) AS explained_count "
        "FROM alert_delivery_outcomes WHERE alert_type = 'event_alert' "
        "AND created_at >= :since AND created_at < :until "
        "AND status IN ('delivered', 'suppressed', 'cooldown', 'failed', 'rate_limited', "
        "'no_eligible_recipients', 'filtered', 'not_scheduled') "
        "GROUP BY event_ai_analysis_id, market_event_id), "
        "gaps AS ("
        "SELECT ca.* FROM candidate_analyses ca "
        "LEFT JOIN sent_delivery sd ON sd.event_ai_analysis_id = ca.id "
        "OR (sd.event_ai_analysis_id IS NULL AND sd.market_event_id = ca.market_event_id) "
        "LEFT JOIN explained_outcomes eo ON eo.event_ai_analysis_id = ca.id "
        "OR (eo.event_ai_analysis_id IS NULL AND eo.market_event_id = ca.market_event_id) "
        "WHERE coalesce(sd.sent_count, 0) = 0 AND coalesce(eo.explained_count, 0) = 0) "
        "SELECT 'should_alert_true_without_delivery_explanation' AS anomaly, count(*) AS gap_count, "
        "count(DISTINCT market_event_id) AS affected_market_events, "
        "(array_agg(DISTINCT symbol ORDER BY symbol))[1:10] AS symbols, "
        "(array_agg(jsonb_build_object('event_ai_analysis_id', id, 'market_event_id', market_event_id, "
        "'symbol', symbol, 'event_key', event_key, 'created_at', created_at) "
        "ORDER BY created_at DESC, id DESC))[1:5] AS sample_analyses "
        "FROM gaps HAVING count(*) > 0",
    ),
    DbQuery(
        "alerts_failures",
        "evidence/db/recent_alert_failures.json",
        "SELECT id AS alert_id, symbol, alert_type, market_event_id, market_heartbeat_id, "
        "event_ai_analysis_id, user_id, status, retry_count, left(last_error, 300) AS last_error, "
        "next_retry_at, final_failed_at, created_at, "
        "CASE WHEN lower(coalesce(last_error, error_message, '')) LIKE '%bot was blocked%' "
        "OR lower(coalesce(last_error, error_message, '')) LIKE '%chat not found%' "
        "OR lower(coalesce(last_error, error_message, '')) LIKE '%user is deactivated%' "
        "OR lower(coalesce(last_error, error_message, '')) LIKE '%forbidden%' "
        "THEN 'blocked_user' WHEN status = 'retry_pending' THEN 'retry_pending_actionable' "
        "ELSE 'unexplained_telegram_failure' END AS failure_category "
        "FROM alerts "
        "WHERE created_at >= :since AND created_at < :until "
        "AND (status IN ('failed', 'retry_pending') OR final_failed_at IS NOT NULL) "
        "ORDER BY created_at DESC, id DESC LIMIT :sample_limit",
    ),
    DbQuery(
        "delivery_invariant_checks",
        "evidence/db/anomalies.json",
        "WITH duplicate_deliveries AS ("
        "SELECT 'duplicate_alert_deliveries' AS anomaly, symbol, market_event_id, user_id, count(*) AS count "
        "FROM alerts WHERE market_event_id IS NOT NULL AND created_at >= :since AND created_at < :until "
        "GROUP BY symbol, market_event_id, user_id HAVING count(*) > 1), "
        "events_without_delivery AS ("
        "SELECT 'market_events_without_alert_deliveries' AS anomaly, me.symbol, me.id AS market_event_id, "
        "NULL::integer AS user_id, 1 AS count FROM market_events me LEFT JOIN alerts a "
        "ON a.market_event_id = me.id WHERE me.detected_at >= :since AND me.detected_at < :until "
        "GROUP BY me.id, me.symbol HAVING count(a.id) = 0), "
        "multiple_analysis AS ("
        "SELECT 'multiple_analysis_ids_for_event' AS anomaly, symbol, market_event_id, NULL::integer AS user_id, "
        "count(DISTINCT event_ai_analysis_id) AS count FROM alerts "
        "WHERE market_event_id IS NOT NULL AND event_ai_analysis_id IS NOT NULL "
        "AND created_at >= :since AND created_at < :until "
        "GROUP BY symbol, market_event_id HAVING count(DISTINCT event_ai_analysis_id) > 1) "
        "SELECT * FROM duplicate_deliveries UNION ALL SELECT * FROM events_without_delivery "
        "UNION ALL SELECT * FROM multiple_analysis LIMIT :anomaly_limit",
    ),
    DbQuery(
        "event_alert_duplicate_deliveries_by_market_event",
        "evidence/db/anomalies.json",
        "SELECT user_id, symbol, alert_type, market_event_id, count(*) AS sent_count, "
        "min(created_at) AS first_sent_at, max(created_at) AS last_sent_at, "
        "count(DISTINCT event_ai_analysis_id) FILTER (WHERE event_ai_analysis_id IS NOT NULL) "
        "AS event_ai_analysis_count, "
        "(array_remove(array_agg(DISTINCT event_ai_analysis_id ORDER BY event_ai_analysis_id), NULL))[1:10] "
        "AS event_ai_analysis_ids "
        "FROM alerts WHERE alert_type = 'event_alert' AND status = 'sent' "
        "AND market_event_id IS NOT NULL "
        "AND created_at >= :since AND created_at < :until "
        "GROUP BY user_id, symbol, alert_type, market_event_id HAVING count(*) > 1 "
        "ORDER BY sent_count DESC, last_sent_at DESC LIMIT :anomaly_limit",
    ),
    DbQuery(
        "event_alert_duplicate_deliveries_by_analysis",
        "evidence/db/anomalies.json",
        "SELECT user_id, symbol, alert_type, event_ai_analysis_id, count(*) AS sent_count, "
        "min(created_at) AS first_sent_at, max(created_at) AS last_sent_at "
        "FROM alerts WHERE alert_type = 'event_alert' AND status = 'sent' "
        "AND event_ai_analysis_id IS NOT NULL "
        "AND created_at >= :since AND created_at < :until "
        "GROUP BY user_id, symbol, alert_type, event_ai_analysis_id HAVING count(*) > 1 "
        "ORDER BY sent_count DESC, last_sent_at DESC LIMIT :anomaly_limit",
    ),
    DbQuery(
        "event_alert_event_invariant_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT me.id AS market_event_id, me.symbol, me.event_key, me.event_instance_key, "
        "count(DISTINCT eaa.id) AS attached_event_analysis_count, "
        "count(DISTINCT eaa.id) FILTER (WHERE eaa.status IN ('success', 'completed')) "
        "AS successful_attached_event_analysis_count, "
        "count(DISTINCT a.id) FILTER (WHERE a.status = 'sent') AS sent_delivery_count, "
        "count(DISTINCT ado.id) AS outcome_count "
        "FROM market_events me "
        "LEFT JOIN event_ai_analyses eaa ON eaa.market_event_id = me.id "
        "AND coalesce(eaa.analysis_type, 'event_analysis') = 'event_analysis' "
        "LEFT JOIN alerts a ON a.market_event_id = me.id AND a.alert_type = 'event_alert' "
        "LEFT JOIN alert_delivery_outcomes ado ON ado.market_event_id = me.id "
        "AND ado.alert_type = 'event_alert' "
        "WHERE me.detected_at >= :since AND me.detected_at < :until "
        "GROUP BY me.id, me.symbol, me.event_key, me.event_instance_key "
        "ORDER BY me.id DESC LIMIT :limit",
    ),
    DbQuery(
        "event_alert_same_family_repeats_24h",
        "evidence/db/anomalies.json",
        "WITH sent AS ("
        "SELECT a.user_id, a.symbol, coalesce(ado.semantic_family, me.event_key) AS canonical_event_key, "
        "ado.semantic_family, ado.decision_reason, a.created_at, "
        "substring(a.numeric_context from "
        "'\"analysed_window_change_percent\"\\s*:\\s*\"?(-?[0-9]+(?:\\.[0-9]+)?)\"?')::numeric "
        "AS analysed_window_change_percent, "
        "md5(coalesce(substring(a.numeric_context from "
        "'\"stable_related_news_ids\"\\s*:\\s*(\\[[^\\]]*\\])'), "
        "coalesce(eaa.related_news_ids, '[]'))) AS stable_news_set_hash "
        "FROM alerts a JOIN market_events me ON me.id = a.market_event_id "
        "LEFT JOIN alert_delivery_outcomes ado ON ado.alert_id = a.id "
        "LEFT JOIN event_ai_analyses eaa ON eaa.id = a.event_ai_analysis_id "
        "WHERE a.alert_type = 'event_alert' AND a.status = 'sent' "
        "AND a.created_at >= :since AND a.created_at < :until) "
        "SELECT user_id, symbol, canonical_event_key, semantic_family, count(*) AS sent_count, "
        "min(created_at) AS first_sent_at, max(created_at) AS last_sent_at, "
        "min(analysed_window_change_percent) AS min_analysed_window_change_percent, "
        "max(analysed_window_change_percent) AS max_analysed_window_change_percent, "
        "count(DISTINCT stable_news_set_hash) AS stable_news_set_hash_count, "
        "(array_agg(DISTINCT stable_news_set_hash ORDER BY stable_news_set_hash))[1:10] "
        "AS stable_news_set_hashes, "
        "(array_remove(array_agg(DISTINCT decision_reason ORDER BY decision_reason), NULL))[1:10] "
        "AS decision_reasons "
        "FROM sent GROUP BY user_id, symbol, canonical_event_key, semantic_family "
        "HAVING count(*) > 1 AND max(created_at) - min(created_at) <= interval '24 hours' "
        "ORDER BY sent_count DESC, last_sent_at DESC LIMIT :anomaly_limit",
    ),
    DbQuery(
        "event_alert_same_news_repeats_24h",
        "evidence/db/anomalies.json",
        "WITH sent AS ("
        "SELECT a.user_id, a.symbol, me.event_key, ado.semantic_family, ado.decision_reason, "
        "a.created_at, "
        "md5(coalesce(substring(a.numeric_context from "
        "'\"stable_related_news_ids\"\\s*:\\s*(\\[[^\\]]*\\])'), "
        "coalesce(eaa.related_news_ids, '[]'))) AS stable_related_news_ids_hash "
        "FROM alerts a JOIN market_events me ON me.id = a.market_event_id "
        "LEFT JOIN alert_delivery_outcomes ado ON ado.alert_id = a.id "
        "LEFT JOIN event_ai_analyses eaa ON eaa.id = a.event_ai_analysis_id "
        "WHERE a.alert_type = 'event_alert' AND a.status = 'sent' "
        "AND a.created_at >= :since AND a.created_at < :until) "
        "SELECT user_id, symbol, stable_related_news_ids_hash, count(*) AS sent_count, "
        "min(created_at) AS first_sent_at, max(created_at) AS last_sent_at, "
        "(array_agg(DISTINCT event_key ORDER BY event_key))[1:10] AS related_event_keys, "
        "(array_remove(array_agg(DISTINCT semantic_family ORDER BY semantic_family), NULL))[1:10] "
        "AS related_semantic_families, "
        "(array_remove(array_agg(DISTINCT decision_reason ORDER BY decision_reason), NULL))[1:10] "
        "AS decision_reasons "
        "FROM sent WHERE stable_related_news_ids_hash != md5('[]') "
        "GROUP BY user_id, symbol, stable_related_news_ids_hash "
        "HAVING count(*) > 1 AND max(created_at) - min(created_at) <= interval '24 hours' "
        "ORDER BY sent_count DESC, last_sent_at DESC LIMIT :anomaly_limit",
    ),
    DbQuery(
        "event_alert_similar_context_reuse",
        "evidence/db/aggregate_metrics.json",
        "SELECT symbol, coalesce(semantic_family, 'unknown') AS semantic_family, "
        "count(*) AS similar_context_reused_count, "
        "count(*) FILTER (WHERE decision_stage = 'pre_llm') AS pre_llm_reused_count, "
        "count(*) FILTER (WHERE market_event_id IS NULL) AS eventless_reused_count, "
        "count(*) FILTER (WHERE event_ai_analysis_id IS NULL) AS llm_skipped_count, "
        "count(DISTINCT context_fingerprint) AS context_fingerprint_count, "
        "max(created_at) AS latest_reuse_at "
        "FROM alert_delivery_outcomes "
        "WHERE alert_type = 'event_alert' "
        "AND created_at >= :since AND created_at < :until "
        "AND decision_reason = 'similar_context_reused' "
        "GROUP BY symbol, coalesce(semantic_family, 'unknown') "
        "ORDER BY similar_context_reused_count DESC, symbol, semantic_family LIMIT :limit",
    ),
    DbQuery(
        "alert_delivery_outcome_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT coalesce(status, 'unknown') AS status, coalesce(reason_code, 'unknown') AS reason_code, "
        "coalesce(decision_stage, 'unknown') AS decision_stage, "
        "coalesce(decision_reason, 'unknown') AS decision_reason, "
        "count(*) AS outcomes, count(*) FILTER (WHERE reason_code IS NULL OR reason_code = '') "
        "AS reason_code_unknown_count, "
        "count(*) FILTER (WHERE decision_reason IS NULL OR decision_reason = '') "
        "AS decision_reason_unknown_count, "
        "count(*) FILTER (WHERE market_event_id IS NULL) AS market_event_id_null_count, "
        "count(*) FILTER (WHERE market_event_id IS NOT NULL) AS market_event_id_present_count, "
        "count(*) FILTER (WHERE event_ai_analysis_id IS NULL) AS event_ai_analysis_id_null_count, "
        "count(*) FILTER (WHERE event_ai_analysis_id IS NOT NULL) AS event_ai_analysis_id_present_count, "
        "count(*) FILTER (WHERE status = 'delivered') AS delivered_count, "
        "count(*) FILTER (WHERE status = 'suppressed') AS suppressed_count, "
        "count(*) FILTER (WHERE status = 'filtered') AS filtered_count, "
        "count(*) FILTER (WHERE status = 'failed') AS failed_count, "
        "count(*) FILTER (WHERE status = 'rate_limited') AS rate_limited_count, "
        "count(*) FILTER (WHERE reason_code = 'no_recipients') AS no_eligible_recipients_count, "
        "count(*) FILTER (WHERE reason_code = 'already_delivered') AS already_delivered_count, "
        "count(*) FILTER (WHERE reason_code = 'telegram_send_failed') AS telegram_send_failed_count, "
        "count(*) FILTER (WHERE reason_code = 'telegram_bot_blocked') AS telegram_bot_blocked_count, "
        "count(*) FILTER (WHERE reason_code = 'llm_rate_limited') AS llm_rate_limited_count, "
        "count(*) FILTER (WHERE reason_code = 'llm_invalid_response') AS llm_invalid_response_count, "
        "count(*) FILTER (WHERE decision_reason = 'news_only_rejected') AS news_only_rejected_count, "
        "count(*) FILTER (WHERE decision_reason = 'llm_should_alert') AS llm_should_alert_count, "
        "count(*) FILTER (WHERE decision_reason = 'llm_no_alert') AS llm_no_alert_count, "
        "count(*) FILTER (WHERE decision_reason = 'semantic_cooldown_suppressed') "
        "AS semantic_cooldown_suppressed_count, "
        "count(*) FILTER (WHERE decision_reason = 'similar_context_reused') "
        "AS similar_context_reused_count, "
        "count(*) FILTER (WHERE decision_reason = 'allowed_market_context_changed') "
        "AS allowed_market_context_changed_count, "
        "count(*) FILTER (WHERE decision_stage = 'pre_llm' "
        "AND decision_reason = 'similar_context_reused') "
        "AS pre_llm_similar_context_reused_count, "
        "count(*) FILTER (WHERE status = 'delivered' AND decision_reason IS NOT NULL) "
        "AS delivered_with_decision_reason_count "
        "FROM alert_delivery_outcomes WHERE created_at >= :since AND created_at < :until "
        "GROUP BY coalesce(status, 'unknown'), coalesce(reason_code, 'unknown'), "
        "coalesce(decision_stage, 'unknown'), coalesce(decision_reason, 'unknown') "
        "ORDER BY outcomes DESC, status, reason_code, decision_stage, decision_reason LIMIT :limit",
    ),
    DbQuery(
        "event_alert_possible_action_quality",
        "evidence/db/aggregate_metrics.json",
        "SELECT count(*) AS event_alert_actions, "
        "count(*) FILTER (WHERE possible_action ~* "
        "'^(monitor price movement|monitor market developments|monitor market sentiment|keep watching|monitor risk)\\.?$') "
        "AS generic_possible_action_count "
        "FROM event_ai_analyses WHERE created_at >= :since AND created_at < :until "
        "AND coalesce(analysis_type, 'event_analysis') = 'event_analysis' "
        "AND should_alert = true",
    ),
    DbQuery(
        "market_events_without_delivery_classification",
        "evidence/db/anomalies.json",
        "WITH events_without_delivery AS ("
        "SELECT me.id AS market_event_id, me.symbol, me.event_type, me.event_key, me.detected_at "
        "FROM market_events me LEFT JOIN alerts a ON a.market_event_id = me.id "
        "WHERE me.detected_at >= :since AND me.detected_at < :until "
        "GROUP BY me.id, me.symbol, me.event_type, me.event_key, me.detected_at "
        "HAVING count(a.id) = 0), "
        "latest_analysis AS ("
        "SELECT DISTINCT ON (market_event_id) market_event_id, id AS analysis_id, status, "
        "should_alert, error_reason, created_at AS analysis_created_at "
        "FROM event_ai_analyses WHERE market_event_id IS NOT NULL "
        "ORDER BY market_event_id, created_at DESC, id DESC), "
        "recipient_summary AS ("
        "SELECT ucs.symbol, "
        "count(DISTINCT u.id) FILTER ("
        "WHERE u.telegram_chat_id IS NOT NULL AND u.is_active = true AND u.bot_blocked = false "
        "AND ucs.is_enabled = true "
        "AND (ucs.symbol = 'btc' OR ups.active_until >= :until)"
        ") AS likely_eligible_recipients, "
        "count(DISTINCT u.id) FILTER ("
        "WHERE u.telegram_chat_id IS NOT NULL AND u.is_active = true AND u.bot_blocked = false "
        "AND ucs.is_enabled = true AND ucs.symbol <> 'btc' "
        "AND (ups.active_until IS NULL OR ups.active_until < :until)"
        ") AS product_gated_users, "
        "count(DISTINCT u.id) FILTER (WHERE ucs.is_enabled = true) AS enabled_watchlist_users "
        "FROM user_coin_subscriptions ucs "
        "JOIN users u ON u.id = ucs.user_id "
        "LEFT JOIN user_premium_subscriptions ups ON ups.user_id = u.id "
        "GROUP BY ucs.symbol), "
        "settings AS ("
        f"SELECT {EFFECTIVE_EVENT_ANALYSIS_INTERVAL_SECONDS} AS cooldown_seconds), "
        "recent_event_alerts AS ("
        "SELECT e.market_event_id, max(a.created_at) AS recent_sent_at "
        "FROM events_without_delivery e JOIN alerts a ON lower(a.symbol) = lower(e.symbol) "
        "AND a.alert_type = 'event_alert' AND a.status = 'sent' "
        "AND a.created_at < e.detected_at "
        "AND a.created_at >= e.detected_at - ((SELECT cooldown_seconds FROM settings) * interval '1 second') "
        "GROUP BY e.market_event_id), "
        "outcome_summary AS ("
        "SELECT e.market_event_id, "
        "count(*) FILTER (WHERE ado.reason_code = 'no_recipients') AS no_recipient_outcomes, "
        "count(*) FILTER (WHERE ado.reason_code = 'premium_required') AS premium_required_outcomes, "
        "count(*) FILTER (WHERE ado.reason_code IN ('cooldown_active', 'similar_event_suppressed', 'similar_context_reused')) AS cooldown_outcomes, "
        "count(*) FILTER (WHERE ado.status IN ('failed', 'rate_limited')) AS failed_or_rate_limited_outcomes "
        "FROM events_without_delivery e JOIN alert_delivery_outcomes ado "
        "ON ado.market_event_id = e.market_event_id "
        "OR (ado.market_event_id IS NULL AND ado.event_ai_analysis_id IN ("
        "SELECT id FROM event_ai_analyses WHERE market_event_id = e.market_event_id"
        ")) "
        "WHERE ado.alert_type = 'event_alert' "
        "GROUP BY e.market_event_id), "
        "classified AS ("
        "SELECT e.market_event_id, e.symbol, e.event_type, e.event_key, e.detected_at, "
        "la.analysis_id, la.status AS analysis_status, la.should_alert, la.error_reason, "
        "rea.recent_sent_at, "
        "coalesce(os.no_recipient_outcomes, 0) AS no_recipient_outcomes, "
        "coalesce(os.premium_required_outcomes, 0) AS premium_required_outcomes, "
        "coalesce(os.cooldown_outcomes, 0) AS cooldown_outcomes, "
        "coalesce(os.failed_or_rate_limited_outcomes, 0) AS failed_or_rate_limited_outcomes, "
        "coalesce(rs.likely_eligible_recipients, 0) AS likely_eligible_recipients, "
        "coalesce(rs.product_gated_users, 0) AS product_gated_users, "
        "coalesce(rs.enabled_watchlist_users, 0) AS enabled_watchlist_users, "
        "CASE "
        "WHEN la.analysis_id IS NULL THEN 'unknown_no_analysis' "
        "WHEN la.status NOT IN ('success', 'completed', 'no_alert') "
        "OR lower(coalesce(la.error_reason, '')) LIKE '%rate%' THEN 'llm_failure_or_rate_limit' "
        "WHEN la.should_alert = false THEN 'expected_should_alert_false' "
        "WHEN la.should_alert IS NULL THEN 'unknown_should_alert_null' "
        "WHEN la.should_alert = true AND coalesce(os.no_recipient_outcomes, 0) > 0 THEN 'expected_no_eligible_recipients' "
        "WHEN la.should_alert = true AND coalesce(os.premium_required_outcomes, 0) > 0 THEN 'expected_product_gating_possible' "
        "WHEN la.should_alert = true AND coalesce(os.cooldown_outcomes, 0) > 0 THEN 'expected_backend_cooldown_active' "
        "WHEN la.should_alert = true AND coalesce(os.failed_or_rate_limited_outcomes, 0) > 0 THEN 'expected_failed_or_rate_limited_outcome' "
        "WHEN la.should_alert = true AND coalesce(rs.likely_eligible_recipients, 0) = 0 "
        "AND lower(e.symbol) <> 'btc' AND coalesce(rs.product_gated_users, 0) > 0 THEN 'expected_product_gating_possible' "
        "WHEN la.should_alert = true AND rea.recent_sent_at IS NOT NULL THEN 'expected_backend_cooldown_active' "
        "WHEN la.should_alert = true AND coalesce(rs.likely_eligible_recipients, 0) = 0 THEN 'expected_no_eligible_recipients' "
        "WHEN la.should_alert = true AND coalesce(rs.likely_eligible_recipients, 0) > 0 THEN 'delivery_gap_should_alert_true' "
        "ELSE 'unknown' END AS classification "
        "FROM events_without_delivery e "
        "LEFT JOIN latest_analysis la ON la.market_event_id = e.market_event_id "
        "LEFT JOIN recipient_summary rs ON rs.symbol = lower(e.symbol) "
        "LEFT JOIN outcome_summary os ON os.market_event_id = e.market_event_id "
        "LEFT JOIN recent_event_alerts rea ON rea.market_event_id = e.market_event_id) "
        "SELECT classification, count(*) AS events, "
        "count(*) FILTER (WHERE analysis_id IS NOT NULL) AS events_with_analysis, "
        "count(*) FILTER (WHERE should_alert = true) AS should_alert_true, "
        "count(*) FILTER (WHERE should_alert = false) AS should_alert_false, "
        "sum(likely_eligible_recipients) AS likely_eligible_recipient_total, "
        "sum(product_gated_users) AS product_gated_user_total, "
        "(array_agg(jsonb_build_object("
        "'market_event_id', market_event_id, 'symbol', symbol, 'event_type', event_type, "
        "'event_key', event_key, 'detected_at', detected_at, 'analysis_status', analysis_status, "
        "'should_alert', should_alert, 'likely_eligible_recipients', likely_eligible_recipients, "
        "'product_gated_users', product_gated_users, 'recent_sent_at', recent_sent_at, "
        "'outcome_counts', jsonb_build_object('no_recipients', no_recipient_outcomes, "
        "'premium_required', premium_required_outcomes, 'cooldown', cooldown_outcomes, "
        "'failed_or_rate_limited', failed_or_rate_limited_outcomes)"
        ") ORDER BY detected_at DESC, market_event_id DESC))[1:5] AS sample_events "
        "FROM classified GROUP BY classification ORDER BY events DESC LIMIT :anomaly_limit",
    ),
    DbQuery(
        "market_heartbeats_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT h.symbol, h.status, count(*) AS heartbeats, max(h.generated_at) AS latest_generated_at, "
        "count(a.id) FILTER (WHERE a.status = 'sent') AS sent_deliveries, "
        "count(a.id) FILTER (WHERE a.status IN ('failed', 'retry_pending')) AS failed_deliveries "
        "FROM market_heartbeats h LEFT JOIN alerts a ON a.market_heartbeat_id = h.id "
        "WHERE h.generated_at >= :since AND h.generated_at < :until "
        "GROUP BY h.symbol, h.status ORDER BY h.symbol, h.status",
    ),
    DbQuery(
        "market_heartbeats_freshness",
        "evidence/db/aggregate_metrics.json",
        "WITH symbols(symbol) AS ("
        f"{ACTIVE_SYMBOL_VALUES_SQL}"
        "), latest AS ("
        "SELECT DISTINCT ON (lower(symbol)) lower(symbol) AS symbol, status, generated_at "
        "FROM market_heartbeats WHERE lower(symbol) IN (SELECT symbol FROM symbols) "
        "ORDER BY lower(symbol), generated_at DESC, id DESC"
        ") "
        "SELECT s.symbol, l.status AS latest_status, l.generated_at AS latest_generated_at, "
        "extract(epoch FROM (:until - l.generated_at)) AS age_seconds "
        "FROM symbols s LEFT JOIN latest l ON l.symbol = s.symbol ORDER BY s.symbol LIMIT :limit",
    ),
    DbQuery(
        "market_heartbeat_delivery_freshness",
        "evidence/db/aggregate_metrics.json",
        "SELECT symbol, user_id, count(*) AS deliveries, "
        "max(created_at) FILTER (WHERE status = 'sent') AS latest_sent_at, "
        "count(*) FILTER (WHERE status = 'sent') AS sent_count, "
        "count(*) FILTER (WHERE status IN ('failed', 'retry_pending') OR final_failed_at IS NOT NULL) "
        "AS failed_count, "
        "count(*) FILTER (WHERE coalesce(message, '') ~* '(^|[^a-z0-9])n/a([^a-z0-9]|$)' "
        "OR coalesce(message, '') ~* '(^|[^a-z0-9])unknown([^a-z0-9]|$)' "
        "OR coalesce(message, '') ~* '(^|[^a-z0-9])unavailable([^a-z0-9]|$)' "
        "OR coalesce(message, '') ~* '(^|[^a-z0-9])null([^a-z0-9]|$)') "
        "AS placeholder_quality_count "
        "FROM alerts WHERE (alert_type = 'market_heartbeat' OR market_heartbeat_id IS NOT NULL) "
        "AND created_at >= :since AND created_at < :until "
        "GROUP BY symbol, user_id ORDER BY latest_sent_at DESC NULLS LAST, symbol LIMIT :limit",
    ),
    DbQuery(
        "market_reports_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT report_type, status, count(*) AS reports, max(generated_at) AS latest_generated_at, "
        "max(expires_at) AS latest_expires_at FROM market_reports "
        "WHERE generated_at >= :since AND generated_at < :until "
        "GROUP BY report_type, status ORDER BY report_type, status",
    ),
    DbQuery(
        "market_reports_freshness",
        "evidence/db/aggregate_metrics.json",
        # Ops freshness thresholds are runtime cadence plus scheduler/reporting grace.
        # They do not change the report generation cadence. Expected regeneration
        # semantics: the bot's scheduled refresh regenerates each report at its runtime
        # interval (daily 4h, weekly 24h), and on-command /dailyreport or /weeklyreport
        # generation may refresh the cache at any time; the threshold adds 1h grace on
        # top of the runtime interval for scheduler jitter and reporting lag.
        "WITH report_types(report_type, max_age_seconds, runtime_interval_seconds) AS ("
        f"{REPORT_FRESHNESS_VALUES_SQL}"
        "), latest AS ("
        "SELECT DISTINCT ON (report_type) report_type, status, generated_at, expires_at "
        "FROM market_reports ORDER BY report_type, generated_at DESC, id DESC"
        "), period_counts AS ("
        "SELECT report_type, count(*) AS reports_in_period, "
        "count(*) FILTER (WHERE status = 'completed') AS completed_in_period, "
        "count(*) FILTER (WHERE status != 'completed') AS failed_in_period "
        "FROM market_reports WHERE generated_at >= :since AND generated_at < :until "
        "GROUP BY report_type"
        ") "
        "SELECT rt.report_type, rt.max_age_seconds, rt.runtime_interval_seconds, "
        "l.status AS latest_status, "
        "l.generated_at AS latest_generated_at, l.expires_at AS latest_expires_at, "
        "extract(epoch FROM (:until - l.generated_at)) AS age_seconds, "
        "l.generated_at + make_interval(secs => rt.runtime_interval_seconds) "
        "AS expected_next_scheduled_refresh_at, "
        "coalesce(pc.reports_in_period, 0) AS reports_in_period, "
        "coalesce(pc.completed_in_period, 0) AS completed_in_period, "
        "coalesce(pc.failed_in_period, 0) AS failed_in_period "
        "FROM report_types rt LEFT JOIN latest l ON l.report_type = rt.report_type "
        "LEFT JOIN period_counts pc ON pc.report_type = rt.report_type ORDER BY rt.report_type",
    ),
    DbQuery(
        "llm_usage_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT provider, model, call_type, status, coalesce(symbol, 'UNKNOWN') AS symbol, "
        "count(*) AS calls, sum(prompt_tokens) AS prompt_tokens, "
        "sum(completion_tokens) AS completion_tokens, sum(total_tokens) AS total_tokens, "
        "max(created_at) AS latest_at, "
        "count(*) FILTER (WHERE status LIKE '%rate_limit%' OR retry_after IS NOT NULL) AS rate_limit_count, "
        "count(*) FILTER (WHERE error_reason = 'timeout') AS timeout_count, "
        "count(*) FILTER (WHERE error_reason IN ('invalid_json', 'schema_validation_failed')) "
        "AS invalid_json_schema_error_count, "
        "max(retry_after) AS max_retry_after FROM llm_usage_logs "
        "WHERE created_at >= :since AND created_at < :until "
        "GROUP BY provider, model, call_type, status, coalesce(symbol, 'UNKNOWN') "
        "ORDER BY calls DESC LIMIT :limit",
    ),
    DbQuery(
        "llm_failure_category_summary",
        "evidence/db/aggregate_metrics.json",
        "WITH classified AS ("
        "SELECT call_type, "
        "CASE "
        "WHEN status IN ('success', 'completed') THEN 'successful' "
        "WHEN status = 'skipped_due_to_rate_limit' "
        "OR error_reason = 'rate_limit_backoff_active' THEN 'active_backoff' "
        "WHEN status = 'skipped_due_to_circuit_breaker' "
        "OR error_reason = 'provider_circuit_broken' THEN 'circuit_breaker' "
        "WHEN status = 'rate_limit' OR retry_after IS NOT NULL "
        "OR error_reason IN ('rate_limit', 'rate_limited') THEN 'provider_rate_limit' "
        "WHEN error_reason = 'provider_model_error' THEN 'provider_model_error' "
        "WHEN error_reason IN ('schema_validation_failed', 'invalid_json', "
        "'provider_json_validate_failed') THEN 'schema_invalid_output' "
        "WHEN error_reason IN ('provider_bad_request', 'provider_4xx') THEN 'bad_request' "
        "WHEN error_reason = 'timeout' THEN 'timeout' "
        "WHEN error_reason IN ('network_error', 'provider_error', 'provider_5xx', "
        "'empty_response') THEN 'network_error' "
        "WHEN error_reason IN ('auth_error', 'config_missing') THEN 'provider_auth_config' "
        "WHEN error_reason LIKE 'provider_%' THEN 'provider_other' "
        "ELSE 'other' END AS failure_category "
        "FROM llm_usage_logs WHERE created_at >= :since AND created_at < :until"
        ") "
        "SELECT call_type, failure_category, count(*) AS calls "
        "FROM classified GROUP BY call_type, failure_category "
        "ORDER BY calls DESC, call_type, failure_category LIMIT :limit",
    ),
    DbQuery(
        "news_freshness_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT "
        "(SELECT max(fetched_at) FROM news_items) AS latest_fetched_at, "
        "(SELECT count(*) FROM news_items WHERE fetched_at >= "
        "CAST(:until AS timestamptz) - interval '24 hours' "
        "AND fetched_at < CAST(:until AS timestamptz) "
        "AND coalesce(is_duplicate, false) = false AND coalesce(is_noise, false) = false) "
        "AS usable_news_count_24h, "
        "(SELECT count(*) FROM news_items WHERE fetched_at >= "
        "CAST(:until AS timestamptz) - interval '24 hours' "
        "AND fetched_at < CAST(:until AS timestamptz) "
        "AND coalesce(is_duplicate, false) = true) AS duplicate_filtered_count_24h, "
        "(SELECT count(*) FROM news_items WHERE fetched_at >= "
        "CAST(:until AS timestamptz) - interval '24 hours' "
        "AND fetched_at < CAST(:until AS timestamptz) "
        "AND coalesce(is_noise, false) = true) AS noise_filtered_count_24h, "
        "(SELECT llm_status FROM news_items WHERE llm_status IS NOT NULL "
        "ORDER BY fetched_at DESC, id DESC LIMIT 1) AS latest_news_intelligence_status",
    ),
    DbQuery(
        "news_items_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT llm_status, impact_level, is_duplicate, is_noise, is_alert_worthy, count(*) AS items "
        "FROM news_items WHERE fetched_at >= :since AND fetched_at < :until "
        "GROUP BY llm_status, impact_level, is_duplicate, is_noise, is_alert_worthy "
        "ORDER BY items DESC LIMIT :limit",
    ),
    DbQuery(
        "news_intelligence_budget_summary",
        "evidence/db/aggregate_metrics.json",
        "WITH classified AS ("
        "SELECT "
        "CASE "
        "WHEN llm_status = 'success' THEN 'successful' "
        "WHEN llm_status = 'skipped_budget' THEN 'skipped_budget' "
        "WHEN llm_status = 'failed' THEN 'failed' "
        "WHEN llm_status IS NULL OR llm_status = 'pending' THEN 'pending' "
        "ELSE 'unknown' END AS outcome_category, "
        "CASE "
        "WHEN impact_level IN ('critical', 'high') THEN 'high' "
        "WHEN impact_level = 'medium' THEN 'medium' "
        "ELSE 'low_or_null' END AS impact_bucket, "
        "fetched_at "
        "FROM news_items WHERE fetched_at >= :since AND fetched_at < :until"
        ") "
        "SELECT outcome_category, impact_bucket, count(*) AS items, "
        "count(*) FILTER ("
        "WHERE fetched_at >= CAST(:until AS timestamptz) - interval '24 hours' "
        "AND fetched_at < CAST(:until AS timestamptz)"
        ") AS recent_24h_items "
        "FROM classified GROUP BY outcome_category, impact_bucket "
        "ORDER BY items DESC, outcome_category, impact_bucket LIMIT :limit",
    ),
    DbQuery(
        "news_items_recent_high_impact",
        "evidence/db/recent_news_failures.json",
        "SELECT id, title, source, url, primary_symbol, category, impact_level, llm_status, "
        "left(llm_error, 300) AS llm_error, fetched_at FROM news_items "
        "WHERE fetched_at >= :since AND fetched_at < :until "
        "AND (llm_status != 'success' OR impact_level IN ('high', 'critical')) "
        "ORDER BY fetched_at DESC, id DESC LIMIT :sample_limit",
    ),
    DbQuery(
        "seen_news_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT count(*) AS seen_news_count, min(seen_at) AS oldest_seen_at, max(seen_at) AS newest_seen_at "
        "FROM seen_news",
    ),
    DbQuery(
        "blocked_users_still_active",
        "evidence/db/anomalies.json",
        "SELECT 'blocked_users_still_active' AS anomaly, id AS user_id, bot_blocked, is_active, blocked_at "
        "FROM users WHERE bot_blocked = true AND is_active = true LIMIT :anomaly_limit",
    ),
)


def validate_read_only_queries(extra: dict[str, str] | None = None) -> list[str]:
    """Assert every collector SQL statement is a read-only, single, unterminated statement.

    ``extra`` carries statements that live outside ``QUERIES`` — notably the alert-evidence
    statement in the collector module, which is the largest query the collector runs and was
    previously not covered by this guard at all.
    """
    errors: list[str] = []
    named_sql = [(query.name, query.sql) for query in QUERIES]
    named_sql.extend((name, sql) for name, sql in (extra or {}).items())
    for name, sql in named_sql:
        normalized = sql.strip().lower()
        if not (normalized.startswith("select") or normalized.startswith("with")):
            errors.append(f"{name} is not read-only")
        if ";" in normalized:
            errors.append(f"{name} contains a semicolon")
    return errors
