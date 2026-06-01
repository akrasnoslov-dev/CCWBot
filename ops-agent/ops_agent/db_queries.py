# ruff: noqa: E501
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DbQuery:
    name: str
    evidence_file: str
    sql: str


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
        "watchlist_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT symbol, is_enabled, count(*) AS users FROM user_coin_subscriptions "
        "GROUP BY symbol, is_enabled ORDER BY symbol, is_enabled",
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
        "payments_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT provider, currency, status, count(*) AS payments, sum(amount) AS amount_total "
        "FROM payments WHERE created_at >= :since AND created_at < :until "
        "GROUP BY provider, currency, status ORDER BY provider, currency, status",
    ),
    DbQuery(
        "price_state_current",
        "evidence/db/aggregate_metrics.json",
        "SELECT symbol, last_price, last_24h_change, last_7d_change, last_checked_at, last_alert_at "
        "FROM price_state ORDER BY symbol",
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
        "event_ai_analysis_samples",
        "evidence/db/recent_llm_failures.json",
        "SELECT id, market_event_id, symbol, analysis_type, provider, model, status, should_alert, "
        "error_reason, left(error_message, 300) AS error_message, created_at "
        "FROM event_ai_analyses WHERE created_at >= :since AND created_at < :until "
        "AND status NOT IN ('success', 'completed') ORDER BY created_at DESC, id DESC LIMIT :sample_limit",
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
        "alerts_failures",
        "evidence/db/recent_alert_failures.json",
        "SELECT id AS alert_id, symbol, alert_type, market_event_id, market_heartbeat_id, "
        "event_ai_analysis_id, user_id, status, retry_count, left(last_error, 300) AS last_error, "
        "next_retry_at, final_failed_at, created_at FROM alerts "
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
        "market_reports_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT report_type, status, count(*) AS reports, max(generated_at) AS latest_generated_at, "
        "max(expires_at) AS latest_expires_at FROM market_reports "
        "WHERE generated_at >= :since AND generated_at < :until "
        "GROUP BY report_type, status ORDER BY report_type, status",
    ),
    DbQuery(
        "llm_usage_summary",
        "evidence/db/aggregate_metrics.json",
        "SELECT provider, model, call_type, status, count(*) AS calls, sum(total_tokens) AS total_tokens, "
        "count(*) FILTER (WHERE status LIKE '%rate_limit%' OR retry_after IS NOT NULL) AS rate_limit_count, "
        "max(retry_after) AS max_retry_after FROM llm_usage_logs "
        "WHERE created_at >= :since AND created_at < :until "
        "GROUP BY provider, model, call_type, status ORDER BY calls DESC LIMIT :limit",
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
        "duplicate_provider_payment_ids",
        "evidence/db/anomalies.json",
        "SELECT 'duplicate_provider_payment_ids' AS anomaly, provider, provider_payment_id, count(*) AS count "
        "FROM payments GROUP BY provider, provider_payment_id HAVING count(*) > 1 LIMIT :anomaly_limit",
    ),
    DbQuery(
        "blocked_users_still_active",
        "evidence/db/anomalies.json",
        "SELECT 'blocked_users_still_active' AS anomaly, id AS user_id, bot_blocked, is_active, blocked_at "
        "FROM users WHERE bot_blocked = true AND is_active = true LIMIT :anomaly_limit",
    ),
)


def validate_read_only_queries() -> list[str]:
    errors: list[str] = []
    for query in QUERIES:
        normalized = query.sql.strip().lower()
        if not (normalized.startswith("select") or normalized.startswith("with")):
            errors.append(f"{query.name} is not read-only")
        if ";" in normalized:
            errors.append(f"{query.name} contains a semicolon")
    return errors
