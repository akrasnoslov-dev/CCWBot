from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from ops_agent.alert_similarity import build_alert_evidence_payloads, normalize_alert_text
from ops_agent.schemas import Period


def _period() -> Period:
    return Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )


def _row(**overrides):
    base = {
        "symbol": "BTC",
        "market_event_id": 10,
        "event_type": "event_alert",
        "event_key": "btc_price_volatility",
        "event_instance_key": "instance-a",
        "price_change_percent": 1.2,
        "last_24h_change": 4.5,
        "last_7d_change": None,
        "detected_at": "2026-06-01T10:00:00Z",
        "event_ai_analysis_id": 100,
        "analysis_id": "event_analysis_btc_a",
        "analysis_symbol": "BTC",
        "analysis_type": "event_analysis",
        "provider": "groq",
        "model": "model",
        "input_hash": "input-a",
        "analysis_status": "success",
        "should_alert": True,
        "analysis_event_key": "btc_price_volatility",
        "analysis_title": "BTC volatility expanded after ETF news",
        "analysis_message_body": "BTC volatility expanded after ETF news near $100000.",
        "analysis_possible_action": "Watch confirmation.",
        "urgency": "normal",
        "confidence": "medium",
        "analysis_reason_for_no_alert": None,
        "related_news_ids": '["n1"]',
        "analysis_plain_text": "BTC volatility expanded after ETF news. Not financial advice.",
        "analysis_created_at": "2026-06-01T10:00:00Z",
        "delivery_count": 1,
        "sent_delivery_count": 1,
        "failed_delivery_count": 0,
        "distinct_recipient_count": 1,
        "first_delivery_at": "2026-06-01T10:01:00Z",
        "last_delivery_at": "2026-06-01T10:01:00Z",
        "alert_type": "event_alert",
        "trigger_source": "event_analysis",
        "status": "sent",
        "alert_message": (
            "BTC volatility expanded after ETF news near $100000. Not financial advice."
        ),
    }
    base.update(overrides)
    return base


def _numeric_context_json(**values) -> str:
    return json.dumps(values, sort_keys=True)


def test_normalize_alert_text_strips_numbers_urls_and_disclaimer():
    normalized = normalize_alert_text(
        "BTC moved +3.4% near $101,000 https://example.test Not financial advice."
    )

    assert "101" not in normalized
    assert "3.4" not in normalized
    assert "http" not in normalized
    assert "financial" not in normalized


def test_alert_evidence_uses_hashes_without_raw_alert_text():
    payloads = build_alert_evidence_payloads(
        [_row()],
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )
    encoded = json.dumps(payloads, sort_keys=True)

    assert "BTC volatility expanded after ETF news near" not in encoded
    assert "$100000" not in encoded
    assert "content_ref:h_" in encoded
    assert "analysis_content_ref:h_" in encoded


def test_alert_quality_groups_placeholder_and_missing_market_context():
    payloads = build_alert_evidence_payloads(
        [
            _row(
                alert_message=(
                    "BTC Event Alert. Since last BTC alert: n/a. "
                    "Analysed-window change: n/a. Not financial advice."
                ),
                trigger_source="news",
                related_news_ids="[]",
                delivery_count=82,
                sent_delivery_count=82,
                distinct_recipient_count=82,
                price_change_percent=None,
            ),
            _row(
                market_event_id=11,
                event_ai_analysis_id=101,
                alert_message="BTC context unavailable and unknown. Not financial advice.",
                trigger_source="news",
                delivery_count=2,
                sent_delivery_count=2,
                distinct_recipient_count=2,
            ),
        ],
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )

    quality = payloads["evidence/db/alert_quality.json"]
    issues = {(row["issue"], row["trigger_source"]) for row in quality["issues"]}

    assert ("contains_n_a", "news") in issues
    assert ("contains_unknown", "news") in issues
    assert ("contains_unavailable", "news") in issues
    assert ("old_since_last_btc_alert_label", "news") in issues
    assert ("old_analysed_window_change_label", "news") in issues
    assert ("empty_related_context", "news") in issues
    assert quality["total_event_alert_deliveries"] == 84
    assert quality["affected_event_alert_deliveries"] == 84
    assert quality["severe_affected_event_alert_deliveries"] == 84
    assert quality["quality_issue_occurrences"] > quality["affected_event_alert_deliveries"]
    assert "Since last BTC alert" not in json.dumps(quality)
    regression = payloads["evidence/db/event_alert_regression_checks.json"]
    assert regression["status"] == "critical"
    assert regression["placeholder_issue_counts"]["contains_n_a"] == 82
    assert regression["old_label_issue_counts"]["old_since_last_btc_alert_label"] == 82


