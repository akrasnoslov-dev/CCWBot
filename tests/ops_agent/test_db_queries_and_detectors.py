from __future__ import annotations

import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic.config import Config
from ops_agent.collectors import db as db_collector
from ops_agent.collectors.db import ALERT_EVIDENCE_SQL
from ops_agent.config import OpsAgentConfig
from ops_agent.db_queries import (
    ACTIVE_SYMBOLS as OPS_AGENT_ACTIVE_SYMBOLS,
)
from ops_agent.db_queries import (
    DAILY_REPORT_FRESHNESS_GRACE_SECONDS,
    DAILY_REPORT_FRESHNESS_THRESHOLD_SECONDS,
    DAILY_REPORT_RUNTIME_INTERVAL_SECONDS,
    MARKET_DATA_FRESHNESS_GRACE_SECONDS,
    QUERIES,
    REPORT_FRESHNESS_VALUES_SQL,
    WEEKLY_REPORT_FRESHNESS_GRACE_SECONDS,
    WEEKLY_REPORT_FRESHNESS_THRESHOLD_SECONDS,
    WEEKLY_REPORT_RUNTIME_INTERVAL_SECONDS,
    DbQuery,
    validate_read_only_queries,
)
from ops_agent.detectors import run_detectors
from ops_agent.redaction import RedactionReport, ReferenceMapper
from ops_agent.schemas import Period
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_all_db_queries_are_read_only_and_parameterized():
    assert validate_read_only_queries() == []
    assert all(query.sql.strip().lower().startswith(("select", "with")) for query in QUERIES)
    assert any(":since" in query.sql for query in QUERIES)
    assert ALERT_EVIDENCE_SQL.strip().lower().startswith(("select", "with"))
    assert ";" not in ALERT_EVIDENCE_SQL
    assert ":since" in ALERT_EVIDENCE_SQL


@pytest.mark.asyncio
async def test_all_ops_agent_queries_explain_against_migrated_postgres_schema():
    database_url = os.getenv("OPS_AGENT_POSTGRES_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set OPS_AGENT_POSTGRES_TEST_DATABASE_URL to a migrated local PostgreSQL DB")
    if not database_url.startswith("postgresql+asyncpg://"):
        pytest.fail("OPS_AGENT_POSTGRES_TEST_DATABASE_URL must use postgresql+asyncpg")

    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    alembic_config.attributes["database_url"] = database_url
    alembic_config.attributes["configure_logger"] = False
    await asyncio.to_thread(command.upgrade, alembic_config, "head")

    params = _query_params()
    engine = create_async_engine(database_url, future=True)
    try:
        async with engine.connect() as connection:
            for query in QUERIES:
                await connection.execute(text(f"EXPLAIN {query.sql}"), params)
            await connection.execute(text(f"EXPLAIN {ALERT_EVIDENCE_SQL}"), params)
            await _assert_malformed_numeric_context_is_safe(connection, params)
            await connection.rollback()
    finally:
        await engine.dispose()


def _query_params() -> dict[str, object]:
    return {
        "since": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "until": datetime(2026, 6, 2, tzinfo=timezone.utc),
        "limit": 100,
        "sample_limit": 20,
        "anomaly_limit": 20,
        "duplicate_bucket_minutes": 15,
        "alert_evidence_limit": 100,
    }


async def _assert_malformed_numeric_context_is_safe(connection, params: dict[str, object]) -> None:
    await connection.execute(
        text(
            """
            INSERT INTO users (
                id, telegram_user_id, telegram_chat_id, role, is_active, bot_blocked,
                alert_frequency_seconds, created_at, updated_at
            )
            VALUES (
                900001, 9900001, 9900001, 'user', true, false, 14400,
                :since, :since
            )
            """
        ),
        params,
    )
    await connection.execute(
        text(
            """
            INSERT INTO market_events (
                id, symbol, event_type, event_key, event_instance_key, price,
                previous_price, price_change_percent, detected_at, created_at
            )
            VALUES
                (
                    900001, 'BTC', 'event_alert', 'btc_price_downtrend',
                    'ops-agent-malformed-context-a', 65000, 66000, -1.5,
                    :since, :since
                ),
                (
                    900002, 'BTC', 'event_alert', 'btc_price_downtrend',
                    'ops-agent-malformed-context-b', 64000, 65000, -1.6,
                    :since, :since
                )
            """
        ),
        params,
    )
    await connection.execute(
        text(
            """
            INSERT INTO event_ai_analyses (
                id, market_event_id, analysis_id, symbol, analysis_type, provider, model,
                input_hash, should_alert, related_news_ids, status, plain_text, created_at
            )
            VALUES
                (
                    900001, 900001, 'ops_agent_contract_a', 'BTC', 'event_analysis',
                    'groq', 'contract-model', 'ops-agent-contract-a', true, '["n1"]',
                    'success', 'Sanitized text. Not financial advice.', :since
                ),
                (
                    900002, 900002, 'ops_agent_contract_b', 'BTC', 'event_analysis',
                    'groq', 'contract-model', 'ops-agent-contract-b', true, '["n1"]',
                    'success', 'Sanitized text. Not financial advice.', :since
                )
            """
        ),
        params,
    )
    await connection.execute(
        text(
            """
            INSERT INTO alerts (
                id, symbol, alert_type, message, sent_to_chat_id, market_event_id,
                event_ai_analysis_id, user_id, status, retry_count, numeric_context,
                created_at
            )
            VALUES
                (
                    900001, 'BTC', 'event_alert', 'Sanitized text. Not financial advice.',
                    9900001, 900001, 900001, 900001, 'sent', 0, '{bad json',
                    :since
                ),
                (
                    900002, 'BTC', 'event_alert', 'Sanitized text. Not financial advice.',
                    9900001, 900002, 900002, 900001, 'sent', 0, '{bad json',
                    :since
                )
            """
        ),
        params,
    )
    await connection.execute(
        text(
            """
            INSERT INTO alert_delivery_outcomes (
                id, symbol, alert_type, market_event_id, event_ai_analysis_id, alert_id,
                user_id, sent_to_chat_id, status, reason_code, recipient_considered,
                recipient_eligible, event_instance_key, semantic_family, created_at
            )
            VALUES
                (
                    900001, 'BTC', 'event_alert', 900001, 900001, 900001, 900001,
                    9900001, 'delivered', 'delivered', true, true,
                    'ops-agent-malformed-context-a', 'price_downtrend', :since
                ),
                (
                    900002, 'BTC', 'event_alert', 900002, 900002, 900002, 900001,
                    9900001, 'delivered', 'delivered', true, true,
                    'ops-agent-malformed-context-b', 'price_downtrend', :since
                )
            """
        ),
        params,
    )

    for query_name in (
        "event_alert_same_family_repeats_24h",
        "event_alert_same_news_repeats_24h",
    ):
        query = next(query for query in QUERIES if query.name == query_name)
        result = await connection.execute(text(query.sql), params)
        rows = result.fetchall()
        assert rows, f"{query_name} should handle malformed numeric_context and return rows"


