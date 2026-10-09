"""Production timeline review tests: decision counts are not ground-truth FP/FN."""

from __future__ import annotations

import pytest

from scripts.audit_event_analysis_timeline import audit


def _row(symbol, at, should_alert, move, rarity, *, deliveries=0):
    return {
        "symbol": symbol,
        "analysis_created_at": at,
        "analysis_ref": f"analysis_ref:safe_{symbol}_{at}",
        "should_alert": should_alert,
        "analysed_window_change_percent": move,
        "relative_window_percentile_30d": rarity,
        "sent_delivery_count": deliveries,
    }


def test_audit_stratifies_both_decisions_without_inventing_false_negative_labels():
    rows = [
        _row("BTC", "2026-10-09T08:00:00Z", True, -1.6, 98.5, deliveries=4),
        _row("BTC", "2026-10-09T08:30:00Z", False, -2.3, 99.7),
        _row("BTC", "2026-10-09T09:00:00Z", False, -0.05, 9.0),
        _row("ETH", "2026-10-09T08:30:00Z", False, -4.5, 99.9),
        _row("GRAM", "2026-10-09T08:30:00Z", True, 0.2, 15),
        _row("SOL", "2026-10-09T08:30:00Z", True, 4.3, 98),
    ]
    report = audit(rows)
    assert report["completed_decisions"] == 6
    assert report["positive"] == 3
    assert report["negative"] == 3
    assert report["false_positive_count"] is None
    assert report["false_negative_count"] is None
    assert "snapshots" in report["missing_llm_input_fields"]
    assert set(report["by_symbol"]) == {"BTC", "ETH", "GRAM", "SOL"}
    btc = report["by_symbol"]["BTC"]["selected_for_review"]
    high_move_negative = next(x for x in btc if x["selection_reason"] == "largest_negative")
    assert high_move_negative["recorded_should_alert"] is False
    assert high_move_negative["previous_positive_minutes_ago"] == 30
    assert high_move_negative["previous_positive_was_delivered"] is True
    assert high_move_negative["needs_manual_adjudication"] is True
    assert all("bundle_local_analysis_ref" not in x for x in btc)


def test_audit_can_include_only_bundle_local_refs_on_explicit_request():
    row = _row("ETH", "2026-10-09T08:30:00Z", False, -4.5, 99.9)
    result = audit([row], show_refs=True)
    selection = result["by_symbol"]["ETH"]["selected_for_review"]
    assert selection[0]["bundle_local_analysis_ref"] == row["analysis_ref"]


def test_audit_rejects_unsanitized_or_incompatible_structure():
    with pytest.raises(ValueError, match="rows array"):
        audit({"raw": "data"})
    with pytest.raises(ValueError, match="sanitized schema"):
        audit([{"symbol": "SOL"}])


def test_audit_targets_countertrend_and_new_negative_episodes():
    rows = [
        _row("GRAM", "2026-10-09T08:00:00Z", True, -2.0, 96),
        _row("GRAM", "2026-10-09T08:30:00Z", False, 1.8, 86),
        _row("GRAM", "2026-10-09T09:00:00Z", False, -2.2, 97),
        _row("ETH", "2026-10-09T08:30:00Z", False, -4.5, 99.9),
    ]
    report = audit(rows)
    gram = report["by_symbol"]["GRAM"]
    assert gram["countertrend_negative_count"] == 1
    assert gram["no_recent_positive_negative_count"] == 0
    assert any(
        "countertrend_negative" in item["review_reasons"] for item in gram["selected_for_review"]
    )
    eth = report["by_symbol"]["ETH"]
    assert eth["no_recent_positive_negative_count"] == 1
    assert any(
        "no_recent_positive_negative" in item["review_reasons"]
        for item in eth["selected_for_review"]
    )
    assert report["false_negative_count"] is None
