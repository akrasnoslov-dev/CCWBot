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
from bot.coin_icons import build_coin_icon_html

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
    assert result.png is not None and result.png.startswith(b"\x89PNG\r\n")
    assert result.points[0][0] == AT - timedelta(hours=24)
    assert result.points[-1][0] == AT
    assert [price for _, price in result.points] == [row.price for row in points]


def test_chart_partial_data_is_labeled_and_no_short_day_fabrication():
    short = _observations(duration_hours=14)
    result = prepare_chart_points(short, as_of=AT)
    assert "14h" in result.label
    assert result.label != "Last 24 hours"
    assert render_price_chart(short, as_of=AT, symbol="ETH").png is not None

    # A truthful short chart is better than an unnecessary unavailable message.
    four_hours = _observations(duration_hours=4, step_minutes=30)
    assert render_price_chart(four_hours, as_of=AT, symbol="ETH").png is not None
    too_short = _observations(duration_hours=1, step_minutes=30)
    assert prepare_chart_points(too_short, as_of=AT).png is None

    # A recent point must exist, not merely historical coverage.
    assert prepare_chart_points(_observations(duration_hours=24)[:-4], as_of=AT).png is None


def test_chart_downtime_selects_latest_gap_free_run_without_inventing_prices():
    snapshots = _observations(step_minutes=30)
    # 2.5h downtime in the middle of a day should not suppress 9h of good data.
    gap_start = AT - timedelta(hours=12)
    gap_end = AT - timedelta(hours=9)
    snapshots = [
        row for row in snapshots
        if not gap_start <= row.checked_at <= gap_end
    ]
    result = render_price_chart(snapshots, as_of=AT, symbol="BTC")
    assert result.png is not None
    assert result.points[0][0] == gap_end + timedelta(minutes=30)
    assert result.points[-1][0] == AT
    assert "available history" in result.label
    assert "24 hours" not in result.label
    assert len(result.points) < len(snapshots)
    assert all(
        later[0] - earlier[0] <= timedelta(minutes=45)
        for earlier, later in zip(result.points, result.points[1:], strict=False)
    )


def test_chart_accepts_normal_30_minute_scheduler_jitter_but_rejects_stale():
    # Render starts before the ongoing check's price snapshot is saved.
    snapshots = [
        SimpleNamespace(
            checked_at=AT - timedelta(minutes=32) - timedelta(minutes=30*i),
            price=2000 + i,
        )
        for i in range(48)
    ]
    result = render_price_chart(snapshots, as_of=AT, symbol="ETH")
    assert result.png is not None
    assert result.label == "Last 24 hours"
    assert result.points[-1][0] == AT - timedelta(minutes=32)

    stale = [
        SimpleNamespace(checked_at=row.checked_at - timedelta(minutes=20), price=row.price)
        for row in snapshots
    ]
    assert prepare_chart_points(stale, as_of=AT).png is None


def test_chart_needs_two_hours_of_recent_verified_observations():
    sufficient = _observations(duration_hours=2, step_minutes=30)
    result = render_price_chart(sufficient, as_of=AT, symbol="SOL")
    assert result.png is not None
    assert "2h" in result.label
    assert len(result.points) == 5
    assert prepare_chart_points(sufficient[1:], as_of=AT).png is None


def test_chart_ignores_invalid_price_or_timestamp_without_fabricating_points():
    good = _observations(duration_hours=3, step_minutes=30)
    bad = [
        SimpleNamespace(checked_at=AT, price=float("nan")),
        SimpleNamespace(checked_at=AT, price=0),
        SimpleNamespace(checked_at="invalid", price=2100),
        SimpleNamespace(checked_at=AT + timedelta(hours=1), price=2200),
    ]
    result = render_price_chart(good + bad, as_of=AT, symbol="GRAM")
    assert result.png is not None
    assert result.points == tuple((row.checked_at, float(row.price)) for row in good)