def test_alert_quality_placeholder_detection_uses_token_boundaries():
    payloads = build_alert_evidence_payloads(
        [
            _row(
                alert_message=(
                    "BTC Event Alert. Nullification risk is known, with no placeholder token."
                ),
                delivery_count=1,
                sent_delivery_count=1,
            )
        ],
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )

    issues = {
        row["issue"] for row in payloads["evidence/db/alert_quality.json"]["issues"]
    }

    assert "contains_null" not in issues
    assert "contains_unknown" not in issues


@pytest.mark.parametrize(
    "alert_message",
    [
        "Price change: +1.20%\nNot financial advice.",
        "• Price change: -2.40%\nNot financial advice.",
        "- Price change: +0.80%\nNot financial advice.",
        "BTC Event Alert\n\nPrice change: +1.20%\nNot financial advice.",
    ],
)
def test_alert_quality_detects_old_price_change_label_only_as_label(alert_message):
    payloads = build_alert_evidence_payloads(
        [_row(alert_message=alert_message)],
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )

    issues = {
        row["issue"] for row in payloads["evidence/db/alert_quality.json"]["issues"]
    }

    assert "old_generic_price_change_label" in issues


@pytest.mark.parametrize(
    "alert_message",
    [
        "A price change alone is not enough.",
        "This price change may be related to broader market conditions.",
        "The price change is still small.",
    ],
)
def test_alert_quality_ignores_price_change_in_normal_sentences(alert_message):
    payloads = build_alert_evidence_payloads(
        [_row(alert_message=alert_message)],
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )

    issues = {
        row["issue"] for row in payloads["evidence/db/alert_quality.json"]["issues"]
    }

    assert "old_generic_price_change_label" not in issues


def test_alert_quality_ignores_old_label_in_internal_analysis_only():
    payloads = build_alert_evidence_payloads(
        [
            _row(
                alert_message=(
                    "BTC Event Alert\n\nMarket context remains mixed. Not financial advice."
                ),
                analysis_plain_text="Internal analysis: 24h change: -4.2%.",
                analysis_message_body="24h change: -4.2%.",
            )
        ],
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )

    issues = {row["issue"] for row in payloads["evidence/db/alert_quality.json"]["issues"]}

    assert "old_24h_change_label" not in issues


def test_alert_quality_detects_old_24h_label_in_delivered_event_alert():
    payloads = build_alert_evidence_payloads(
        [_row(alert_message="BTC Event Alert\n24h change: -4.2%\nNot financial advice.")],
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )

    issues = {row["issue"] for row in payloads["evidence/db/alert_quality.json"]["issues"]}

    assert "old_24h_change_label" in issues


def test_alert_quality_preserves_other_delivered_old_label_detection():
    payloads = build_alert_evidence_payloads(
        [_row(alert_message="BTC Event Alert\nSince last BTC alert: -4.2%\nNot financial advice.")],
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )

    issues = {row["issue"] for row in payloads["evidence/db/alert_quality.json"]["issues"]}

    assert "old_since_last_btc_alert_label" in issues


def test_alert_quality_clean_delivered_event_alert_stays_clean():
    payloads = build_alert_evidence_payloads(
        [_row(alert_message="BTC Event Alert\nMarket context is mixed. Not financial advice.")],
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )

    issues = {row["issue"] for row in payloads["evidence/db/alert_quality.json"]["issues"]}

    assert not {
        "old_24h_change_label",
        "old_since_last_btc_alert_label",
        "old_analysed_window_change_label",
        "old_generic_price_change_label",
    }.intersection(issues)


