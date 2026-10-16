"""Event Alert UX, chart evidence and single-send fallback contracts."""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from telegram.error import BadRequest

from bot import alerts
from bot.alerting.event_chart import prepare_chart_points, render_price_chart
from bot.alerting.rich_delivery import RichDeliveryUncertain, send_rich_event_alert

AT = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)


def _observations(*, duration_hours=24, step_minutes=15):
    count = int(duration_hours * 60 / step_minutes)
    return [
        SimpleNamespace(
            checked_at=AT - timedelta(hours=duration_hours) + timedelta(minutes=i * step_minutes),
            price=2500 + i / 5 + 9 * ((i % 13) / 13),
        )
        for i in range(count + 1)
    ]


def test_chart_full_day_uses_observed_timestamps_and_png():
    points = _observations()
    result = render_price_chart(points, as_of=AT, symbol="ETH")
    assert result.label == "Last 24 hours"
    assert result.png is not None and result.png.startswith(b"\\x89PNG\\r\\n")
    assert result.points[0][0] == AT - timedelta(hours=24)
    assert result.points[-1][0] == AT
    assert [price for _, price in result.points] == [row.price for row in points]


def test_chart_partial_data_is_labeled_and_no_short_day_fabrication():
    short = _observations(duration_hours=14)
    result = prepare_chart_points(short, as_of=AT)
    assert "14h" in result.label
    assert result.label != "Last 24 hours"
    assert render_price_chart(short, as_of=AT, symbol="ETH").png is not None
    too_short = _observations(duration_hours=4)
    assert prepare_chart_points(too_short, as_of=AT).png is None
    assert prepare_chart_points(_observations(duration_hours=24)[:-4], as_of=AT).png is None


def test_metric_labels_correct_actual_windows_and_notification_type():
    metrics = alerts._event_alert_market_context_lines(
        symbol="ETH", price=2482.58, change_since_message=1.4,
        last_message_at=AT - timedelta(hours=6, minutes=29),
        last_message_price=2448.30, last_message_type="event_alert",
        current_at=AT, analysed_window_minutes=180, analysed_window_change=1.12,
    )
    assert metrics == [
        "Price (now): $2,482.58",
        "Since previous alert (6h 29m ago): +1.40%",
        "3h market move: +1.12%",
    ]
    metric_heartbeat = alerts._event_alert_market_context_lines(
        symbol="ETH", price=2482.58, change_since_message=1.4,
        last_message_at=AT - timedelta(hours=3), last_message_price=2448.30,
        last_message_type="market_heartbeat",
        current_at=AT, analysed_window_minutes=60, analysed_window_change=1.12,
    )
    assert "Market Heartbeat" in metric_heartbeat[1]
    assert metric_heartbeat[-1] == "1h market move: +1.12%"


def test_recipient_last_delivery_replaces_shared_global_metric_in_all_formats():
    shared = {
        "plain_text": (
            "ETH Event Alert — +1.12%\\n\\n"
            "Price (now): $2,482.58\\n"
            "Since previous alert (1h ago): +3.00%\\n"
            "3h market move: +1.12%\\n\\n"
            "Last 24 hours: chart unavailable in text-only view.\\n\\nSituation:\\nVerified.\\n\\n"
            "Possible action:\\nObserve.\\n\\nNot financial advice."
        ),
        "html_text": (
            "<b>ETH Event Alert — +1.12%</b>\\n"
            "Price (now): $2,482.58\\n"
            "Since previous alert (1h ago): +3.00%\\n"
            "3h market move: +1.12%\\n"
        ),
        "rich_html": (
            "<h2>ETH Event Alert — +1.12%</h2><p>Price (now): $2,482.58</p>"
            "<p>Since previous alert (1h ago): +3.00%</p><p>3h market move: +1.12%</p>"
            "<h3>Situation</h3><p>Verified.</p><h3>Possible action</h3><p>Observe.</p>"
            "<footer>Not financial advice.</footer>"
        ),
    }
    prior = SimpleNamespace(
        numeric_context=json.dumps({"current_price": 2400}),
        alert_type=alerts.EVENT_ALERT_TYPE,
        sent_at=AT - timedelta(hours=6, minutes=29),
    )
    result = alerts._event_alert_for_recipient(
        shared, previous_alert=prior, current_price=2482.58, as_of=AT,
    )
    for key in ("plain_text", "html_text", "rich_html"):
        assert "Since previous alert (6h 29m ago): +3.44%" in result[key]
        assert "1h ago" not in result[key]
        assert "Price (now)" in result[key]
        assert (
            result[key].index("Price (now)")
            < result[key].index("Since previous alert")
            < result[key].index("3h market move")
        )
    no_reference = alerts._event_alert_for_recipient(
        shared, previous_alert=None, current_price=2482.58, as_of=AT,
    )
    assert "Since previous" not in no_reference["plain_text"]
    assert "Since previous" not in no_reference["rich_html"]
    assert "Situation" in no_reference["plain_text"]