def test_half_hour_persisted_samples_use_true_24h_axis_without_fabrication():
    # Production persists samples approximately every 30m; the edge samples
    # may lie inside the query window despite complete expected coverage.
    points = [
        SimpleNamespace(
            checked_at=AT - timedelta(hours=24) + timedelta(minutes=30*i),
            price=2400 + i * 0.1,
        )
        for i in range(1, 48)
    ]
    result = render_price_chart(points, as_of=AT, symbol="ETH")
    assert result.label == "Last 24 hours"
    assert result.png and result.png.startswith(b"\x89PNG")
    assert result.points[0][0] == AT - timedelta(hours=23, minutes=30)
    assert result.points[-1][0] == AT - timedelta(minutes=30)
    # No synthetic boundary samples were inserted.
    assert len(result.points) == 47


def test_incomplete_24h_coverage_stays_labeled_partial():
    points = [
        SimpleNamespace(
            checked_at=AT - timedelta(hours=23) + timedelta(minutes=30*i),
            price=2400 + i * 0.1,
        )
        for i in range(46)
    ]
    result = prepare_chart_points(points, as_of=AT)
    assert "available history" in result.label
    assert result.label != "Last 24 hours"


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
            "ETH Event Alert — +1.12%\n\n"
            "Price (now): $2,482.58\n"
            "Since previous alert (1h ago): +3.00%\n"
            "3h market move: +1.12%\n\n"
            "Last 24 hours: chart unavailable in text-only view.\n\nSituation:\nVerified.\n\n"
            "Possible action:\nObserve.\n\nNot financial advice."
        ),
        "html_text": (
            "<b>ETH Event Alert — +1.12%</b>\n"
            "Price (now): $2,482.58\n"
            "Since previous alert (1h ago): +3.00%\n"
            "3h market move: +1.12%\n"
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



def test_event_alert_rich_layout_matches_mobile_preview_hierarchy():
    html = alerts._build_event_alert_rich_html(
        headline="BTC Event Alert — -0.25%",
        metric_lines=[
            "Price (now): $81,378.00",
            "Since previous alert (6h ago): -0.40%",
            "3h market move: -0.25%",
        ],
        situation="The move matches the 24-hour direction.",
        related_section_html='<a href="https://example.org">Related source</a>',
        possible_action="Observe the next snapshot.",
    )
    assert f"<h2>{build_coin_icon_html('BTC')} BTC Event Alert — -0.25%</h2>" in html
    assert 'tg-emoji emoji-id=' in html
    assert "<p>💰 <b>Price (now): $81,378.00</b></p>" in html
    assert "<p>🕒 <b>Since previous alert (6h ago): -0.40%</b></p>" in html
    assert "<p>📉 <b>3h market move: -0.25%</b></p>" in html
    assert "<h3>📌 Situation</h3>" in html
    assert "<h3>📰 Related context</h3>" in html
    assert "<h3>🔎 Possible action</h3>" in html
    assert html.endswith("<footer>Not financial advice.</footer>")


def test_rich_recipient_metric_is_replaced_not_duplicated_with_emoji_formatting():
    payload = {
        "plain_text": "SOL Event Alert — -0.19%\nPrice (now): $103.87\n"
        "Since previous alert (1h ago): +3.00%\n3h market move: -0.19%",
        "rich_html": alerts._build_event_alert_rich_html(
            headline="SOL Event Alert — -0.19%",
            metric_lines=[
                "Price (now): $103.87",
                "Since previous alert (1h ago): +3.00%",
                "3h market move: -0.19%",
            ],
            situation="Observed short-term movement.",
            related_section_html=None,
            possible_action="Watch the next observed interval.",
        ),
    }
    prior = SimpleNamespace(
        numeric_context=json.dumps({"current_price": 100}),
        alert_type=alerts.EVENT_ALERT_TYPE,
        sent_at=AT - timedelta(hours=6),
    )
    actual = alerts._event_alert_for_recipient(
        payload, previous_alert=prior, current_price=103.87, as_of=AT,
    )["rich_html"]
    assert "Since previous alert (6h ago): +3.87%" in actual
    assert "Since previous alert (1h ago)" not in actual
    assert actual.count("Since previous alert") == 1
    assert "🕒" in actual
    no_prior = alerts._event_alert_for_recipient(
        payload, previous_alert=None, current_price=103.87, as_of=AT,
    )["rich_html"]
    assert "Since previous alert" not in no_prior


def test_heartbeat_uses_one_rich_message_template_and_styled_html_fallback():
    heartbeat = SimpleNamespace(
        symbol="SOL",
        title="Calm market update",
        message_body="Price remains near the observed range.",
        possible_action="Monitor the next short interval.",
    )
    payload = alerts._build_market_heartbeat_payload(
        heartbeat=heartbeat,
        current_price=103.87,
        change_since_last_message=0.54,
        change_24h=-0.8,
        related_news=[],
    )
    html = payload["rich_html"]
    assert f"<h2>{build_coin_icon_html('SOL')} 📡 SOL Market Heartbeat</h2>" in html
    assert 'tg-emoji emoji-id=' in html
    assert "<p>💰 <b>Price: $103.87</b></p>" in html
    assert "<p>🕒 <b>Since last SOL message: +0.54%</b></p>" in html
    assert "<p>📉 <b>24h change: -0.80%</b></p>" in html
    assert "__CCWBOT_CHART_BLOCK__" in html
    assert "<h3>📌 Situation</h3>" in html
    assert "<h3>🔎 Possible action</h3>" in html
    assert html.endswith("<footer>Not financial advice.</footer>")
    assert "<b>📡 SOL Market Heartbeat</b>" in payload["html_text"]
    assert "Not financial advice." in payload["plain_text"]


@pytest.mark.asyncio
async def test_heartbeat_uses_existing_shared_price_snapshot_chart(monkeypatch):
    calls = {"db": 0}
    class FakeSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
    async def read_snapshots(*args, **kwargs):
        calls["db"] += 1
        return _observations()
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", FakeSession)
    monkeypatch.setattr(alerts, "get_price_snapshots_since", read_snapshots)
    payload = {"rich_html": "__CCWBOT_CHART_BLOCK__"}
    await alerts._prepare_event_alert_chart(payload, symbol="SOL", as_of=AT)
    assert calls["db"] == 1
    assert payload["chart_png"].startswith(b"\x89PNG")
    assert "📈 Last 24 hours" in payload["rich_html"]
    assert "tg://photo?id=chart" in payload["rich_html"]



@pytest.mark.asyncio
async def test_heartbeat_falls_back_to_styled_html_if_rich_adapter_has_no_token():
    bot = SimpleNamespace(send_message=AsyncMock())
    heartbeat = SimpleNamespace(
        symbol="BTC", title="Calm monitoring",
        message_body="No marked change.", possible_action="Watch the next interval.",
    )
    payload = alerts._build_market_heartbeat_payload(
        heartbeat=heartbeat, current_price=100000.0,
        change_since_last_message=None, change_24h=0.5, related_news=[],
    )
    sent, error, _ = await alerts._send_alert_to_recipient_once(
        SimpleNamespace(bot=bot),
        alerts.AlertRecipient(chat_id=123),
        payload,
    )
    assert sent and error is None
    bot.send_message.assert_awaited_once()
    assert "<b>📡 BTC Market Heartbeat</b>" in bot.send_message.await_args.kwargs["text"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Forbidden: bot was blocked by the user", True),
        ("Forbidden: user is deactivated", True),
        ("Forbidden: chat not found", True),
        ("Forbidden: cannot send rich message", False),
    ],
)
async def test_rich_403_preserves_safe_blocked_classification_without_raw_errors(
    monkeypatch, description, expected,
):
    from telegram.error import Forbidden

    from bot.telegram_errors import is_bot_blocked_error

    class FakeResponse:
        def json(self):
            return {"ok": False, "error_code": 403, "description": description}
    class FakeClient:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, **kwargs):
            return FakeResponse()
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    with pytest.raises(Forbidden) as caught:
        await send_rich_event_alert(
            bot_token="test", chat_id=123, rich_html="<p>Hello</p>", chart_png=None,
        )
    assert is_bot_blocked_error(caught.value) is expected
    assert str(caught.value) != description


