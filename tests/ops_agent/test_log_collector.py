from __future__ import annotations

from datetime import datetime, timezone

from ops_agent.collectors.logs import LOG_PATTERNS, collect_logs, parse_log_timestamp
from ops_agent.config import OpsAgentConfig, OpsAgentLimits
from ops_agent.redaction import RedactionReport, ReferenceMapper
from ops_agent.schemas import Period


def test_parse_log_timestamp_supports_existing_ccwbot_format():
    parsed = parse_log_timestamp(
        "2026-06-01 22:12:14,825 WARNING bot.alerts: ops_event=test"
    )

    assert parsed == datetime(2026, 6, 1, 22, 12, 14, 825000, tzinfo=timezone.utc)


def test_collect_logs_separates_period_matched_and_tail_context(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "ccwbot-operational.log").write_text(
        "\n".join(
            [
                "2026-06-01 00:00:00,000 INFO bot.runtime: ops_event=bot_start",
                "2026-06-01 00:30:00,000 ERROR bot.alerts: "
                "ops_event=event_alert_delivery_summary user_id=123",
                "2026-06-01 00:31:00,000 INFO bot.alerts: "
                "ops_event=event_alert_suppression suppression_reason=semantic_cooldown "
                "raw_event_key=btc_move canonical_event_key=btc_move "
                "event_instance_key=btc_move delivery_count=0 suppression_count=1 "
                "analysed_window_minutes=180",
                "2026-06-02 00:00:00,000 ERROR bot.alerts: outside period",
                "ERROR unscoped tail context user_id=456 suppression_reason=delivery_failed",
            ]
        ),
        encoding="utf-8",
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=logs_dir,
        legacy_state_path=tmp_path / "state.json",
        limits=OpsAgentLimits(max_log_tail_bytes=20_000),
    )

    index, pattern_counts, excerpts, statuses = collect_logs(
        config=config,
        period=period,
        mapper=ReferenceMapper(salt=b"0" * 32),
        redaction_report=RedactionReport(),
    )

    assert statuses == [{"name": "logs.ccwbot-operational.log", "status": "ok", "error": None}]
    file_index = index["files"][0]
    assert file_index["timestamp_parse"]["period_matched_lines"] == 3
    assert file_index["timestamp_parse"]["outside_period_lines"] == 1
    assert file_index["timestamp_parse"]["unparseable_timestamp_lines"] == 1
    assert pattern_counts["period_matched_pattern_counts"]["error"] == 1
    assert pattern_counts["tail_context_pattern_counts"]["error"] == 1
    assert pattern_counts["period_matched_suppression_reason_counts"] == {
        "semantic_cooldown": 1
    }
    assert pattern_counts["tail_context_suppression_reason_counts"] == {"delivery_failed": 1}
    assert pattern_counts["suppression_reason_counts"] == {
        "delivery_failed": 1,
        "semantic_cooldown": 1,
    }
    assert excerpts == {}
    assert file_index["suppression_reasons"]["period_matched"] == {"semantic_cooldown": 1}
    assert file_index["suppression_reasons"]["tail_context"] == {"delivery_failed": 1}
    period_records = pattern_counts["period_matched_records"]
    tail_records = pattern_counts["tail_context_records"]
    delivery_record = next(
        record for record in period_records if record["event"] == "event_alert_delivery_summary"
    )
    assert delivery_record["timestamp"] == "2026-06-01T00:30:00Z"
    assert tail_records[0]["timestamp"] is None
    encoded = str(pattern_counts)
    assert "user_id=123" not in encoded
    assert "user_id=456" not in encoded