def test_price_state_query_uses_existing_price_state_columns_only():
    price_state_query = next(query for query in QUERIES if query.name == "price_state_current")

    assert "last_7d_change" not in price_state_query.sql
    assert "('btc'), ('eth'), ('gram'), ('sol')" in price_state_query.sql
    assert "lower(symbol) IN" in price_state_query.sql


def test_ops_agent_classifies_legacy_symbols_and_blocked_failures_separately():
    query_names = {query.name: query for query in QUERIES}

    assert "legacy_inactive_price_state" in query_names
    assert "legacy_inactive_symbol" in query_names["legacy_inactive_price_state"].sql
    assert "failure_category" in query_names["alerts_failures"].sql
    assert "blocked_user" in query_names["alerts_failures"].sql
    assert "retry_pending_actionable" in query_names["alerts_failures"].sql
    assert "unexplained_telegram_failure" in query_names["alerts_failures"].sql
    assert "telegram_delivery_failure_summary" in query_names
    assert "failed_or_retry_pending_total" in query_names[
        "telegram_delivery_failure_summary"
    ].sql


def test_ops_agent_queries_include_hardened_anomaly_evidence():
    query_names = {query.name for query in QUERIES}

    assert "premium_payment_inconsistencies" in query_names
    assert "market_reports_freshness" in query_names
    assert "market_heartbeats_freshness" in query_names
    assert "event_ai_analysis_invariant_checks" in query_names
    assert "event_alert_llm_estimates" in query_names
    assert "user_impact_summary" in query_names
    assert "delivery_funnel" in query_names
    assert "alert_quality_summary" in query_names
    assert "event_alert_delivery_explanation_gaps" in query_names
    assert "event_alert_duplicate_deliveries_by_market_event" in query_names
    assert "event_alert_duplicate_deliveries_by_analysis" in query_names
    assert "event_alert_event_invariant_summary" in query_names
    assert "event_alert_same_family_repeats_24h" in query_names
    assert "event_alert_same_news_repeats_24h" in query_names
    assert "alert_delivery_outcome_summary" in query_names
    assert "market_heartbeat_delivery_freshness" in query_names
    assert "news_intelligence_budget_summary" in query_names
    assert "llm_failure_category_summary" in query_names
    assert "event_analysis_logical_outcome_summary" in query_names
    no_delivery = next(
        query for query in QUERIES if query.name == "market_events_without_delivery_classification"
    )
    assert "outcome_summary AS" in no_delivery.sql
    assert "expected_no_eligible_recipients" in no_delivery.sql
    assert "expected_product_gating_possible" in no_delivery.sql
    assert "news_freshness_summary" in query_names


def test_no_delivery_classification_counts_all_cooldown_reason_codes_as_explained():
    query = next(
        query for query in QUERIES if query.name == "market_events_without_delivery_classification"
    )

    cooldown_filter_start = query.sql.index("AS cooldown_outcomes")
    cooldown_filter = query.sql[max(0, cooldown_filter_start - 200) : cooldown_filter_start]
    for reason_code in ("cooldown_active", "similar_event_suppressed", "similar_context_reused"):
        assert f"'{reason_code}'" in cooldown_filter
    assert "expected_backend_cooldown_active" in query.sql


def test_no_delivery_classification_uses_effective_cooldown_without_settings_row():
    query = next(
        query for query in QUERIES if query.name == "market_events_without_delivery_classification"
    )

    assert "SELECT 1800 AS cooldown_seconds)," in query.sql
    assert "FROM app_settings ORDER BY id DESC LIMIT 1" not in query.sql


def test_ops_agent_event_alert_estimate_query_exposes_cadence_fields():
    query = next(query for query in QUERIES if query.name == "event_alert_llm_estimates")

    assert "event_analysis_interval_seconds" in query.sql
    assert "payload_points" in query.sql
    assert "analysed_window_minutes" in query.sql
    assert "configured_eligible_symbols" in query.sql
    assert "active_eligible_symbols" in query.sql
    assert "inactive_configured_eligible_symbols" in query.sql
    assert "coalesce(e.active_symbols, 0) AS eligible_symbols" in query.sql
    assert "coalesce(e.active_symbols, 0) * 3600.0" in query.sql
    assert "coalesce(e.active_symbols, 0) * 86400.0" in query.sql
    assert "estimated_event_alert_llm_calls_per_hour" in query.sql
    assert "estimated_event_alert_llm_calls_per_day" in query.sql
    assert "SELECT 1800 AS event_analysis_interval_seconds" in query.sql
    assert "greatest(coalesce(automatic_check_interval_seconds" not in query.sql


def test_delivery_funnel_downstream_counts_are_event_alert_only():
    query = next(query for query in QUERIES if query.name == "delivery_funnel")

    assert query.sql.count("alert_type = 'event_alert'") >= 4
    assert "AS alert_records_created" in query.sql
    assert "AS telegram_delivery_attempts" in query.sql
    assert "AS telegram_delivered" in query.sql
    assert "AS telegram_failed" in query.sql


def test_event_ai_invariant_query_scopes_to_attached_successful_event_analyses():
    query = next(query for query in QUERIES if query.name == "event_ai_analysis_invariant_checks")

    assert "market_event_id IS NOT NULL" in query.sql
    assert "coalesce(analysis_type, 'event_analysis') = 'event_analysis'" in query.sql
    assert "status IN ('success', 'completed')" in query.sql


def test_event_alert_delivery_explanation_gap_query_accepts_expected_outcomes():
    query = next(
        query for query in QUERIES if query.name == "event_alert_delivery_explanation_gaps"
    )

    assert "should_alert = true" in query.sql
    assert "AND market_event_id IS NOT NULL" in query.sql
    assert "status = 'sent'" in query.sql
    for expected_status in (
        "delivered",
        "suppressed",
        "cooldown",
        "failed",
        "rate_limited",
        "no_eligible_recipients",
        "filtered",
        "not_scheduled",
    ):
        assert expected_status in query.sql
    assert "(array_agg(DISTINCT symbol ORDER BY symbol))[1:10]" in query.sql
    assert "array_agg(DISTINCT symbol ORDER BY symbol)[1:10]" not in query.sql