@pytest.mark.asyncio
async def test_event_dispatch_reuses_confirmed_chart_file_id_across_recipients(monkeypatch):
    """Chart upload happens once, while recipient-specific text remains separate."""
    seen = []

    async def chart(payload, **_kwargs):
        payload["chart_png"] = b"one-chart"
        payload["rich_html"] = "<h2>BTC</h2><img src='tg://photo?id=chart'/>"

    async def rich_send(**kwargs):
        seen.append((kwargs["chart_file_id"], kwargs["chart_png"], kwargs["chat_id"]))
        return "telegram-cached-chart"

    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "_prepare_event_alert_chart", chart)
    monkeypatch.setattr(alerts, "send_rich_event_alert", rich_send)
    monkeypatch.setattr(alerts, "_record_alert_delivery", AsyncMock())
    monkeypatch.setattr(alerts, "_record_alert_delivery_outcome", AsyncMock())
    monkeypatch.setattr(alerts, "_persist_successful_product_alert_state", AsyncMock())
    app = SimpleNamespace(bot=SimpleNamespace(token="fake", send_message=AsyncMock()))
    sent = await alerts._deliver_market_event_alert(
        app, symbol="BTC", event_type=alerts.EVENT_ALERT_TYPE,
        alert_payload={"plain_text": "BTC Event Alert. Not financial advice."},
        market_event_id=None, event_ai_analysis_id=None,
        recipients=[alerts.AlertRecipient(chat_id=111), alerts.AlertRecipient(chat_id=222)],
    )
    assert sent
    assert [(file_id, png) for file_id, png, _ in seen] == [
        (None, b"one-chart"), ("telegram-cached-chart", b"one-chart")
    ]
    app.bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("message_id", [None, False, 0, -1, "17", 1.5])