def test_exact_and_similar_alert_groups_are_derived():
    rows = [
        _row(
            market_event_id=10,
            event_ai_analysis_id=100,
            alert_message="BTC volatility expanded after ETF news near $100000.",
        ),
        _row(
            market_event_id=11,
            event_ai_analysis_id=101,
            event_instance_key="instance-b",
            input_hash="input-b",
            detected_at="2026-06-01T11:00:00Z",
            analysis_created_at="2026-06-01T11:00:00Z",
            first_delivery_at="2026-06-01T11:01:00Z",
            last_delivery_at="2026-06-01T11:01:00Z",
            alert_message="BTC volatility expanded after ETF news near $101000.",
        ),
        _row(
            market_event_id=12,
            event_ai_analysis_id=102,
            event_key="btc_etf_headlines",
            analysis_event_key="btc_etf_headlines",
            event_instance_key="instance-c",
            input_hash="input-c",
            detected_at="2026-06-01T12:00:00Z",
            analysis_created_at="2026-06-01T12:00:00Z",
            first_delivery_at="2026-06-01T12:01:00Z",
            last_delivery_at="2026-06-01T12:01:00Z",
            alert_message="BTC volatility expanded after ETF news near $102000.",
            analysis_plain_text="BTC volatility expanded after ETF news.",
        ),
    ]

    payloads = build_alert_evidence_payloads(
        rows,
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )

    repeated = payloads["evidence/db/alert_content_fingerprints.json"]["repeated_groups"]
    similar = payloads["evidence/db/alert_similarity_groups.json"]["groups"]
    identity = payloads["evidence/db/event_identity_quality.json"]

    assert repeated
    assert repeated[0]["market_events"] >= 2
    assert similar
    assert any(group["market_events"] >= 2 for group in similar)
    assert identity["same_content_split_key_groups"]


def test_suppression_effectiveness_flags_inside_cooldown_candidates():
    rows = [
        _row(first_delivery_at="2026-06-01T10:01:00Z", last_delivery_at="2026-06-01T10:01:00Z"),
        _row(
            market_event_id=11,
            event_ai_analysis_id=101,
            event_instance_key="instance-b",
            input_hash="input-b",
            analysis_created_at="2026-06-01T11:00:00Z",
            first_delivery_at="2026-06-01T11:01:00Z",
            last_delivery_at="2026-06-01T11:01:00Z",
        ),
    ]

    payloads = build_alert_evidence_payloads(
        rows,
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )
    groups = payloads["evidence/db/backend_suppression_effectiveness.json"]["suppression_groups"]

    assert groups[0]["delivered_inside_cooldown_candidates"] == 1
    assert groups[0]["confidence"] == "medium"


def test_suppression_effectiveness_marks_allowed_escalation_separately():
    rows = [
        _row(
            first_delivery_at="2026-06-01T10:01:00Z",
            last_delivery_at="2026-06-01T10:01:00Z",
            alert_numeric_context=_numeric_context_json(
                notification_severity="normal",
                analysed_window_change_percent=-3.0,
                semantic_family="price_downtrend",
                stable_related_news_ids=["old"],
            ),
        ),
        _row(
            market_event_id=11,
            event_ai_analysis_id=101,
            event_instance_key="instance-b",
            input_hash="input-b",
            analysis_created_at="2026-06-01T11:00:00Z",
            urgency="high",
            first_delivery_at="2026-06-01T11:01:00Z",
            last_delivery_at="2026-06-01T11:01:00Z",
            alert_numeric_context=_numeric_context_json(
                notification_severity="high",
                analysed_window_change_percent=-3.2,
                semantic_family="price_downtrend",
                stable_related_news_ids=["old"],
            ),
        ),
    ]

    payloads = build_alert_evidence_payloads(
        rows,
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )
    groups = payloads["evidence/db/backend_suppression_effectiveness.json"]["suppression_groups"]
    regression = payloads["evidence/db/event_alert_regression_checks.json"]

    assert groups[0]["delivered_inside_cooldown_candidates"] == 0
    assert groups[0]["delivered_inside_cooldown_allowed_escalations"] == 1
    assert groups[0]["allowed_escalation_reasons"] == {"urgency_increased": 1}
    assert regression["same_family_repeat_noise_groups"] == 0
    assert regression["same_family_allowed_escalation_groups"] == 1