def test_ops_agent_event_alert_observability_queries_are_sanitized_aggregates():
    duplicate_by_event = next(
        query
        for query in QUERIES
        if query.name == "event_alert_duplicate_deliveries_by_market_event"
    )
    duplicate_by_analysis = next(
        query
        for query in QUERIES
        if query.name == "event_alert_duplicate_deliveries_by_analysis"
    )
    invariant = next(
        query for query in QUERIES if query.name == "event_alert_event_invariant_summary"
    )
    same_family = next(
        query for query in QUERIES if query.name == "event_alert_same_family_repeats_24h"
    )
    same_news = next(
        query for query in QUERIES if query.name == "event_alert_same_news_repeats_24h"
    )
    outcomes = next(query for query in QUERIES if query.name == "alert_delivery_outcome_summary")
    reuse = next(query for query in QUERIES if query.name == "event_alert_similar_context_reuse")
    possible_action_quality = next(
        query for query in QUERIES if query.name == "event_alert_possible_action_quality"
    )

    assert "user_id" in duplicate_by_event.sql
    assert "market_event_id" in duplicate_by_event.sql
    assert "event_ai_analysis_count" in duplicate_by_event.sql
    assert "event_ai_analysis_id" in duplicate_by_analysis.sql
    assert "attached_event_analysis_count" in invariant.sql
    assert "successful_attached_event_analysis_count" in invariant.sql
    assert "sent_delivery_count" in invariant.sql
    assert "outcome_count" in invariant.sql
    assert "semantic_family" in same_family.sql
    assert "decision_reason" in same_family.sql
    assert "analysed_window_change_percent" in same_family.sql
    assert "stable_news_set_hash" in same_family.sql
    assert "::jsonb" not in same_family.sql
    assert "md5" in same_news.sql
    assert "decision_reason" in same_news.sql
    assert "::jsonb" not in same_news.sql
    assert "message" not in same_news.sql.lower()
    assert "reason_code_unknown_count" in outcomes.sql
    assert "decision_stage" in outcomes.sql
    assert "decision_reason" in outcomes.sql
    assert "news_only_rejected_count" in outcomes.sql
    assert "llm_no_alert_count" in outcomes.sql
    assert "semantic_cooldown_suppressed_count" in outcomes.sql
    assert "similar_context_reused_count" in outcomes.sql
    assert "allowed_market_context_changed_count" in outcomes.sql
    assert "telegram_bot_blocked_count" in outcomes.sql
    assert "llm_invalid_response_count" in outcomes.sql
    assert "pre_llm_similar_context_reused_count" in outcomes.sql
    assert "error_message" not in next(
        query for query in QUERIES if query.name == "market_reports_freshness"
    ).sql
    assert "decision_reason = 'similar_context_reused'" in reuse.sql
    assert "event_ai_analysis_id IS NULL" in reuse.sql
    assert "context_fingerprint" in reuse.sql
    for status in ("delivered", "suppressed", "filtered", "failed", "rate_limited"):
        assert f"{status}_count" in outcomes.sql
    assert "generic_possible_action_count" in possible_action_quality.sql
    assert "should_alert = true" in possible_action_quality.sql


def test_llm_usage_query_groups_by_call_type_model_status_and_symbol():
    query = next(query for query in QUERIES if query.name == "llm_usage_summary")
    category_query = next(
        query for query in QUERIES if query.name == "llm_failure_category_summary"
    )

    assert "call_type" in query.sql
    assert "model" in query.sql
    assert "status" in query.sql
    assert "coalesce(symbol, 'UNKNOWN') AS symbol" in query.sql
    assert "sum(prompt_tokens) AS prompt_tokens" in query.sql
    assert "sum(completion_tokens) AS completion_tokens" in query.sql
    assert "sum(total_tokens) AS total_tokens" in query.sql
    assert "max(created_at) AS latest_at" in query.sql
    assert "rate_limit_count" in query.sql
    assert "timeout_count" in query.sql
    assert "invalid_json_schema_error_count" in query.sql
    for category in (
        "active_backoff",
        "circuit_breaker",
        "provider_rate_limit",
        "provider_model_error",
        "provider_json_validation_failure",
        "client_json_validation_failure",
        "client_schema_validation_failure",
        "provider_bad_request",
        "provider_4xx",
        "timeout",
        "provider_5xx",
        "network_error",
        "provider_auth_config",
        "other",
    ):
        assert category in category_query.sql
    assert "SELECT provider, model, call_type, failure_category" in category_query.sql
    assert "GROUP BY provider, model, call_type, failure_category" in category_query.sql


def test_llm_failure_category_query_keeps_provider_and_client_reasons_distinct():
    query = next(query for query in QUERIES if query.name == "llm_failure_category_summary")
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            "CREATE TABLE llm_usage_logs ("
            "provider TEXT, model TEXT, call_type TEXT, status TEXT, error_reason TEXT, "
            "retry_after TEXT, created_at TEXT)"
        )
        rows = [
            ("groq", "m1", "event_analysis", "llm_error", "provider_bad_request", None),
            ("groq", "m1", "event_analysis", "llm_error", "provider_4xx", None),
            (
                "cerebras",
                "m2",
                "event_analysis",
                "llm_error",
                "provider_json_validate_failed",
                None,
            ),
            ("gemini", "m3", "event_analysis", "invalid_json", "invalid_json", None),
            (
                "mistral",
                "m4",
                "event_analysis",
                "schema_error",
                "schema_validation_failed",
                None,
            ),
            ("groq", "m1", "event_analysis", "llm_error", "provider_5xx", None),
            ("groq", "m1", "event_analysis", "rate_limit", "rate_limit", "30"),
            (
                "groq",
                "m1",
                "event_analysis",
                "skipped_due_to_rate_limit",
                "rate_limit_backoff_active",
                None,
            ),
        ]
        connection.executemany(
            "INSERT INTO llm_usage_logs VALUES (?, ?, ?, ?, ?, ?, '2026-06-01T00:00:00Z')",
            rows,
        )
        result = connection.execute(
            query.sql,
            {"since": "2026-06-01T00:00:00Z", "until": "2026-06-02T00:00:00Z", "limit": 100},
        ).fetchall()
    finally:
        connection.close()

    categories = {row[3]: row[4] for row in result}
    assert categories == {
        "active_backoff": 1,
        "client_json_validation_failure": 1,
        "client_schema_validation_failure": 1,
        "provider_4xx": 1,
        "provider_5xx": 1,
        "provider_bad_request": 1,
        "provider_json_validation_failure": 1,
        "provider_rate_limit": 1,
    }


def test_news_budget_query_uses_sanitized_aggregates_only():
    query = next(query for query in QUERIES if query.name == "news_intelligence_budget_summary")

    assert "outcome_category" in query.sql
    assert "impact_bucket" in query.sql
    assert "recent_24h_items" in query.sql
    for category in ("successful", "skipped_budget", "failed", "pending", "unknown"):
        assert category in query.sql
    assert "title" not in query.sql.lower()
    assert "url" not in query.sql.lower()
    assert "llm_error" not in query.sql.lower()


def test_news_candidates_signal_and_freshness_queries_expose_sanitized_columns():
    query_names = {query.name: query for query in QUERIES}

    samples = query_names["event_ai_analysis_samples"]
    assert "related_news_candidates_count" in samples.sql
    # raw_input_json is read only to derive a candidate count, never selected into the bundle.
    for forbidden in ("error_message", "raw_output_json", "prompt", "response"):
        assert forbidden not in samples.sql.lower()
    summary = query_names["event_analysis_news_candidates_summary"]
    assert "zero_candidate_analyses" in summary.sql
    assert "with_candidates_analyses" in summary.sql
    assert "unknown_candidates_analyses" in summary.sql
    assert "alerts_with_candidates_but_no_attached_news" in summary.sql
    # Counts only — the signal must never select news content columns.
    assert "title" not in summary.sql.lower()
    assert "url" not in summary.sql.lower()
    assert "link" not in summary.sql.lower()
    freshness = query_names["market_reports_freshness"]
    assert "runtime_interval_seconds" in freshness.sql
    assert "expected_next_scheduled_refresh_at" in freshness.sql


