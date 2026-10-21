"""Offline-first regression tests for the bounded CCW-16 dual-provider replay."""
import hashlib
import json
from datetime import datetime, timezone

import pytest

from scripts import ccw16_dual_provider_pilot as pilot


def _dataset():
    cases = []
    labels = {}
    for symbol in pilot.SYMBOLS:
        for warrant, n in (("alert", 3), ("no_alert", 3), ("ambiguous", 2)):
            for i in range(n):
                cid = f"{symbol.lower()}_{warrant}_{i}"
                case = {
                    "id": cid,
                    "symbol": symbol,
                    "input_sha256": hashlib.sha256(cid.encode()).hexdigest(),
                    "input": {"symbol": symbol, "market": {}},
                }
                cases.append(case)
                labels[cid] = {"warrant": warrant}
    return {"dataset_sha256": pilot.FROZEN_DATASET_SHA256, "cases": cases}, labels


def test_stratification_is_deterministic_and_provider_independent():
    ds, labels = _dataset()
    first = pilot.select_cases(ds, labels)
    second = pilot.select_cases(ds, labels)
    assert first == second
    assert len(first) == 20
    for symbol in pilot.SYMBOLS:
        chosen = [c for c in first if c["symbol"] == symbol]
        assert len(chosen) == 5
        assert [labels[c["id"]]["warrant"] for c in chosen].count("alert") == 2
        assert [labels[c["id"]]["warrant"] for c in chosen].count("no_alert") == 2
        assert [labels[c["id"]]["warrant"] for c in chosen].count("ambiguous") == 1


def test_provider_requests_use_same_messages_with_native_formats():
    inp = {"symbol": "BTC", "market": {}}
    prompt = "PROMPT\nInput JSON:\n{}"
    g = pilot.request_body("groq", inp, prompt)
    c = pilot.request_body("cloudflare", inp, prompt)
    assert g["messages"] == c["messages"]
    assert g["model"] == pilot.MODELS["groq"]
    assert c["model"] == pilot.MODELS["cloudflare"]
    assert g["max_tokens"] == 6300
    assert g["reasoning_effort"] == "medium"
    assert "reasoning_effort" not in c
    assert c["max_tokens"] == 300
    assert g["response_format"]["json_schema"]["schema"] == pilot.SCHEMA
    assert c["response_format"]["json_schema"] == pilot.SCHEMA


def test_reserved_budget_limits_before_call():
    ledger = {"attempts": [
        {"provider": "groq", "timestamp": "2026-10-21T10:00:00+00:00",
         "reserved": 11000, "state": "reserved"}
    ]}
    assert not pilot.budget_allows(ledger, "groq", 10000,
                                   datetime(2026, 10, 21, 12, tzinfo=timezone.utc))
    assert pilot.budget_allows(ledger, "cloudflare", 250,
                               datetime(2026, 10, 21, 12, tzinfo=timezone.utc))


def test_run_is_disabled_without_explicit_isolation_attestation(monkeypatch):
    for key in pilot.REQUIRED_ATTESTATIONS:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(RuntimeError, match="preflight"):
        pilot.require_live_preflight("groq")


def test_no_result_can_be_reported_as_scored_on_failed_provider_attempt():
    assert pilot.classify_result({"error": "provider_error"}) == "provider_error"
    assert pilot.classify_result({"content": "not json"}) == "invalid_json"
    assert pilot.classify_result({"content": json.dumps({"should_alert": True})}) == "schema_error"


def test_all_six_combinations_share_fixed_manifest_ids():
    ds, labels = _dataset()
    rows = pilot.select_cases(ds, labels)
    keys = pilot.work_items(rows)
    assert len(keys) == 120
    assert len({(x["id"], x["prompt"], x["provider"]) for x in keys}) == 120
    assert {x["id"] for x in keys} == {c["id"] for c in rows}
    assert {x["provider"] for x in keys} == set(pilot.MODELS)
    assert {x["prompt"] for x in keys} == set(pilot.PROMPTS)