async def test_rich_success_without_valid_message_identity_is_uncertain(monkeypatch, message_id):
    class FakeResponse:
        def json(self):
            return {"ok": True, "result": {"message_id": message_id,
                                            "rich_message": {"photo": [{"file_id": "id"}]}}}

    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *_args, **_kwargs): return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    with pytest.raises(RichDeliveryUncertain):
        await send_rich_event_alert(
            bot_token="test", chat_id=123, rich_html="<p>Hi</p>", chart_png=b"png"
        )


@pytest.mark.asyncio
async def test_rich_httpx_transport_uncertainty_never_retries_or_falls_back(monkeypatch):
    attempts = []

    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *_args, **_kwargs):
            attempts.append(1)
            raise httpx.ReadTimeout("timeout with private URL")

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    bot = SimpleNamespace(token="private", send_message=AsyncMock())
    result = await alerts._send_alert_to_recipient_with_retry(
        SimpleNamespace(bot=bot), alerts.AlertRecipient(chat_id=123),
        {"rich_html": "<p>Hi</p>", "html_text": "Hi", "plain_text": "Hi"}
    )
    assert not result[0]
    assert isinstance(result[2], RichDeliveryUncertain)
    assert attempts == [1]
    assert "private" not in str(result[2])
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_integrity_error_recovery_does_not_reopen_terminal_delivery(monkeypatch):
    from sqlalchemy.exc import IntegrityError
    from bot.db import alerts as db_alerts

    terminal = SimpleNamespace(status="failed", final_failed_at=AT)
    session = SimpleNamespace(
        add=lambda *_: None,
        commit=AsyncMock(side_effect=IntegrityError("unique", {}, Exception("duplicate"))),
        rollback=AsyncMock(),
    )
    get_existing = AsyncMock(side_effect=[None, terminal])
    monkeypatch.setattr(db_alerts, "get_alert_delivery", get_existing)
    alert, should_send = await db_alerts.reserve_alert_delivery(
        session, user_id=1, symbol="BTC", alert_type="event_alert",
        sent_to_chat_id=2, market_event_id=3, event_ai_analysis_id=4,
        message="safe message",
    )
    assert alert is terminal
    assert should_send is False
    session.rollback.assert_awaited_once()
