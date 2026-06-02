from __future__ import annotations

from datetime import datetime, timezone

from ops_agent.collectors.logs import collect_logs, parse_log_timestamp
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
                "2026-06-02 00:00:00,000 ERROR bot.alerts: outside period",
                "ERROR unscoped tail context user_id=456",
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
    assert file_index["timestamp_parse"]["period_matched_lines"] == 2
    assert file_index["timestamp_parse"]["outside_period_lines"] == 1
    assert file_index["timestamp_parse"]["unparseable_timestamp_lines"] == 1
    assert pattern_counts["period_matched_pattern_counts"]["error"] == 1
    assert pattern_counts["tail_context_pattern_counts"]["error"] == 1
    period_excerpt = excerpts[file_index["period_matched_excerpt"]]["text"]
    tail_excerpt = excerpts[file_index["tail_context_excerpt"]]["text"]
    assert "00:30:00" in period_excerpt
    assert "outside period" not in period_excerpt
    assert "unscoped tail context" in tail_excerpt
    assert "user_ref:" in period_excerpt
    assert "user_ref:" in tail_excerpt


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
