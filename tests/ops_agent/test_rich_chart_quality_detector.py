"""Regressions for rich Telegram charts persisted as plain alternatives."""

from ops_agent.alert_similarity import (
    RICH_ALERT_CHART_TEXT_FALLBACK,
    _quality_issues,
)
from ops_agent.db_queries import QUERIES


def _issues(message: str, *, alert_type: str = "event_alert") -> list[str]:
    row = {
        "alert_type": alert_type,
        "market_event_id": 123 if alert_type == "event_alert" else None,
        "alert_message": message,
    }
    return _quality_issues(row, delivered_text=message, related_news_count=1)


def test_exact_chart_fallback_is_not_a_quality_failure_for_rich_alerts():
    message = (
        "BTC Event Alert\n"
        "Price (now): $81,378.00\n"
        + RICH_ALERT_CHART_TEXT_FALLBACK
        + "\nSituation: Observed move.\nPossible action: Watch the trend."
    )
    assert "contains_unavailable" not in _issues(message)
    queries = {item.name: item.sql for item in QUERIES}
    for name in ("alert_quality_summary", "user_impact_summary"):
        assert RICH_ALERT_CHART_TEXT_FALLBACK in queries[name]


def test_other_unavailable_text_is_still_flagged():
    message = (
        RICH_ALERT_CHART_TEXT_FALLBACK
        + "\nSituation: Reliable direction is unavailable for this interval."
    )
    assert "contains_unavailable" in _issues(message)


def test_heartbeat_unavailable_is_not_suppressed_by_event_alert_exception():
    assert "contains_unavailable" in _issues(
        RICH_ALERT_CHART_TEXT_FALLBACK, alert_type="market_heartbeat",
    )


def test_other_placeholders_and_old_labels_remain_detectable():
    message = (
        RICH_ALERT_CHART_TEXT_FALLBACK
        + "\nSituation: unknown\nAnalysed-window change: n/a"
    )
    issues = _issues(message)
    assert "contains_unavailable" not in issues
    assert "contains_unknown" in issues
    assert "contains_n_a" in issues
    assert "old_analysed_window_change_label" in issues
