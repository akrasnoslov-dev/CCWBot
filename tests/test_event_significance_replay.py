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
    assert len(cases) == 16
    assert set(case["input"]["symbol"] for case in cases) == {"BTC", "ETH", "GRAM", "SOL"}
    for symbol in ("BTC", "ETH", "GRAM", "SOL"):
        group = [c for c in cases if c["input"]["symbol"] == symbol]
        assert Counter(c["expected_should_alert"] for c in group) == {
            True: 1, False: 2, None: 1,
        }
        assert {c["group"] for c in group} == {
            "routine", "significant", "repeat", "ambiguous",
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
    assert report["cases"] == 16
    assert report["expected_positive"] == 4
    assert report["expected_negative"] == 8
    assert report["unadjudicated"] == 4
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
