"""Pure local tests; no Groq calls, Telegram deliveries or real credentials."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts import auto_event_significance_replay as auto


@pytest.fixture
def now():
    return datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def empty_ledger():
    return {"attempted_requests": 226, "runs": {}}


def test_rolling_window_conservatively_reserves_for_running_bot(now, empty_ledger):
    private = {
        "history": [
            {"at": (now - timedelta(hours=1)).isoformat(),
             "reserved_tokens": 8300}
            for _ in range(7)
        ],
        "rate_limit_streak": 0, "not_before": None,
    }
    allowed, reason = auto.compute_next_eligible(private, empty_ledger, now=now)
    assert not allowed and reason == "rolling_24h_token_reserve"
    private["history"] = private["history"][:1]
    assert auto.compute_next_eligible(private, empty_ledger, now=now) == (
        True, "eligible",
    )
    # A reservation more than 24h ago does not consume the new rolling window.
    private["history"] = [{
        "at": (now - timedelta(hours=25)).isoformat(),
        "reserved_tokens": 8300,
    }]
    assert auto.compute_next_eligible(private, empty_ledger, now=now)[0]


def test_scheduler_early_retrigger_never_spends_second_request(now, empty_ledger):
    private = {
        "history": [{
            "at": (now - timedelta(minutes=5)).isoformat(),
            "reserved_tokens": auto.RESERVATION_TOKENS,
        }],
        "rate_limit_streak": 0,
        "not_before": None,
    }
    allowed, reason = auto.compute_next_eligible(private, empty_ledger, now=now)
    assert not allowed and reason == "minimum_hourly_interval"
    allowed, reason = auto.compute_next_eligible(
        private, empty_ledger, now=now + timedelta(hours=1),
    )
    assert allowed and reason == "eligible"


def test_retry_after_and_extra_backoff_survive_worker_restarts(now, empty_ledger):
    empty_ledger["runs"]["market_signal_path"] = [{
        "id": "frozen",
        "http_status": 429,
        "rate_limit_at_utc": (now - timedelta(seconds=60)).isoformat(),
        "retry_after_seconds": 600,
    }]
    state = {"history": [], "rate_limit_streak": 1, "not_before": None}
    assert auto.compute_next_eligible(state, empty_ledger, now=now)[1] == (
        "provider_retry_after_active"
    )
    empty_ledger["runs"]["market_signal_path"] = []
    state["not_before"] = (now + timedelta(hours=2)).isoformat()
    assert auto.compute_next_eligible(state, empty_ledger, now=now)[1] == (
        "consecutive_rate_limit_backoff"
    )
    state["rate_limit_streak"] = 3
    state["not_before"] = None
    assert auto.compute_next_eligible(state, empty_ledger, now=now)[1] == (
        "repeated_429_manual_review_required"
    )


def test_never_exceeds_approved_calls_or_token_safety(now, empty_ledger):
    state = {"history": [], "rate_limit_streak": 0, "not_before": None}
    empty_ledger["attempted_requests"] = auto.MAX_APPROVED_CALLS
    assert auto.compute_next_eligible(state, empty_ledger, now=now)[1] == (
        "replay_call_safety_ceiling"
    )
    empty_ledger["attempted_requests"] = 100
    empty_ledger["runs"]["production"] = [
        {"total_tokens": 5_101_000, "status": "valid"},
    ]
    assert auto.compute_next_eligible(state, empty_ledger, now=now)[1] == (
        "total_token_safety_ceiling"
    )


def test_private_status_has_only_allowlisted_safety_fields(tmp_path, now):
    status_file = tmp_path / "state.json"
    result = auto.record_status(
        status_file, {"history": [], "not_before": None},
        reason="provider_retry_after_active", attempts=226,
    )
    assert result["attempts"] == 226
    payload = json.loads(status_file.read_text(encoding="utf-8"))
    assert payload["status"] == "provider_retry_after_active"
    assert "GROQ_API_KEY" not in status_file.read_text(encoding="utf-8")
    assert auto.read_private_status(status_file) == payload


def test_missing_local_reference_never_issues_provider_request(tmp_path, monkeypatch):
    monkeypatch.setattr(auto, "PRIVATE", tmp_path)
    monkeypatch.setattr(auto, "LEDGER_DIR", tmp_path / "run")
    assert auto.run_once() == {"status": "private_frozen_cases_unavailable"}


def test_lock_is_exclusive_and_released_after_error(tmp_path):
    lock_path = tmp_path / ".lock"
    with auto.exclusive_worker_lock(lock_path):
        with pytest.raises(RuntimeError, match="already running"):
            with auto.exclusive_worker_lock(lock_path):
                pass
    with auto.exclusive_worker_lock(lock_path):
        pass


def test_one_worker_invocation_makes_at_most_one_approved_request(
    tmp_path, monkeypatch, now,
):
    private = tmp_path / "private"
    run = private / "merged_pilots_private"
    run.mkdir(parents=True)
    (private / "v2_private_sanitized.json").write_text("{}", encoding="utf-8")
    (private / "reviewer_A_significance_for_pr1.json").write_text("{}", encoding="utf-8")
    (run / "replay_state.json").write_text(json.dumps({
        "dataset_sha256": "fixed", "attempted_requests": 226, "runs": {
            auto.VARIANT: [],
        },
    }), encoding="utf-8")
    monkeypatch.setattr(auto, "PRIVATE", private)
    monkeypatch.setattr(auto, "LEDGER_DIR", run)
    monkeypatch.setattr(auto, "load_frozen", lambda _: {
        "dataset_sha256": "fixed", "cases": [{"id": "case", "symbol": "BTC"}],
    })
    monkeypatch.setattr(auto, "load_reviewer_a", lambda *_: {"case": "alert"})
    calls = []

    async def fake_replay(_dataset, _labels, _out, **kwargs):
        calls.append(kwargs)
        ledger = run / "replay_state.json"
        payload = json.loads(ledger.read_text(encoding="utf-8"))
        payload["attempted_requests"] += 1
        payload["runs"][auto.VARIANT].append({
            "id": "case", "status": "valid", "should_alert": True,
        })
        ledger.write_text(json.dumps(payload), encoding="utf-8")
        return {"stop": "requested_limit", "attempts_this_invocation": 1}

    monkeypatch.setattr(auto, "replay", fake_replay)
    assert auto.run_once(now=now)["attempts"] == 227
    assert calls[0]["max_requests"] == 1
    assert calls[0]["screen_positives_first"] is True
    assert calls[0]["stop_on_impossible_gates"] is True
    assert calls[0]["retry_rate_limited"] is True
    assert auto.run_once(now=now)["status"] == "candidate_fully_scored_review_required"
    assert len(calls) == 1