def test_collect_logs_exports_only_allowlisted_structured_match_fields(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    operation_id = "123e4567-e89b-42d3-a456-426614174000"
    (logs_dir / "ccwbot-operational.log").write_text(
        "2026-06-01 00:30:00Z ERROR bot.llm: "
        f"ops_event=llm_provider_switch provider=groq model=openai/gpt-oss-120b "
        f"call_type=event_analysis symbol=BTC reason=rate_limit operation_id={operation_id} "
        "chat_id=123 prompt=private_text authorization=Bearer_secret\n",
        encoding="utf-8",
    )
    period = Period(
        datetime(2026, 6, 1, tzinfo=timezone.utc),
        datetime(2026, 6, 2, tzinfo=timezone.utc),
        "test",
    )
    config = OpsAgentConfig(None, None, tmp_path, logs_dir, tmp_path / "state.json")

    _, counts, _, _ = collect_logs(
        config=config,
        period=period,
        mapper=ReferenceMapper(salt=b"2" * 32),
        redaction_report=RedactionReport(),
    )

    record = counts["period_matched_records"][0]
    assert record["operation_ref"].startswith("operation_ref:h_")
    assert record["provider"] == "groq"
    assert record["model"] == "openai/gpt-oss-120b"
    encoded = str(counts)
    assert operation_id not in encoded
    assert "private_text" not in encoded
    assert "chat_id" not in encoded
    assert "Bearer_secret" not in encoded


def test_collect_logs_never_exports_credential_shaped_model_values(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    credential = "sk-abcdefghijklmnopqrstuvwxyz1234567890"
    (logs_dir / "ccwbot-operational.log").write_text(
        "2026-06-01 00:30:00Z ERROR bot.llm: "
        f"ops_event=llm_provider_switch provider=groq model={credential} "
        "call_type=event_analysis reason=invalid_output\n",
        encoding="utf-8",
    )
    period = Period(
        datetime(2026, 6, 1, tzinfo=timezone.utc),
        datetime(2026, 6, 2, tzinfo=timezone.utc),
        "test",
    )
    config = OpsAgentConfig(None, None, tmp_path, logs_dir, tmp_path / "state.json")

    _, counts, _, _ = collect_logs(
        config=config,
        period=period,
        mapper=ReferenceMapper(salt=b"3" * 32),
        redaction_report=RedactionReport(),
    )

    record = counts["period_matched_records"][0]
    assert "model" not in record
    assert credential not in str(counts)


def test_collect_logs_warns_when_timestamps_are_unparseable(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "ccwbot-warnings-errors.log").write_text(
        "ERROR no timestamp ops_event=llm_failure\n",
        encoding="utf-8",
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    config = OpsAgentConfig(
        database_url=None,
        health_url=None,
        output_dir=tmp_path,
        logs_dir=logs_dir,
        legacy_state_path=tmp_path / "state.json",
    )

    index, pattern_counts, _, _ = collect_logs(
        config=config,
        period=period,
        mapper=ReferenceMapper(salt=b"1" * 32),
        redaction_report=RedactionReport(),
    )

    assert "no parseable timestamps" in index["warnings"][0]
    assert index["files"][0]["timestamp_parse"]["period_filter_applied"] is False
    assert pattern_counts["period_matched_pattern_counts"]["error"] == 0
    assert pattern_counts["tail_context_pattern_counts"]["error"] == 1


def test_llm_failure_pattern_ignores_healthy_llm_lines_and_failed_zero_counters():
    pattern = LOG_PATTERNS["llm_failure"]

    non_failures = [
        "Running automatic LLM event-analysis check.",
        "ops_event=news_intelligence_batch_completed fetched=5 success=5 "
        "skipped_budget=0 failed=0",
        "Groq client initialised for model x.",
    ]
    failures = [
        "Groq JSON mode failed; using deterministic fallback.",
        "LLM usage logging failed: database unavailable",
        "AI parsing failed: invalid JSON (unexpected token).",
        "ops_event=llm_rate_limit_started provider=groq model=x call_type=unknown",
        "market heartbeat schema validation failed: missing field",
    ]

    assert not any(pattern.search(line) for line in non_failures)
    assert all(pattern.search(line) for line in failures)


def test_coingecko_rate_limit_pattern_is_provider_specific():
    pattern = LOG_PATTERNS["coingecko_rate_limit"]
    coingecko_limits = [
        "ops_event=coingecko_rate_limit attempt=1 max_retries=3",
        "CoinGecko request failed with HTTP 429",
        "429 rate limit returned by CoinGecko",
    ]
    unrelated_limits = [
        "ops_event=llm_rate_limit_started provider=groq model=x",
        "Groq rate_limit retry_after_seconds=30",
        "numeric counters: requests=429 successes=428",
        "CoinGecko request completed successfully",
    ]

    assert all(pattern.search(line) for line in coingecko_limits)
    assert not any(pattern.search(line) for line in unrelated_limits)


def test_heartbeat_failure_pattern_ignores_healthy_heartbeat_lines():
    pattern = LOG_PATTERNS["heartbeat_failure"]

    non_failures = [
        "ops_event=heartbeat_delivery_summary symbol=BTC heartbeat_id=1 "
        "due=3 sent=3 failed=0",
        # Summary lines with failed>0 repeat the per-delivery heartbeat_delivery_failed
        # lines and previously double-counted every failure vs the DB truth; they are
        # intentionally not matched.
        "ops_event=heartbeat_delivery_summary symbol=BTC heartbeat_id=1 "
        "due=3 sent=1 failed=2",
        "ops_event=heartbeat_generation_scheduled interval_seconds=3600",
        "ops_event=heartbeat_generation_completed symbols=4",
        "BTC market heartbeat skipped: no cached heartbeat.",
        "Market heartbeat generation skipped because database storage is off.",
    ]
    failures = [
        "BTC market heartbeat generation failed: provider timeout",
        "BTC market heartbeat schema validation failed: missing field",
        "ops_event=heartbeat_generation_failed symbol=BTC error=x",
        "ops_event=heartbeat_delivery_failed symbol=BTC error_class=Forbidden",
    ]

    assert not any(pattern.search(line) for line in non_failures)
    assert all(pattern.search(line) for line in failures)


def test_heartbeat_failure_pattern_counts_failed_delivery_once_not_twice():
    # Regression for the July 2026 double-count (pattern 50 vs DB 25): one failed
    # delivery produces a per-delivery line plus a summary line; only one may match.
    pattern = LOG_PATTERNS["heartbeat_failure"]
    paired_lines = [
        "ops_event=heartbeat_delivery_failed symbol=BTC error_class=Forbidden",
        "ops_event=heartbeat_delivery_summary symbol=BTC heartbeat_id=1 "
        "due=1 sent=0 failed=1",
    ]

    assert sum(1 for line in paired_lines if pattern.search(line)) == 1