def test_heartbeat_report_and_news_freshness_queries_handle_empty_db_shape():
    query_names = {query.name: query for query in QUERIES}

    assert "LEFT JOIN latest" in query_names["market_heartbeats_freshness"].sql
    assert REPORT_FRESHNESS_VALUES_SQL in query_names["market_reports_freshness"].sql
    assert "VALUES ('btc'), ('eth'), ('gram'), ('sol')" in query_names[
        "market_heartbeats_freshness"
    ].sql
    assert "placeholder_quality_count" in query_names["market_heartbeat_delivery_freshness"].sql
    assert "latest_fetched_at" in query_names["news_freshness_summary"].sql
    assert "usable_news_count_24h" in query_names["news_freshness_summary"].sql
    assert "CAST(:until AS timestamptz) - interval '24 hours'" in query_names[
        "news_freshness_summary"
    ].sql
    assert (
        query_names["news_freshness_summary"].sql.count(
            "fetched_at < CAST(:until AS timestamptz)"
        )
        == 3
    )
    assert ":until - interval '24 hours'" not in query_names["news_freshness_summary"].sql
    assert "array_agg(llm_status" not in query_names["news_freshness_summary"].sql
    assert "ORDER BY fetched_at DESC, id DESC LIMIT 1" in query_names[
        "news_freshness_summary"
    ].sql


def test_report_freshness_thresholds_include_scheduler_grace_without_runtime_cadence_change():
    assert DAILY_REPORT_RUNTIME_INTERVAL_SECONDS == 14400
    assert WEEKLY_REPORT_RUNTIME_INTERVAL_SECONDS == 86400
    assert DAILY_REPORT_FRESHNESS_GRACE_SECONDS == 3600
    assert WEEKLY_REPORT_FRESHNESS_GRACE_SECONDS == 3600
    assert DAILY_REPORT_FRESHNESS_THRESHOLD_SECONDS == 18000
    assert WEEKLY_REPORT_FRESHNESS_THRESHOLD_SECONDS == 90000


def test_alert_repetition_evidence_rolls_up_only_selected_recent_analyses():
    assert "delivery_candidates AS" in ALERT_EVIDENCE_SQL
    assert "JOIN alerts a ON a.event_ai_analysis_id = ra.event_ai_analysis_id" in ALERT_EVIDENCE_SQL
    assert "JOIN alerts a ON a.event_ai_analysis_id IS NULL" in ALERT_EVIDENCE_SQL
    assert "GROUP BY a.rollup_event_ai_analysis_id" in ALERT_EVIDENCE_SQL
    assert "OR (dr.event_ai_analysis_id IS NULL" not in ALERT_EVIDENCE_SQL


def test_alert_quality_summary_uses_token_boundary_placeholder_regexes():
    query = next(query for query in QUERIES if query.name == "alert_quality_summary")

    assert "~* '(^|[^a-z0-9])unknown([^a-z0-9]|$)'" in query.sql
    assert "~* '(^|[^a-z0-9])unavailable([^a-z0-9]|$)'" in query.sql
    assert "~* '(^|[^a-z0-9])null([^a-z0-9]|$)'" in query.sql


def test_old_price_change_label_queries_use_line_aware_regex():
    user_impact = next(query for query in QUERIES if query.name == "user_impact_summary")
    quality = next(query for query in QUERIES if query.name == "alert_quality_summary")

    expected = (
        "~* '(^|\\n)[[:space:]]*([•*\\-][[:space:]]*)?"
        "price change[[:space:]]*:'"
    )
    assert expected in user_impact.sql
    assert expected in quality.sql
    assert "LIKE '%price change%'" not in user_impact.sql
    assert "LIKE '%price change%'" not in quality.sql


def test_alert_repetition_detectors_unknown_when_evidence_missing():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )

    results = {
        result.id: result
        for result in run_detectors(
            {
                "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
                "evidence/health/health.json": {"status": "ok"},
            },
            period,
        )
    }

    assert results["noisy_alert_symbols"].status == "unknown"
    assert results["repeated_alert_content"].status == "unknown"
    assert results["similar_alert_groups"].status == "unknown"
    assert results["weak_event_identity"].status == "unknown"
    assert results["cooldown_effectiveness_gap"].status == "unknown"
    assert results["llm_repeated_alert_true_for_similar_situations"].status == "unknown"


def test_alert_repetition_detectors_unknown_when_evidence_partial():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )

    results = {
        result.id: result
        for result in run_detectors(
            {
                "evidence/db/alert_delivery_distribution.json": {
                    "warnings": ["bucket timeout"],
                    "symbols": [],
                },
                "evidence/db/alert_content_fingerprints.json": {
                    "warnings": ["bucket timeout"],
                    "repeated_groups": [],
                },
                "evidence/db/alert_similarity_groups.json": {
                    "warnings": ["bucket timeout"],
                    "groups": [],
                },
                "evidence/db/backend_suppression_effectiveness.json": {
                    "warnings": ["bucket timeout"],
                    "cooldown_gap_groups": [],
                },
                "evidence/db/event_identity_quality.json": {
                    "warnings": ["bucket timeout"],
                    "rows": [],
                },
            },
            period,
        )
    }

    assert results["noisy_alert_symbols"].status == "unknown"
    assert results["repeated_alert_content"].status == "unknown"
    assert results["similar_alert_groups"].status == "unknown"
    assert results["weak_event_identity"].status == "unknown"
    assert results["cooldown_effectiveness_gap"].status == "unknown"


def test_alert_repetition_detectors_trigger_with_evidence():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/alert_delivery_distribution.json": {
            "symbols": [{"symbol": "BTC", "sent_deliveries": 8}]
        },
        "evidence/db/alert_content_fingerprints.json": {
            "repeated_groups": [{"symbol": "BTC", "sent_deliveries": 8, "market_events": 2}]
        },
        "evidence/db/alert_similarity_groups.json": {
            "groups": [
                {
                    "symbols": ["BTC"],
                    "market_events": 2,
                    "sent_deliveries": 8,
                    "should_alert_true": 2,
                }
            ]
        },
        "evidence/db/event_identity_quality.json": {
            "rows": [
                {
                    "symbol": "BTC",
                    "market_events": 6,
                    "event_key_churn_ratio": 1.0,
                    "same_content_split_key_groups": 1,
                }
            ],
            "same_content_split_key_groups": [{"symbol": "BTC", "event_key_count": 2}],
        },
        "evidence/db/backend_suppression_effectiveness.json": {
            "suppression_groups": [
                {
                    "symbol": "BTC",
                    "event_key": "btc_price_volatility",
                    "delivered_inside_cooldown_candidates": 1,
                }
            ]
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["noisy_alert_symbols"].status == "triggered"
    assert results["repeated_alert_content"].status == "triggered"
    assert results["similar_alert_groups"].status == "triggered"
    assert results["weak_event_identity"].status == "triggered"
    assert results["cooldown_effectiveness_gap"].status == "triggered"
    assert results["llm_repeated_alert_true_for_similar_situations"].status == "triggered"


def test_failed_delivery_detector_triggers():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "alerts_summary": {
                    "rows": [{"deliveries": 10, "failed": 5}],
                },
                "telegram_delivery_failure_summary": {
                    "rows": [
                        {
                            "failed_or_retry_pending_total": 5,
                            "blocked_user": 0,
                            "retry_pending_actionable": 2,
                            "unexplained_telegram_failure": 3,
                        }
                    ]
                },
            }
        },
        "evidence/db/recent_alert_failures.json": {
            "queries": {"alerts_failures": {"rows": [{"alert_id": 1}]}}
        },
        "evidence/health/health.json": {"status": "ok"},
        "evidence/logs/pattern_counts.json": {"pattern_counts": {}},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["failed_telegram_deliveries"].status == "triggered"
    assert results["failed_telegram_deliveries"].severity == "high"


