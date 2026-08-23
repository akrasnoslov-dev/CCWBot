"""Detectors and evidence quality for an LLM-side Event Analysis outage.

Covers the three ways the 2026-07 outage stayed invisible for 18 days: no detector keyed on
the event-analysis success rate, no detector compared the model actually used against the
shipped default, and the failure storm itself exhausted the alert-repetition row cap and
blinded six unrelated alert-quality detectors.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from ops_agent.collectors.db import ALERT_EVIDENCE_SQL
from ops_agent.detectors import (
    consecutive_zero_success_runs,
    event_analysis_call_totals,
    run_detectors,
)
from ops_agent.expected_models import SHIPPED_DEFAULT_MODELS
from ops_agent.schemas import Period
from ops_agent.state import record_collection

PERIOD = Period(
    start=datetime(2026, 8, 4, tzinfo=timezone.utc),
    end=datetime(2026, 8, 5, tzinfo=timezone.utc),
    source="test",
)


def _evidence(llm_rows, *, state_runs=None):
    return {
        "evidence/db/aggregate_metrics.json": {
            "queries": {
                "llm_usage_summary": {"rows": llm_rows},
                "llm_failure_category_summary": {"rows": []},
                "event_analysis_logical_outcome_summary": {"rows": []},
            }
        },
        "evidence/local_state/ops_agent_state_snapshot.json": {"recent_runs": state_runs or []},
    }


def _detector(evidence, detector_id):
    for result in run_detectors(evidence, PERIOD):
        if result.id == detector_id:
            return result
    raise AssertionError(f"detector {detector_id} not registered")


def _row(
    status,
    calls,
    *,
    model="llama-3.3-70b-versatile",
    call_type="event_analysis",
    provider="groq",
):
    return {"call_type": call_type, "status": status, "calls": calls, "model": model,
            "provider": provider}


# --- zero success rate -------------------------------------------------------------------


def test_zero_successful_event_analyses_triggers():
    # The outage shape: a steady stream of identical failures and not one success.
    result = _detector(_evidence([_row("other_error", 3396)]), "event_analysis_success_rate_zero")

    assert result.status == "triggered"
    assert result.severity == "critical"
    assert result.metrics["successful_calls"] == 0
    assert result.metrics["total_calls"] == 3396


def test_any_success_clears_the_detector():
    result = _detector(
        _evidence([_row("success", 40), _row("other_error", 5)]),
        "event_analysis_success_rate_zero",
    )

    assert result.status == "clear"
    assert result.metrics["successful_calls"] == 40


def test_no_alert_counts_as_a_successful_analysis():
    # `no_alert` means the LLM answered and decided against alerting. That is a working
    # pipeline, not a failure, and must not read as an outage on a quiet market.
    result = _detector(_evidence([_row("no_alert", 12)]), "event_analysis_success_rate_zero")

    assert result.status == "clear"


def test_no_event_analysis_calls_is_unknown_not_clear():
    # Project rule: missing evidence is incomplete, never healthy.
    result = _detector(
        _evidence([_row("success", 3, call_type="market_heartbeat")]),
        "event_analysis_success_rate_zero",
    )

    assert result.status == "unknown"


def test_consecutive_zero_success_cycles_accumulate_across_runs():
    runs = [
        {"event_analysis": {"successful_calls": 0, "total_calls": 700}},
        {"event_analysis": {"successful_calls": 0, "total_calls": 720}},
    ]
    result = _detector(
        _evidence([_row("other_error", 700)], state_runs=runs),
        "event_analysis_success_rate_zero",
    )

    assert result.metrics["consecutive_zero_success_cycles"] == 3


def test_a_prior_successful_run_stops_the_streak():
    runs = [
        {"event_analysis": {"successful_calls": 0, "total_calls": 700}},
        {"event_analysis": {"successful_calls": 5, "total_calls": 700}},
        {"event_analysis": {"successful_calls": 0, "total_calls": 700}},
    ]
    assert consecutive_zero_success_runs({"recent_runs": runs}) == 1


def test_runs_without_the_signal_do_not_count_either_way():
    # Older state files have no event_analysis block. Neither healthy nor unhealthy.
    assert consecutive_zero_success_runs({"recent_runs": [{"status": "complete"}]}) == 0
    assert consecutive_zero_success_runs({}) == 0


def test_call_totals_ignore_other_call_types():
    rows = [_row("success", 5, call_type="daily_report"), _row("other_error", 2)]
    assert event_analysis_call_totals(rows) == (0, 2)


def test_state_records_the_per_run_signal():
    state = record_collection(
        {},
        bundle_id="b1",
        status="complete",
        period=PERIOD,
        event_analysis={"successful_calls": 0, "total_calls": 720},
    )

    assert state["recent_runs"][0]["event_analysis"] == {
        "successful_calls": 0,
        "total_calls": 720,
    }


# --- model drift -------------------------------------------------------------------------


def test_model_matching_the_shipped_default_is_clear():
    result = _detector(
        _evidence([_row("success", 10, model=SHIPPED_DEFAULT_MODELS["event_analysis"])]),
        "event_analysis_model_drift",
    )

    assert result.status == "clear"


def test_decommissioned_model_in_use_triggers_at_high_severity():
    # Exactly the production state during the outage: the deployed .env pinned a model the
    # provider had withdrawn, and no surface compared it against what the code shipped.
    result = _detector(
        _evidence([_row("other_error", 3396, model="meta-llama/llama-4-scout-17b-16e-instruct")]),
        "event_analysis_model_drift",
    )

    assert result.status == "triggered"
    assert result.severity == "high"
    assert result.metrics["decommissioned_primary_models_in_use"] == [
        "meta-llama/llama-4-scout-17b-16e-instruct"
    ]


def test_any_other_divergence_triggers_at_medium_severity():
    result = _detector(
        _evidence([_row("success", 10, model="llama-3.1-8b-instant")]),
        "event_analysis_model_drift",
    )

    assert result.status == "triggered"
    assert result.severity == "medium"
    assert result.metrics["drifted_primary_models"] == ["llama-3.1-8b-instant"]


def test_operator_can_declare_an_intentional_model_override(monkeypatch):
    monkeypatch.setenv("OPS_AGENT_EXPECTED_EVENT_ANALYSIS_MODEL", "llama-3.1-8b-instant")
    result = _detector(
        _evidence([_row("success", 10, model="llama-3.1-8b-instant")]),
        "event_analysis_model_drift",
    )

    assert result.status == "clear"


def test_no_recorded_model_is_unknown():
    result = _detector(_evidence([]), "event_analysis_model_drift")
    assert result.status == "unknown"


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        ("cerebras", "gpt-oss-120b"),
        ("gemini", "gemini-2.5-flash"),
        ("mistral", "mistral-small-latest"),
    ],
)
def test_fallback_models_do_not_count_as_primary_model_drift(provider, model):
    result = _detector(
        _evidence(
            [
                _row("success", 1, model=SHIPPED_DEFAULT_MODELS["event_analysis"]),
                _row("success", 1, provider=provider, model=model),
            ]
        ),
        "event_analysis_model_drift",
    )

    assert result.status == "clear"
    assert result.metrics["fallback_models_in_use"] == [model]


def test_fallback_only_evidence_is_unknown_not_primary_model_drift():
    result = _detector(
        _evidence([_row("success", 1, provider="cerebras", model="gpt-oss-120b")]),
        "event_analysis_model_drift",
    )

    assert result.status == "unknown"
    assert result.metrics["primary_models_in_use"] == []
    assert result.metrics["fallback_models_in_use"] == ["gpt-oss-120b"]


# --- repetition-evidence row cap ---------------------------------------------------------


def test_repetition_evidence_query_excludes_failed_analyses():
    for status in ("llm_error", "invalid_json", "schema_error", "skipped_due_to_rate_limit"):
        assert f"'{status}'" in ALERT_EVIDENCE_SQL
    assert "NOT IN" in ALERT_EVIDENCE_SQL


def test_repetition_evidence_query_stays_read_only_and_parameterized():
    lowered = ALERT_EVIDENCE_SQL.strip().lower()
    assert lowered.startswith("with")
    assert ";" not in ALERT_EVIDENCE_SQL
    for token in (" insert ", " update ", " delete ", " drop ", " alter "):
        assert token not in f" {lowered} "
    assert ":alert_evidence_limit" in ALERT_EVIDENCE_SQL


def _simulate_row_cap(rows, *, row_cap, bucket_hours=6):
    """Mimic the collector: newest bucket first, each bucket capped by remaining budget.

    A local stand-in for the SQL, so the flooding scenario is reproducible without PostgreSQL.
    """
    kept: list[dict] = []
    buckets: dict[int, list[dict]] = {}
    for row in rows:
        bucket = int((PERIOD.end - row["created_at"]).total_seconds() // (bucket_hours * 3600))
        buckets.setdefault(bucket, []).append(row)
    for bucket in sorted(buckets):
        if len(kept) >= row_cap:
            break
        ordered = sorted(buckets[bucket], key=lambda item: item["created_at"], reverse=True)
        kept.extend(ordered[: max(row_cap - len(kept), 1)])
    return kept[:row_cap]


def test_a_failure_storm_no_longer_starves_delivered_analyses_of_the_row_cap():
    # Reproduces the reported flooding: ~3400 failed analyses against a handful of delivered
    # ones, under the 500-row-per-bucket cap. Before the fix the delivered rows were pushed
    # out entirely and six alert-quality detectors reported `unknown`.
    rows = []
    for index in range(3396):
        rows.append(
            {
                "status": "llm_error",
                "created_at": PERIOD.end - timedelta(seconds=30 * (index + 1)),
            }
        )
    for index in range(6):
        rows.append(
            {
                "status": "success",
                "created_at": PERIOD.end - timedelta(hours=20, minutes=index),
            }
        )

    before = _simulate_row_cap(rows, row_cap=500)
    assert [row for row in before if row["status"] == "success"] == []

    excluded = {"llm_error", "invalid_json", "schema_error", "skipped_due_to_rate_limit"}
    after = _simulate_row_cap(
        [row for row in rows if row["status"] not in excluded], row_cap=500
    )
    assert len([row for row in after if row["status"] == "success"]) == 6
