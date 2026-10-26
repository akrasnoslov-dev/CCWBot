"""Event Alert PNG reference-point and shared-delivery regressions."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from bot import alerts
from bot.alerting.event_chart import render_price_chart

AT = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)


def samples(hours=24, step=30, base=1000.0):
    return [
        SimpleNamespace(
            checked_at=AT - timedelta(hours=hours) + timedelta(minutes=i * step),
            price=base + i * 0.25,
        )
        for i in range(hours * 60 // step + 1)
    ]


def event_chart(rows=None, *, current=(AT, 1012.4), previous=None, symbol="BTC"):
    return render_price_chart(
        samples() if rows is None else rows,
        as_of=AT,
        symbol=symbol,
        event_markers=True,
        current_observation=current,
        previous_alert=previous,
    )


def marker(chart, label):
    return next(m for m in chart.markers if m.label == label)


def test_four_reliable_markers_and_exact_observation_values():
    rows = samples()
    chart = event_chart(rows, current=(AT, 1234.5),
                        previous=(AT - timedelta(hours=2), 998.7))
    assert chart.png and Image.open(BytesIO(chart.png)).size == (900, 615)
    assert [m.label for m in chart.markers] == ["NOW", "PREVIOUS ALERT", "−3H", "−24H"]
    assert all(m.plotted for m in chart.markers)
    assert marker(chart, "NOW").price == 1234.5
    assert marker(chart, "PREVIOUS ALERT").price == 998.7
    assert marker(chart, "−3H").timestamp == AT - timedelta(hours=3)
    assert marker(chart, "−3H").price == rows[-7].price
    assert marker(chart, "−24H").timestamp == AT - timedelta(hours=24)
    assert marker(chart, "−24H").price == rows[0].price


def test_missing_references_are_explicitly_unavailable():
    chart = event_chart(samples(hours=4))
    assert not marker(chart, "PREVIOUS ALERT").plotted
    assert marker(chart, "PREVIOUS ALERT").reason == "no previous market event"
    assert not marker(chart, "−24H").plotted
    assert "no sample" in marker(chart, "−24H").reason
    assert marker(chart, "−3H").plotted


def test_previous_event_outside_visible_window_never_pinned_to_boundary():
    prior_at = AT - timedelta(hours=30)
    chart = event_chart(previous=(prior_at, 900.0))
    prior = marker(chart, "PREVIOUS ALERT")
    assert prior.timestamp == prior_at
    assert not prior.plotted and prior.label_box is None
    assert prior.reason == "outside visible window"


def test_current_event_newer_and_different_from_latest_persisted_snapshot():
    rows = samples()[:-1]
    chart = event_chart(rows, current=(AT, 1400.0))
    assert chart.points[-1][0] == AT - timedelta(minutes=30)
    assert marker(chart, "NOW").timestamp == AT
    assert marker(chart, "NOW").price == 1400.0
    assert (AT, 1400.0) not in chart.points


def test_current_missing_cannot_fall_back_to_history():
    chart = event_chart(current=None)
    now = marker(chart, "NOW")
    assert not now.plotted and now.price is None
    assert now.reason == "current observation unavailable"


def test_three_hour_reference_is_not_a_longer_analysed_window():
    rows = samples(hours=12)
    chart = event_chart(rows)
    assert marker(chart, "−3H").timestamp == AT - timedelta(hours=3)
    assert marker(chart, "−3H").price == rows[-7].price
    assert chart.points[0][0] == AT - timedelta(hours=12)


def test_nearest_sample_retains_actual_utc_timestamp_with_tolerance():
    rows = [SimpleNamespace(checked_at=row.checked_at + timedelta(minutes=7), price=row.price)
            for row in samples()[:-1]]
    chart = event_chart(rows)
    assert marker(chart, "−3H").timestamp == AT - timedelta(hours=3) + timedelta(minutes=7)
    assert marker(chart, "−24H").timestamp == AT - timedelta(hours=24) + timedelta(minutes=7)


def test_unreliable_three_hour_gap_does_not_create_reference():
    rows = [r for r in samples()
            if abs((r.checked_at - (AT - timedelta(hours=3))).total_seconds()) > 50 * 60]
    chart = event_chart(rows)
    assert not marker(chart, "−3H").plotted
    assert "20m" in marker(chart, "−3H").reason


def test_discontinuous_history_remains_gap_free_and_partial():
    rows = [r for r in samples()
            if not AT - timedelta(hours=9) <= r.checked_at <= AT - timedelta(hours=6)]
    chart = event_chart(rows)
    assert chart.points[0][0] == AT - timedelta(hours=5, minutes=30)
    assert all(b[0] - a[0] <= timedelta(minutes=45)
               for a, b in zip(chart.points, chart.points[1:], strict=False))
    assert "available history" in chart.label
    assert not marker(chart, "−24H").plotted


def test_partial_history_missing_old_alert_has_no_false_markers():
    chart = event_chart(samples(hours=5), previous=(AT - timedelta(hours=10), 999.0),
                        symbol="GRAM")
    assert "available history" in chart.label
    assert not marker(chart, "−24H").plotted
    assert not marker(chart, "PREVIOUS ALERT").plotted
    assert marker(chart, "NOW").plotted


def test_marker_labels_do_not_overlap_and_are_clamped_at_boundaries():
    chart = event_chart(previous=(AT - timedelta(minutes=1), 1002.0))
    boxes = [m.label_box for m in chart.markers if m.label_box is not None]
    assert all(118 <= b[0] < b[2] <= 865 and 60 <= b[1] < b[3] <= 165 for b in boxes)
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert not (a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3])


def test_missing_previous_event_price_keeps_time_but_omits_price_pin():
    chart = event_chart(previous=(AT - timedelta(hours=2), None))
    prior = marker(chart, "PREVIOUS ALERT")
    assert prior.timestamp == AT - timedelta(hours=2)
    assert prior.price is None and not prior.plotted
    assert prior.reason == "price unavailable"


def test_market_heartbeat_still_uses_original_png_and_no_markers():
    rows = samples()
    baseline = render_price_chart(rows, as_of=AT, symbol="SOL")
    explicit = render_price_chart(
        rows, as_of=AT, symbol="SOL", event_markers=False,
        current_observation=(AT, 99999), previous_alert=(AT, 100),
    )
    assert baseline.png == explicit.png
    assert Image.open(BytesIO(baseline.png)).size == (900, 360)
    assert baseline.markers == ()


@pytest.mark.asyncio
async def test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(monkeypatch):
    visits = {"sessions": 0, "snapshots": 0, "previous": 0}
    class Session:
        async def __aenter__(self):
            visits["sessions"] += 1
            return self
        async def __aexit__(self, *args):
            pass

    async def get_snapshots(*args, **kwargs):
        visits["snapshots"] += 1
        return samples()

    async def get_previous(*args, **kwargs):
        visits["previous"] += 1
        assert kwargs["symbol"] == "BTC"
        assert kwargs["alert_type"] == alerts.EVENT_ALERT_TYPE
        assert kwargs["current_market_event_id"] == 17
        return SimpleNamespace(detected_at=AT - timedelta(hours=2), price=1008.0)

    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", Session)
    monkeypatch.setattr(alerts, "get_price_snapshots_since", get_snapshots)
    monkeypatch.setattr(alerts, "get_previous_market_event_for_chart", get_previous)
    payload = {"rich_html": "__CCWBOT_CHART_BLOCK__"}
    await alerts._prepare_event_alert_chart(
        payload, symbol="BTC", as_of=AT, event_markers=True,
        current_price=1012.0, market_event_id=17,
    )
    assert visits == {"sessions": 1, "snapshots": 1, "previous": 1}
    assert payload["chart_png"].startswith(bytes((137, 80, 78, 71)))
    assert 'tg://photo?id=chart' in payload["rich_html"]


@pytest.mark.asyncio
async def test_heartbeat_does_not_query_previous_event(monkeypatch):
    class Session:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass

    async def get_snapshots(*args, **kwargs):
        return samples()

    async def forbidden(*args, **kwargs):
        pytest.fail("Heartbeat cannot read previous market event")

    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", Session)
    monkeypatch.setattr(alerts, "get_price_snapshots_since", get_snapshots)
    monkeypatch.setattr(alerts, "get_previous_market_event_for_chart", forbidden)
    payload = {"rich_html": "__CCWBOT_CHART_BLOCK__"}
    await alerts._prepare_event_alert_chart(payload, symbol="SOL", as_of=AT)
    assert payload["chart_png"].startswith(bytes((137, 80, 78, 71)))