def test_failed_delivery_detector_uses_aggregate_counts_not_capped_samples():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "alerts_summary": {"rows": [{"deliveries": 100, "failed": 25}]},
                "telegram_delivery_failure_summary": {
                    "rows": [
                        {
                            "failed_or_retry_pending_total": 25,
                            "blocked_user": 0,
                            "retry_pending_actionable": 20,
                            "unexplained_telegram_failure": 5,
                        }
                    ]
                },
            }
        },
        "evidence/db/recent_alert_failures.json": {
            "queries": {
                "alerts_failures": {
                    "rows": [{"alert_id": 1, "failure_category": "retry_pending_actionable"}]
                }
            }
        },
        "evidence/health/health.json": {"status": "ok"},
        "evidence/logs/pattern_counts.json": {"pattern_counts": {}},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}
    detector = results["failed_telegram_deliveries"]

    assert detector.status == "triggered"
    assert detector.severity == "high"
    assert detector.metrics["failed"] == 25
    assert detector.metrics["sample_failure_rows"] == 1


def test_blocked_user_delivery_failures_stay_visible_without_actionable_severity():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "alerts_summary": {"rows": [{"deliveries": 100, "failed": 12}]},
                "telegram_delivery_failure_summary": {
                    "rows": [
                        {
                            "failed_or_retry_pending_total": 12,
                            "blocked_user": 12,
                            "retry_pending_actionable": 0,
                            "unexplained_telegram_failure": 0,
                        }
                    ]
                },
            }
        },
        "evidence/db/recent_alert_failures.json": {
            "queries": {
                "alerts_failures": {
                    "rows": [{"alert_id": 1, "failure_category": "blocked_user"}]
                }
            }
        },
        "evidence/health/health.json": {"status": "ok"},
        "evidence/logs/pattern_counts.json": {"pattern_counts": {}},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}
    detector = results["failed_telegram_deliveries"]

    assert detector.status == "clear"
    assert detector.severity == "info"
    assert detector.metrics["failed"] == 0
    assert detector.metrics["blocked_user_failures"] == 12
    assert detector.metrics["failed_or_retry_pending_total"] == 12


def test_health_detector_triggers_when_unavailable():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )

    results = {
        result.id: result
        for result in run_detectors(
            {
                "evidence/health/health.json": {"status": "failed"},
                "evidence/logs/pattern_counts.json": {"pattern_counts": {}},
            },
            period,
        )
    }

    assert results["health_endpoint_unavailable"].status == "triggered"


def test_duplicate_market_event_detector_clear_when_evidence_exists():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "duplicate_market_event_buckets": {
                    "rows": [],
                    "parameters": {"bucket_minutes": 15},
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["duplicate_market_events"].status == "clear"
    assert results["duplicate_market_events"].metrics["duplicate_like_group_count"] == 0


def test_duplicate_market_event_detector_triggers_with_bucket_groups():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "duplicate_market_event_buckets": {
                    "parameters": {"bucket_minutes": 30},
                    "rows": [
                        {
                            "symbol": "BTC",
                            "event_type": "price_movement",
                            "event_key": "btc_move",
                            "group_size": 3,
                            "sample_market_event_ids": [10, 11, 12],
                        }
                    ],
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    duplicate = results["duplicate_market_events"]
    assert duplicate.status == "triggered"
    assert duplicate.metrics["bucket_minutes"] == 30
    assert duplicate.metrics["max_group_size"] == 3
    assert duplicate.metrics["affected_symbols"] == ["BTC"]


def test_duplicate_market_event_detector_unknown_when_db_evidence_missing():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )

    results = {
        result.id: result
        for result in run_detectors(
            {
                "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
                "evidence/health/health.json": {"status": "ok"},
            },
            period,
        )
    }

    assert results["duplicate_market_events"].status == "unknown"
    assert "duplicate_market_event_buckets" in results["duplicate_market_events"].evidence_gap


def test_missing_required_db_evidence_returns_unknown_not_clear():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )

    results = {
        result.id: result
        for result in run_detectors(
            {
                "evidence/health/health.json": {"status": "ok"},
                "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
            },
            period,
        )
    }

    assert results["failed_telegram_deliveries"].status == "unknown"
    assert results["failed_telegram_deliveries"].evidence_gap is not None


@pytest.mark.asyncio
async def test_db_collector_failure_is_isolated_and_later_collectors_continue(
    monkeypatch, tmp_path
):
    class FakeRow:
        def __init__(self, **values):
            self._mapping = values

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def __iter__(self):
            return iter(self._rows)

    class FakeConnection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def execute(self, statement, _params):
            sql = str(statement)
            if "BROKEN QUERY" in sql:
                raise RuntimeError(
                    "syntax error near FROM DATABASE_URL=postgresql://user:secret@db/name"
                )
            if "ok_later" in sql:
                return FakeResult([FakeRow(value=1)])
            return FakeResult([])

        async def rollback(self):
            return None

    class FakeEngine:
        def connect(self):
            return FakeConnection()

        async def dispose(self):
            return None

    monkeypatch.setattr(db_collector, "create_async_engine", lambda *_args, **_kwargs: FakeEngine())
    monkeypatch.setattr(
        db_collector,
        "QUERIES",
        (
            DbQuery("broken", "evidence/db/anomalies.json", "SELECT * FROM BROKEN QUERY"),
            DbQuery("ok_later", "evidence/db/aggregate_metrics.json", "SELECT 1 AS ok_later"),
        ),
    )
    monkeypatch.setattr(db_collector, "ALERT_EVIDENCE_SQL", "SELECT 1 WHERE false")

    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    config = OpsAgentConfig(
        database_url="postgresql+asyncpg://ccwbot_ops_reader:secret@postgres/ccwbot",
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path,
        legacy_state_path=tmp_path / "state.json",
    )

    payloads, statuses = await db_collector.collect_db(
        config=config,
        period=period,
        mapper=ReferenceMapper(salt=b"0" * 32),
        redaction_report=RedactionReport(),
    )

    status_by_name = {status["name"]: status for status in statuses}
    assert status_by_name["db.broken"]["status"] == "failed"
    assert status_by_name["db.broken"]["error"] == "RuntimeError: sql_syntax_or_schema_error"
    assert "secret" not in str(status_by_name["db.broken"]["error"])
    assert "DATABASE_URL" not in str(status_by_name["db.broken"]["error"])
    assert status_by_name["db.ok_later"]["status"] == "ok"
    assert payloads["evidence/db/aggregate_metrics.json"]["queries"]["ok_later"]["row_count"] == 1