def test_suppression_effectiveness_marks_material_movement_escalation_separately():
    rows = [
        _row(
            first_delivery_at="2026-06-01T10:01:00Z",
            last_delivery_at="2026-06-01T10:01:00Z",
            alert_numeric_context=_numeric_context_json(
                notification_severity="normal",
                analysed_window_change_percent=-1.0,
                semantic_family="price_downtrend",
                stable_related_news_ids=["old"],
            ),
        ),
        _row(
            market_event_id=11,
            event_ai_analysis_id=101,
            event_instance_key="instance-b",
            input_hash="input-b",
            analysis_created_at="2026-06-01T11:00:00Z",
            first_delivery_at="2026-06-01T11:01:00Z",
            last_delivery_at="2026-06-01T11:01:00Z",
            alert_numeric_context=_numeric_context_json(
                notification_severity="normal",
                analysed_window_change_percent=-3.6,
                semantic_family="price_downtrend",
                stable_related_news_ids=["old"],
            ),
        ),
    ]

    payloads = build_alert_evidence_payloads(
        rows,
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )
    groups = payloads["evidence/db/backend_suppression_effectiveness.json"]["suppression_groups"]

    assert groups[0]["delivered_inside_cooldown_candidates"] == 0
    assert groups[0]["allowed_escalation_reasons"] == {"material_movement_increased": 1}


def test_suppression_effectiveness_does_not_allow_new_news_driver_alone():
    rows = [
        _row(
            first_delivery_at="2026-06-01T10:01:00Z",
            last_delivery_at="2026-06-01T10:01:00Z",
            alert_numeric_context=_numeric_context_json(
                notification_severity="normal",
                analysed_window_change_percent=-3.0,
                semantic_family="news_catalyst",
                stable_related_news_ids=["old"],
            ),
        ),
        _row(
            market_event_id=11,
            event_ai_analysis_id=101,
            event_instance_key="instance-b",
            input_hash="input-b",
            analysis_created_at="2026-06-01T11:00:00Z",
            first_delivery_at="2026-06-01T11:01:00Z",
            last_delivery_at="2026-06-01T11:01:00Z",
            alert_numeric_context=_numeric_context_json(
                notification_severity="normal",
                analysed_window_change_percent=-3.2,
                semantic_family="news_catalyst",
                stable_related_news_ids=["old", "new"],
            ),
        ),
    ]

    payloads = build_alert_evidence_payloads(
        rows,
        period=_period(),
        row_cap=10,
        semantic_cooldown_seconds=14400,
    )
    groups = payloads["evidence/db/backend_suppression_effectiveness.json"]["suppression_groups"]

    assert groups[0]["delivered_inside_cooldown_candidates"] == 1
    assert groups[0]["allowed_escalation_reasons"] == {}


def test_similarity_memberships_link_recipients_without_exporting_source_ids():
    rows = [
        _row(
            delivery_members=[{"recipient_id": 101, "alert_id": 1001, "status": "sent"}],
            alert_message="BTC volatility expanded after ETF news near $100000.",
        ),
        _row(
            market_event_id=11,
            event_ai_analysis_id=101,
            event_instance_key="instance-b",
            input_hash="input-b",
            delivery_members=[{"recipient_id": 101, "alert_id": 1002, "status": "sent"}],
            alert_message="BTC volatility expanded after ETF news near $101000.",
        ),
        _row(
            market_event_id=12,
            event_ai_analysis_id=102,
            event_instance_key="instance-c",
            input_hash="input-c",
            delivery_members=[
                {
                    "recipient_id": 202,
                    "alert_id": None,
                    "outcome_id": 2003,
                    "status": "suppressed",
                }
            ],
            alert_message="BTC volatility expanded after ETF news near $102000.",
        ),
    ]

    payloads = build_alert_evidence_payloads(
        rows, period=_period(), row_cap=10, semantic_cooldown_seconds=14400
    )
    evidence = payloads["evidence/db/alert_similarity_groups.json"]
    memberships = evidence["memberships"]

    assert len(memberships) == 3
    recipient_refs = [member["recipient_ref"] for member in memberships]
    assert len(set(recipient_refs)) == 2
    assert any(recipient_refs.count(reference) == 2 for reference in recipient_refs)
    assert {member["status"] for member in memberships} == {"sent", "suppressed"}
    assert all(member["market_event_ref"] and member["analysis_ref"] for member in memberships)
    suppressed = next(member for member in memberships if member["status"] == "suppressed")
    assert suppressed["alert_ref"] is None
    assert suppressed["outcome_ref"].startswith("outcome_ref:h_")
    encoded = json.dumps(evidence, sort_keys=True)
    for source_id in ("101", "202", "1001", "1002", "2003"):
        assert f'"{source_id}"' not in encoded
    assert "volatility expanded" not in encoded
