"""Event Alert metric/title and true observed NOW continuity regressions."""

from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace

from PIL import Image

from bot import alerts
from bot.alerting.event_analysis import EventAnalysisDecision
from bot.alerting.event_chart import (
    _connectable_now_segment,
    _reference_markers,
    render_price_chart,
)

AT = datetime(2026, 10, 29, 18, 0, tzinfo=timezone.utc)


def history(*, last_offset_minutes=30):
    # Observed half-hour cadence; no fabricated samples.
    return [
        SimpleNamespace(
            checked_at=AT - timedelta(minutes=last_offset_minutes + 30 * (8 - i)),
            price=100.0 + i * 0.25,
        )
        for i in range(9)
    ]


def market_payload(day):
    return {
        "market": {
            "price": 102.3,
            "chg_window_percent": -0.93,
            "analysed_window_minutes": 180,
            "chg24h_percent": day,
            "snapshots": [
                {"m": -90, "p": 104.0},
                {"m": -60, "p": 103.0},
                {"m": -30, "p": 102.7},
                {"m": 0, "p": 102.3},
            ],
        },
    }


def decision():
    return EventAnalysisDecision(
        symbol="SOL", should_alert=True, event_key=None, title=None,
        message_body="The latest observed decline aligns with the broader 24-hour trend.",
        related_news_ids=[], possible_action=(
            "Watch whether the next observed interval extends the decline or reverses it."
        ),
        urgency="normal", confidence="high", reason_for_no_alert=None,
    )


def test_24h_metric_and_unambiguous_header_in_all_delivery_formats():
    payload = alerts._build_event_alert_payload(
        decision=decision(), input_payload=market_payload(-4.15), related_news=[],
    )
    for key in ("plain_text", "html_text", "rich_html"):
        output = payload[key]
        assert "SOL Event Alert: -0.93%" in output
        assert "SOL Event Alert — -0.93%" not in output
        assert "3h market move: -0.93%" in output
        assert "24h market move: -4.15%" in output
        assert output.index("3h market move") < output.index("24h market move")
    # Market data does not come from, or change with, a recipient's last message.
    result = alerts._event_alert_for_recipient(
        payload, previous_alert=None, current_price=102.3, as_of=AT,
    )
    assert "24h market move: -4.15%" in result["rich_html"]


def test_unknown_24h_change_is_omitted_not_assumed_zero():
    payload = alerts._build_event_alert_payload(
        decision=decision(), input_payload=market_payload(None), related_news=[],
    )
    for key in ("plain_text", "html_text", "rich_html"):
        assert "24h market move" not in payload[key]


def test_now_joins_last_recorded_price_within_real_sampling_cadence():
    rows = history(last_offset_minutes=30)
    chart = render_price_chart(
        rows, as_of=AT, symbol="BTC", event_markers=True,
        current_observation=(AT, 102.5),
    )
    assert chart.png and Image.open(BytesIO(chart.png)).size == (900, 615)
    assert len(chart.points) == 9 and chart.points[-1][0] == AT - timedelta(minutes=30)
    assert (AT, 102.5) not in chart.points
    assert _connectable_now_segment(chart.points, chart.markers) == (
        (AT - timedelta(minutes=30), rows[-1].price), (AT, 102.5)
    )


def test_now_does_not_join_across_gap_or_invalid_timestamp():
    rows = history(last_offset_minutes=30)
    chart = render_price_chart(
        rows, as_of=AT, symbol="BTC", event_markers=True,
        current_observation=(AT, 102.5),
    )
    assert chart.markers
    older_points = chart.points[:-1]  # latest now 60m from the last persisted point
    assert _connectable_now_segment(older_points, chart.markers) is None
    assert _connectable_now_segment(chart.points, []) is None
    assert _connectable_now_segment(chart.points, _reference_markers(
        chart.points, as_of=AT, axis_start=AT-timedelta(hours=24),
        current_observation=(AT+timedelta(minutes=1), 102.5), previous_alert=None,
    )) is None
    same_timestamp = _reference_markers(
        chart.points, as_of=AT, axis_start=AT-timedelta(hours=24),
        current_observation=(chart.points[-1][0], 102.5), previous_alert=None,
    )
    assert _connectable_now_segment(chart.points, same_timestamp) is None