class _FakeRow:
    def __init__(self, **values):
        self._mapping = values


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _AlertEvidenceFakeConnection:
    def __init__(self, engine):
        self._engine = engine

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def execute(self, _statement, _params):
        self._engine.calls += 1
        self._engine.params.append(dict(_params))
        if self._engine.fail_mode == "partial" and self._engine.calls == 1:
            raise TimeoutError("bucket timed out")
        if self._engine.fail_mode == "all":
            raise TimeoutError("bucket timed out")
        rows = self._engine.rows_by_since.get(_params.get("since"), [])
        limit = int(_params.get("alert_evidence_limit") or len(rows) or 1)
        return _FakeResult([_FakeRow(**row) for row in rows[:limit]])

    async def rollback(self):
        return None


class _AlertEvidenceFakeEngine:
    def __init__(
        self,
        fail_mode: str | None = None,
        rows_by_since: dict[datetime, list[dict[str, object]]] | None = None,
    ):
        self.fail_mode = fail_mode
        self.rows_by_since = rows_by_since or {}
        self.calls = 0
        self.params: list[dict[str, object]] = []

    def connect(self):
        return _AlertEvidenceFakeConnection(self)

    async def dispose(self):
        return None


@pytest.mark.asyncio
async def test_alert_repetition_row_cap_prioritizes_newest_bucket():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    newest_bucket_start = datetime(2026, 6, 1, 18, tzinfo=timezone.utc)
    oldest_bucket_start = datetime(2026, 6, 1, 0, tzinfo=timezone.utc)
    fake_engine = _AlertEvidenceFakeEngine(
        rows_by_since={
            newest_bucket_start: [{"marker": "newest"}],
            oldest_bucket_start: [{"marker": "oldest"}],
        }
    )

    rows, statuses, warnings = await db_collector._collect_alert_repetition_rows(
        fake_engine,
        params={},
        period=period,
        timeout_seconds=1,
        row_cap=1,
        mapper=ReferenceMapper(salt=b"0" * 32),
        redaction_report=RedactionReport(),
    )

    assert rows == [{"marker": "newest"}]
    assert fake_engine.params[0]["since"] == newest_bucket_start
    assert fake_engine.params[0]["until"] == period.end
    assert len(statuses) == 1
    assert warnings == ["alert repetition evidence row cap reached before older buckets ran"]


async def _collect_alert_evidence_with_fake_engine(monkeypatch, tmp_path, *, fail_mode=None):
    fake_engine = _AlertEvidenceFakeEngine(fail_mode=fail_mode)
    monkeypatch.setattr(db_collector, "create_async_engine", lambda *_args, **_kwargs: fake_engine)
    monkeypatch.setattr(db_collector, "QUERIES", ())
    monkeypatch.setattr(db_collector, "ALERT_EVIDENCE_SQL", "SELECT 1 WHERE false")
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    config = OpsAgentConfig(
        database_url="postgresql+asyncpg://ccwbot_ops_reader:secret@postgres/ccwbot",
        health_url=None,
        output_dir=tmp_path,
        logs_dir=tmp_path,
        legacy_state_path=tmp_path / "state.json",
    )
    payloads, statuses = await db_collector.collect_db(
        config=config,
        period=period,
        mapper=ReferenceMapper(salt=b"0" * 32),
        redaction_report=RedactionReport(),
    )
    return payloads, {status["name"]: status for status in statuses}, period


@pytest.mark.asyncio
async def test_alert_repetition_zero_rows_collects_valid_empty_evidence(monkeypatch, tmp_path):
    payloads, statuses, period = await _collect_alert_evidence_with_fake_engine(
        monkeypatch,
        tmp_path,
    )

    assert statuses["db.alert_repetition_evidence"]["status"] == "ok"
    assert payloads["evidence/db/alert_delivery_distribution.json"]["warnings"] == []
    assert payloads["evidence/db/alert_delivery_distribution.json"]["symbols"] == []

    results = {result.id: result for result in run_detectors(payloads, period)}

    assert results["noisy_alert_symbols"].status == "clear"
    assert results["repeated_alert_content"].status == "clear"
    assert results["similar_alert_groups"].status == "clear"


@pytest.mark.asyncio
async def test_alert_repetition_partial_bucket_warning_marks_dependent_detectors_unknown(
    monkeypatch, tmp_path
):
    payloads, statuses, period = await _collect_alert_evidence_with_fake_engine(
        monkeypatch,
        tmp_path,
        fail_mode="partial",
    )

    assert statuses["db.alert_repetition_evidence"]["status"] == "partial"
    assert "timeout" in statuses["db.alert_repetition_evidence"]["error"]

    results = {result.id: result for result in run_detectors(payloads, period)}

    assert results["noisy_alert_symbols"].status == "unknown"
    assert results["repeated_alert_content"].status == "unknown"
    assert results["similar_alert_groups"].status == "unknown"


@pytest.mark.asyncio
async def test_alert_repetition_all_buckets_failed_keeps_dependent_detectors_unknown(
    monkeypatch, tmp_path
):
    payloads, statuses, period = await _collect_alert_evidence_with_fake_engine(
        monkeypatch,
        tmp_path,
        fail_mode="all",
    )

    assert statuses["db.alert_repetition_evidence"]["status"] == "failed"

    results = {result.id: result for result in run_detectors(payloads, period)}

    assert results["noisy_alert_symbols"].status == "unknown"
    assert results["repeated_alert_content"].status == "unknown"
    assert results["similar_alert_groups"].status == "unknown"