def test_rich_sections_order_links_and_disclaimer():
    html = alerts._build_event_alert_rich_html(
        headline="ETH Event Alert — +1.12%",
        metric_lines=["Price (now): $2,482.58", "3h market move: +1.12%"],
        situation="Verified move.",
        related_section_html='<a href="https://example.org/a">Relevant news</a>',
        possible_action="Watch for slowing in the next snapshot.",
    )
    ordered = [
        "ETH Event Alert", "Price (now):", "3h market move:",
        "__CCWBOT_CHART_BLOCK__", "Situation", "Related context",
        "Possible action", "Not financial advice.",
    ]
    locations = [html.index(label) for label in ordered]
    assert locations == sorted(locations)
    assert '<a href="https://example.org/a">' in html
    assert "<h2>" in html
    assert "<footer>Not financial advice.</footer>" in html


@pytest.mark.asyncio
async def test_chart_prepared_once_and_shared_not_in_recipient_loop(monkeypatch):
    calls = {"db": 0, "render": 0}
    class FakeSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
    async def query(*args, **kwargs):
        calls["db"] += 1
        return _observations()
    def render(*args, **kwargs):
        calls["render"] += 1
        return SimpleNamespace(label="Last 24 hours", png=b"png")
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", FakeSession)
    monkeypatch.setattr(alerts, "get_price_snapshots_since", query)
    monkeypatch.setattr(alerts, "render_price_chart", render)
    payload = {
        "rich_html": "<h2>Alert</h2>__CCWBOT_CHART_BLOCK__"
        "<footer>Not financial advice.</footer>",
    }
    await alerts._prepare_event_alert_chart(payload, symbol="ETH", as_of=AT)
    assert calls == {"db": 1, "render": 1}
    assert payload["chart_png"] == b"png"
    assert '<img src="tg://photo?id=chart"/>' in payload["rich_html"]


@pytest.mark.asyncio
async def test_rich_confirmed_bad_request_falls_back_once(monkeypatch):
    bot = SimpleNamespace(token="fake", send_message=AsyncMock())
    app = SimpleNamespace(bot=bot)
    async def rejected(**kwargs):
        raise BadRequest("invalid rich formatting")
    monkeypatch.setattr(alerts, "send_rich_event_alert", rejected)
    result = await alerts._send_alert_to_recipient_once(
        app, alerts.AlertRecipient(chat_id=123),
        {"rich_html": "<h2>A</h2>", "html_text": "<b>A</b>", "plain_text": "A"},
    )
    assert result[0] is True
    bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_rich_ambiguous_error_never_falls_back_or_retries(monkeypatch):
    bot = SimpleNamespace(token="fake", send_message=AsyncMock())
    app = SimpleNamespace(bot=bot)
    sends = []
    async def unknown(**kwargs):
        sends.append(1)
        raise RichDeliveryUncertain("Rich delivery acknowledgement unknown")
    monkeypatch.setattr(alerts, "send_rich_event_alert", unknown)
    result = await alerts._send_alert_to_recipient_with_retry(
        app, alerts.AlertRecipient(chat_id=123),
        {"rich_html": "<h2>A</h2>", "html_text": "<b>A</b>", "plain_text": "A"},
    )
    assert result[0] is False
    assert len(sends) == 1
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_transport_reuses_file_id_and_handles_valid_response(monkeypatch):
    requests = []
    class FakeResponse:
        def json(self):
            return {"ok": True, "result": {
                "message_id": 10, "rich_message": {
                    "blocks": [{"type": "photo", "photo": [{"file_id": "cached-ID"}]}]
                },
            }}
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            assert url.endswith("/sendRichMessage")
            requests.append(kwargs)
            return FakeResponse()
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    for file_id in (None, "cached-ID"):
        returned = await send_rich_event_alert(
            bot_token="test", chat_id=123,
            rich_html='<h3>Last 24 hours</h3><img src="tg://photo?id=chart"/>',
            chart_png=b"data", chart_file_id=file_id,
        )
        assert returned == "cached-ID"
    assert requests[0]["files"]["chart"][1] == b"data"
    assert requests[1]["files"] is None
    reused = json.loads(requests[1]["data"]["rich_message"])["media"][0]
    assert reused["media"]["media"] == "cached-ID"
