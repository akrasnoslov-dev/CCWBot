"""Offline guardrails for the synthetic low/medium replay harness."""
from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

from bot.services.llm import config
from scripts import replay_event_significance as replay


def test_synthetic_replay_has_both_labels_and_all_market_symbols():
    cases = replay.load_cases()
    assert len(cases) == 24
    assert set(case["input"]["symbol"] for case in cases) == {"BTC", "ETH", "GRAM", "SOL"}
    for symbol in ("BTC", "ETH", "GRAM", "SOL"):
        group = [c for c in cases if c["input"]["symbol"] == symbol]
        assert Counter(c["expected_should_alert"] for c in group) == {
            True: 2, False: 2, None: 2,
        }
        assert {c["group"] for c in group} == {
            "routine", "significant", "significant_up", "repeat",
            "ambiguous", "borderline",
        }
    assert all(c["source"] == "SYNTHETIC_NOT_PRODUCTION" for c in cases)


def test_replay_passes_the_identical_semantic_input_to_both_efforts(monkeypatch):
    for case in replay.load_cases():
        monkeypatch.setenv("LLM_EVENT_ANALYSIS_REASONING_EFFORT", "low")
        low = replay.prompt_for(case)
        monkeypatch.setenv("LLM_EVENT_ANALYSIS_REASONING_EFFORT", "medium")
        medium = replay.prompt_for(case)
        assert low == medium
        assert case["input"]["symbol"] in low


def test_replay_offline_requires_no_provider_key_or_calls(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    cases = replay.load_cases()
    report = replay.offline_report(cases)
    assert report["cases"] == 24
    assert report["expected_positive"] == 8
    assert report["expected_negative"] == 8
    assert report["unadjudicated"] == 8
    assert "no provider requests" in report["provenance"]
    assert all(data["decision_metrics"] == "NOT MEASURED"
               for data in report["efforts"].values())


def test_replay_budget_respects_groq_free_tier(monkeypatch):
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("LLM_EVENT_ANALYSIS_REASONING_EFFORT", raising=False)
    model = "openai/gpt-oss-120b"
    assert config.effective_max_tokens_for(
        call_type="event_analysis", provider="groq", model=model
    ) == 6300
    monkeypatch.setenv("LLM_EVENT_ANALYSIS_REASONING_EFFORT", "low")
    assert config.effective_max_tokens_for(
        call_type="event_analysis", provider="groq", model=model
    ) == 1324


def test_replay_live_requires_two_explicit_flags():
    script = Path(replay.__file__)
    result = subprocess.run(
        [sys.executable, str(script), "--live", "--case", "btc_routine_news"],
        capture_output=True, text=True, check=False,
        env={k: v for k, v in os.environ.items() if k != "GROQ_API_KEY"},
        timeout=10,
    )
    assert result.returncode != 0
    assert "--live requires --approve-provider-requests" in result.stderr


def test_replay_snapshot_changes_agree_with_provided_market_metrics():
    # Fixture consistency only. These are not alert significance thresholds.
    for case in replay.load_cases():
        market = case["input"]["market"]
        observations = market["snapshots"]
        assert [item["m"] for item in observations] == [-60, -30, 0]
        one_hour = 100 * (observations[-1]["p"] / observations[0]["p"] - 1)
        half_hour = 100 * (observations[-1]["p"] / observations[-2]["p"] - 1)
        assert abs(one_hour - market["chg1h_percent"]) < 0.002, case["id"]
        assert abs(half_hour - market["chg30m_percent"]) < 0.002, case["id"]
        assert abs(half_hour - market["chg_window_percent"]) < 0.002, case["id"]
        assert market["analysed_window_minutes"] == 30


def test_replay_uses_production_strict_groq_significance_schema(monkeypatch):
    monkeypatch.delenv("GROQ_JSON_MODE", raising=False)
    from bot.services import ai_agent_groq

    schema = replay.groq_significance_response_format()
    assert schema == {
        "type": "json_schema",
        "json_schema": {
            "name": "event_significance",
            "strict": True,
            "schema": ai_agent_groq._EVENT_SIGNIFICANCE_JSON_SCHEMA,
        },
    }


def test_replay_scoring_does_not_conflate_errors_with_negative_decisions():
    def answer(decision, prompt=400, completion=200):
        return {"status": "valid", "decision": decision,
                "prompt_tokens": prompt, "completion_tokens": completion,
                "total_tokens": prompt + completion}

    rows = [
        {"case": "positive", "expected": True,
         "low": answer(False), "medium": answer(True, completion=350)},
        {"case": "negative", "expected": False,
         "low": answer(True), "medium": answer(False)},
        {"case": "schema_failure", "expected": False,
         "low": {"status": "schema_error"},
         "medium": answer(False)},
        {"case": "borderline", "expected": None,
         "low": answer(False), "medium": answer(True)},
    ]
    result = replay.summarize_rows(rows)
    assert result["paired_valid_cases"] == 3
    assert result["paired_decision_disagreements"] == 3
    assert result["unadjudicated_case_ids"] == ["borderline"]
    assert result["scores"]["low"]["false_positive"] == 1
    assert result["scores"]["low"]["false_negative"] == 1
    assert result["scores"]["low"]["failed_or_invalid"] == 1
    assert result["scores"]["low"]["schema_invalid_calls"] == 1
    assert result["scores"]["medium"]["true_positive"] == 1
    assert result["scores"]["medium"]["true_negative"] == 2
    assert result["scores"]["medium"]["accuracy_valid_adjudicated"] == 1
    assert result["scores"]["medium"]["actual_completion_tokens"] == 950