def test_no_delivery_classification_clear_for_expected_no_alert():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "market_events_without_delivery_classification": {
                    "rows": [
                        {
                            "classification": "expected_should_alert_false",
                            "events": 4,
                            "sample_events": [{"market_event_id": 20}],
                        }
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["market_events_without_alert_deliveries"]
    assert detector.status == "clear"
    assert detector.metrics["expected_no_delivery"] == 4


def test_no_delivery_classification_triggers_for_true_alert_gap():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "market_events_without_delivery_classification": {
                    "rows": [
                        {
                            "classification": "delivery_gap_should_alert_true",
                            "events": 2,
                            "sample_events": [{"market_event_id": 30}],
                        }
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["market_events_without_alert_deliveries"]
    assert detector.status == "triggered"
    assert detector.metrics["delivery_gap_should_alert_true"] == 2


def test_event_alert_delivery_explanation_gap_detector_triggers():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "event_alert_delivery_explanation_gaps": {
                    "rows": [
                        {
                            "anomaly": "should_alert_true_without_delivery_explanation",
                            "gap_count": 3,
                            "affected_market_events": 2,
                        }
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["event_alert_delivery_explanation_gaps"]
    assert detector.status == "triggered"
    assert detector.metrics["should_alert_true_without_delivery_explanation"] == 3


def test_no_delivery_classification_unknown_when_reason_missing():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "market_events_without_delivery_classification": {
                    "rows": [{"classification": "unknown_no_analysis", "events": 1}]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["market_events_without_alert_deliveries"].status == "unknown"


def test_no_delivery_classification_clear_for_backend_cooldown():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "market_events_without_delivery_classification": {
                    "rows": [
                        {
                            "classification": "expected_backend_cooldown_active",
                            "events": 2,
                            "sample_events": [{"market_event_id": 40}],
                        }
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["market_events_without_alert_deliveries"]
    assert detector.status == "clear"
    assert detector.metrics["expected_backend_cooldown_active"] == 2


def test_fully_cooldown_suppressed_event_is_not_flagged_as_delivery_gap():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "market_events_without_delivery_classification": {
                    "rows": [
                        {
                            "classification": "expected_backend_cooldown_active",
                            "events": 1,
                            "should_alert_true": 1,
                            "likely_eligible_recipient_total": 194,
                            "sample_events": [
                                {
                                    "market_event_id": 3617,
                                    "symbol": "BTC",
                                    "should_alert": True,
                                    "likely_eligible_recipients": 194,
                                    "outcome_counts": {
                                        "no_recipients": 0,
                                        "premium_required": 0,
                                        "cooldown": 194,
                                        "failed_or_rate_limited": 0,
                                    },
                                }
                            ],
                        }
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["market_events_without_alert_deliveries"]
    assert detector.status == "clear"
    assert detector.severity == "info"
    assert detector.metrics["delivery_gap_should_alert_true"] == 0
    assert detector.metrics["expected_backend_cooldown_active"] == 1
    assert detector.metrics["expected_no_delivery"] == 1


def test_no_alert_deliveries_clear_when_active_period_has_no_market_events():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "alerts_summary": {"rows": []},
                "price_state_current": {"rows": [{"symbol": "BTC"}]},
                "market_events_summary": {"rows": []},
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["no_alert_deliveries_observed"].status == "clear"


def test_news_budget_detector_clears_expected_small_budget_skips():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "news_intelligence_budget_summary": {
                    "rows": [
                        {
                            "outcome_category": "successful",
                            "impact_bucket": "high",
                            "items": 8,
                        },
                        {
                            "outcome_category": "skipped_budget",
                            "impact_bucket": "low_or_null",
                            "items": 2,
                        },
                    ]
                }
            }
        },
        "evidence/db/recent_news_failures.json": {
            "queries": {"news_items_recent_high_impact": {"rows": [{}] * 100}}
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["news_intelligence_failures"]
    assert detector.status == "clear"
    assert detector.metrics["skipped_budget"] == 2
    assert detector.metrics["sample_rows"] == 100


def test_news_budget_detector_triggers_on_aggregate_failures_despite_capped_sample():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "news_intelligence_budget_summary": {
                    "rows": [
                        {
                            "outcome_category": "failed",
                            "impact_bucket": "high",
                            "items": 12,
                        },
                    ]
                }
            }
        },
        "evidence/db/recent_news_failures.json": {
            "queries": {"news_items_recent_high_impact": {"rows": [{}]}}
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["news_intelligence_failures"]
    assert detector.status == "triggered"
    assert detector.severity == "high"
    assert detector.metrics["failed_news_intelligence"] == 12
    assert detector.metrics["sample_rows"] == 1


def test_news_budget_detector_triggers_on_excessive_high_medium_skips():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "news_intelligence_budget_summary": {
                    "rows": [
                        {
                            "outcome_category": "skipped_budget",
                            "impact_bucket": "high",
                            "items": 3,
                        },
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["news_intelligence_failures"]
    assert detector.status == "triggered"
    assert detector.severity == "medium"
    assert detector.metrics["excessive_budget_skips"] is True


def test_llm_failure_detector_uses_safe_category_aggregates():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "llm_usage_summary": {"rows": []},
                "llm_failure_category_summary": {
                    "rows": [
                        {
                            "provider": "groq",
                            "model": "primary",
                            "call_type": "event_analysis",
                            "failure_category": "provider_rate_limit",
                            "calls": 2,
                        },
                        {
                            "provider": "groq",
                            "model": "primary",
                            "call_type": "event_analysis",
                            "failure_category": "active_backoff",
                            "calls": 1,
                        },
                        {
                            "provider": "cerebras",
                            "model": "fallback",
                            "call_type": "event_analysis",
                            "failure_category": "successful",
                            "calls": 2,
                        },
                        {
                            "provider": "groq",
                            "model": "heartbeat",
                            "call_type": "market_heartbeat",
                            "failure_category": "provider_model_error",
                            "calls": 1,
                        },
                    ]
                },
                "event_analysis_logical_outcome_summary": {
                    "rows": [
                        {
                            "provider": "cerebras",
                            "model": "fallback",
                            "logical_outcome": "logical_success",
                            "analyses": 2,
                        }
                    ]
                },
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["repeated_llm_failures_or_rate_limits"]
    assert detector.status == "triggered"
    assert detector.metrics["provider_attempt_incidents"] == 3
    assert detector.metrics["actual_provider_rate_limits"] == 2
    assert detector.metrics["active_backoff_skips"] == 1
    assert detector.metrics["terminal_event_analysis_failures"] == 0
    assert detector.metrics["terminal_event_analysis_rate_limited"] == 0
    assert detector.metrics["event_analysis_logical_outcomes"] == {"logical_success": 2}
    assert detector.metrics["failure_categories_by_call_type"] == {
        "event_analysis": {
            "active_backoff": 1,
            "provider_rate_limit": 2,
            "successful": 2,
        },
        "market_heartbeat": {"provider_model_error": 1},
    }


def test_llm_terminal_event_analysis_failure_is_visible_separately_from_provider_pressure():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "llm_failure_category_summary": {
                    "rows": [
                        {
                            "provider": "groq",
                            "model": "primary",
                            "call_type": "event_analysis",
                            "failure_category": "provider_rate_limit",
                            "calls": 2,
                        }
                    ]
                },
                "event_analysis_logical_outcome_summary": {
                    "rows": [
                        {
                            "provider": "groq",
                            "model": "primary",
                            "logical_outcome": "logical_failed",
                            "analyses": 1,
                        }
                    ]
                },
            }
        }
    }

    detector = {
        result.id: result for result in run_detectors(evidence, period)
    }["repeated_llm_failures_or_rate_limits"]

    assert detector.status == "triggered"
    assert detector.metrics["provider_attempt_incidents"] == 2
    assert detector.metrics["terminal_event_analysis_failures"] == 1


def test_llm_detector_is_unknown_when_logical_outcome_evidence_is_missing():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {"llm_failure_category_summary": {"rows": []}}
        }
    }

    detector = {
        result.id: result for result in run_detectors(evidence, period)
    }["repeated_llm_failures_or_rate_limits"]

    assert detector.status == "unknown"


def test_payment_premium_detector_aggregates_inconsistency_types():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "premium_payment_inconsistencies": {
                    "rows": [
                        {"anomaly": "paid_without_premium"},
                        {"anomaly": "expired_active_subscription"},
                        {"anomaly": "active_premium_without_trail"},
                    ]
                }
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["payment_premium_inconsistencies"]
    assert detector.status == "triggered"
    assert detector.severity == "high"
    assert detector.metrics["anomalies_by_type"]["paid_without_premium"] == 1
    assert detector.metrics["anomalies_by_type"]["expired_active_subscription"] == 1


def test_market_event_analysis_invariant_surfaces_multiple_analysis_ids():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/anomalies.json": {
            "queries": {
                "delivery_invariant_checks": {
                    "rows": [{"anomaly": "multiple_analysis_ids_for_event", "count": 2}]
                },
                "event_ai_analysis_invariant_checks": {"rows": []},
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["market_event_analysis_invariant"]
    assert detector.status == "triggered"
    assert detector.severity == "critical"
    assert detector.metrics["multiple_analysis_ids_for_event"] == 2


def test_report_freshness_detector_triggers_for_stale_or_missing_reports():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "market_reports_summary": {"rows": []},
                "market_reports_freshness": {
                    "rows": [
                        {
                            "report_type": "daily",
                            "latest_status": "completed",
                            "latest_generated_at": "2026-06-01T00:00:00Z",
                            "latest_expires_at": "2026-06-01T04:00:00Z",
                            "age_seconds": 86400,
                            "max_age_seconds": 14400,
                        },
                        {"report_type": "weekly", "latest_generated_at": None},
                    ]
                },
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["failed_daily_weekly_reports"]
    assert detector.status == "triggered"
    assert detector.metrics["stale_or_missing_reports"] == 2
    assert detector.metrics["affected_report_types"] == ["daily", "weekly"]


def test_report_freshness_detector_surfaces_age_vs_expected_next_refresh():
    # Explicit scheduler-grace evidence: age, runtime interval, grace, and the expected
    # next scheduled refresh are surfaced so reports never speculate about cadence.
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "market_reports_summary": {"rows": []},
                "market_reports_freshness": {
                    "rows": [
                        {
                            "report_type": "weekly",
                            "latest_status": "completed",
                            "latest_generated_at": "2026-06-01T12:00:00Z",
                            "latest_expires_at": "2026-06-02T12:00:00Z",
                            "age_seconds": 43200,
                            "max_age_seconds": 90000,
                            "runtime_interval_seconds": 86400,
                            "expected_next_scheduled_refresh_at": "2026-06-02T12:00:00Z",
                        },
                    ]
                },
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["failed_daily_weekly_reports"]
    assert detector.status == "clear"
    freshness_rows = detector.metrics["report_freshness"]
    assert freshness_rows == [
        {
            "report_type": "weekly",
            "latest_status": "completed",
            "latest_generation_age_seconds": 43200,
            "freshness_threshold_seconds": 90000,
            "runtime_interval_seconds": 86400,
            "scheduler_grace_seconds": 3600,
            "expected_next_scheduled_refresh_at": "2026-06-02T12:00:00Z",
        }
    ]
    assert "regeneration_semantics" in detector.metrics


@pytest.mark.parametrize(
    ("age_seconds", "latest_status", "expected_status"),
    [
        (86399, "completed", "clear"),
        (86401, "completed", "clear"),
        (90000, "completed", "clear"),
        (90001, "completed", "triggered"),
        (1, "failed", "triggered"),
        (60, "completed", "clear"),
    ],
)
def test_weekly_report_freshness_respects_interval_plus_grace_boundaries(
    age_seconds, latest_status, expected_status
):
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "market_reports_summary": {"rows": []},
                "market_reports_freshness": {
                    "rows": [
                        {
                            "report_type": "weekly",
                            "latest_status": latest_status,
                            "latest_generated_at": "2026-06-01T00:00:00Z",
                            # Nominal expiry may pass inside grace without being stale.
                            "latest_expires_at": "2026-06-01T23:59:59Z",
                            "age_seconds": age_seconds,
                            "max_age_seconds": 90000,
                            "runtime_interval_seconds": 86400,
                        }
                    ]
                },
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    assert results["failed_daily_weekly_reports"].status == expected_status


def test_market_data_freshness_uses_explicit_scheduler_grace_at_boundary():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )

    def detector_for_age(age_seconds):
        checked_at = period.end.timestamp() - age_seconds
        evidence = {
            "evidence/db/aggregate_metrics.json": {
                "queries": {
                    "app_settings": {"rows": [{"automatic_check_interval_seconds": 600}]},
                    "price_state_current": {
                        "rows": [
                            {
                                "symbol": "ETH",
                                "last_checked_at": datetime.fromtimestamp(
                                    checked_at, tz=timezone.utc
                                ).isoformat(),
                            }
                        ]
                    },
                }
            },
            "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
            "evidence/health/health.json": {"status": "ok"},
        }
        return {
            result.id: result for result in run_detectors(evidence, period)
        }["stale_price_snapshots"]

    assert MARKET_DATA_FRESHNESS_GRACE_SECONDS == 120
    at_boundary = detector_for_age(1800 + MARKET_DATA_FRESHNESS_GRACE_SECONDS)
    beyond_boundary = detector_for_age(1801 + MARKET_DATA_FRESHNESS_GRACE_SECONDS)

    assert at_boundary.status == "clear"
    assert beyond_boundary.status == "triggered"
    assert at_boundary.metrics["freshness_base_threshold_seconds"] == 1800
    assert at_boundary.metrics["freshness_grace_seconds"] == 120
    assert at_boundary.metrics["freshness_threshold_seconds"] == 1920


def test_ops_agent_active_symbols_match_runtime_active_symbols():
    from bot.domain.supported_coins import ACTIVE_SYMBOLS as BOT_ACTIVE_SYMBOLS

    assert OPS_AGENT_ACTIVE_SYMBOLS == BOT_ACTIVE_SYMBOLS


def test_heartbeat_freshness_detector_triggers_for_stale_or_missing_cache():
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    evidence = {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "market_heartbeats_summary": {"rows": []},
                "market_heartbeats_freshness": {
                    "rows": [
                        {
                            "symbol": "BTC",
                            "latest_status": "completed",
                            "latest_generated_at": "2026-06-01T00:00:00Z",
                            "age_seconds": 86400,
                        },
                        {"symbol": "ETH", "latest_generated_at": None},
                    ]
                },
            }
        },
        "evidence/logs/pattern_counts.json": {"period_matched_pattern_counts": {}},
        "evidence/health/health.json": {"status": "ok"},
    }

    results = {result.id: result for result in run_detectors(evidence, period)}

    detector = results["stale_or_failed_market_heartbeats"]
    assert detector.status == "triggered"
    assert detector.metrics["stale_or_missing_heartbeats"] == 2
    assert detector.metrics["affected_symbols"] == ["BTC", "ETH"]


def test_alert_evidence_collector_uses_dedicated_timeout_and_narrower_buckets():
    from ops_agent.collectors.db import _alert_evidence_windows
    from ops_agent.config import OpsAgentLimits, load_config

    limits = OpsAgentLimits()
    assert limits.alert_evidence_query_timeout_seconds > limits.db_query_timeout_seconds
    assert limits.alert_evidence_bucket_hours < 6

    config = load_config(output_dir="reports")
    assert config.limits.alert_evidence_query_timeout_seconds == 45
    assert config.limits.alert_evidence_bucket_hours == 3

    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    windows = _alert_evidence_windows(period, bucket_hours=3)
    assert len(windows) == 8
    assert windows[0][0] == period.start
    assert windows[-1][1] == period.end


def test_event_alert_delivered_event_ratio_query_is_registered():
    query = next(
        query for query in QUERIES if query.name == "event_alert_delivered_event_ratio"
    )

    assert query.evidence_file == "evidence/db/aggregate_metrics.json"
    assert "should_alert = true" in query.sql
    assert "AS should_alert_true_events" in query.sql
    assert "AS delivered_events" in query.sql
    assert "status = 'sent'" in query.sql
