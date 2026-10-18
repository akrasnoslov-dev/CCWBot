"""Rich Daily/Weekly Report UX, trusted chart, and no-duplicate delivery contracts."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.error import BadRequest

import bot.reports as reports
from bot.alerting.market_report_rich import (
    format_html_market_report,
    format_rich_market_report,
    market_report_change_chart,
)
from bot.handlers import transient


def _sample_text(report_type="daily"):
    if report_type == "daily":
        return (
            "📊 Daily Market Report\n\n"
            "Market pulse:\nBTC outperformed.\n\n"
            "Tracked assets:\n• BTC: $80,000, 24h +1.2%\n"
            "• ETH: $2,400, 24h -0.7%\n\n"
            "Coin-specific news:\n"
            "• News title (Source) https://example.org/news?x=1&y=2\n\n"
            "What to watch next:\nWatch the next market snapshot.\n\n"
            "Not financial advice."
        )
    return (
        "📊 Weekly Market Report\n\n"
        "Week in one line:\nBTC outperformed.\n\n"
        "Weekly scoreboard:\n• BTC: $80,000, 7d +1.8%\n"
        "• SOL: $104, 7d -1.2%\n\n"
        "Market breadth:\n• Mixed performance.\n\n"
        "Top catalysts of the week:\nNo clearly relevant fresh news.\n\n"
        "Next week in focus:\nMonitor confirmed movement.\n\n"
        "Not financial advice."
    )


def _input_json(report_type):
    return json.dumps({
        "report_type": report_type,
        "coins": [
            {"symbol": "BTC", "change_24h_percent": 1.2, "change_7d_percent": 1.8},
            {"symbol": "ETH", "change_24h_percent": -0.7, "change_7d_percent": None},
            {"symbol": "SOL", "change_24h_percent": -0.4, "change_7d_percent": -1.2},
            {"symbol": "GRAM", "change_24h_percent": 0.1, "change_7d_percent": 0.4},
        ],
    })


@pytest.mark.parametrize("report_type", ["daily", "weekly"])
def test_rich_report_retains_sections_custom_coin_icons_and_single_chart(report_type):
    plain = _sample_text(report_type)
    html = format_rich_market_report(plain, report_type=report_type, chart_available=True)
    assert f"<h2>📊 {report_type.title()} Market Report</h2>" in html
    assert html.count('<img src="tg://photo?id=chart"/>') == 1
    assert '<tg-emoji emoji-id="5220072735815802195">🖕</tg-emoji>' in html
    assert '<footer>Not financial advice.</footer>' in html
    assert "BTC outperformed." in html
    if report_type == "daily":
        assert "<h3>🌍 Market pulse</h3>" in html
        assert '<a href="https://example.org/news?x=1&amp;y=2">' in html
    else:
        assert "<h3>📊 Market breadth</h3>" in html
        assert "<h3>🗓️ Week timeline</h3>" not in html


@pytest.mark.parametrize("report_type", ["daily", "weekly"])
def test_chart_uses_only_cached_verified_changes(report_type):
    png = market_report_change_chart(_input_json(report_type), report_type=report_type)
    assert isinstance(png, bytes) and png.startswith(b"\x89PNG")
    assert market_report_change_chart(
        '{"report_type":"daily","coins":[{"symbol":"BTC","change_24h_percent":null}]}',
        report_type="daily",
    ) is None
    assert market_report_change_chart(_input_json("daily"), report_type="weekly") is None
    assert market_report_change_chart("not json", report_type=report_type) is None


def test_missing_chart_and_unsafe_model_text_are_escaped():
    plain = _sample_text().replace(
        "BTC outperformed.", "<script>alert('bad')</script>"
    )
    html = format_rich_market_report(plain, report_type="daily", chart_available=False)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Chart unavailable: verified changes missing." in html
    assert "<img " not in html
    fallback = format_html_market_report(plain, report_type="daily")
    assert "<b>🌍 Market pulse</b>" in fallback
    assert "<script>" not in fallback


@pytest.mark.asyncio
async def test_native_rich_report_is_one_send_and_has_close_tracking(monkeypatch):
    report = {
        "telegram_message": _sample_text(),
        "raw_input_json": _input_json("daily"),
    }
    sender = AsyncMock()
    monkeypatch.setattr(reports, "get_or_generate_report", AsyncMock(return_value=report))
    monkeypatch.setattr(reports, "_is_report_rate_limited", lambda *_: False)
    monkeypatch.setattr(reports, "send_rich_event_alert", sender)
    target = SimpleNamespace(
        chat_id=222, get_bot=lambda: SimpleNamespace(token="unit-test"),
        reply_text=AsyncMock(),
    )

    await reports.send_daily_report_message(target)

    sender.assert_awaited_once()
    kw = sender.await_args.kwargs
    assert kw["chat_id"] == 222
    assert kw["bot_token"] == "unit-test"
    assert kw["chart_png"].startswith(b"\x89PNG")
    assert "<h3>📈 Verified 24h coin performance</h3>" in kw["rich_html"]
    target.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_definite_rich_rejection_falls_back_once_to_html(monkeypatch):
    monkeypatch.setattr(
        reports, "get_or_generate_report",
        AsyncMock(return_value={
            "telegram_message": _sample_text("weekly"),
            "raw_input_json": _input_json("weekly"),
        }),
    )
    monkeypatch.setattr(reports, "_is_report_rate_limited", lambda *_: False)
    monkeypatch.setattr(
        reports, "send_rich_event_alert",
        AsyncMock(side_effect=BadRequest("unsupported rich")),
    )
    target = SimpleNamespace(
        chat_id=222, get_bot=lambda: SimpleNamespace(token="unit-test"),
        reply_text=AsyncMock(),
    )

    await reports.send_weekly_report_message(target)

    target.reply_text.assert_awaited_once()
    assert "<b>📊 Weekly Market Report</b>" in target.reply_text.await_args.args[0]
    assert target.reply_text.await_args.kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_uncertain_rich_response_never_sends_duplicate_fallback(monkeypatch):
    from bot.alerting.rich_delivery import RichDeliveryUncertain

    monkeypatch.setattr(
        reports, "get_or_generate_report",
        AsyncMock(return_value={"telegram_message": _sample_text()}),
    )
    monkeypatch.setattr(reports, "_is_report_rate_limited", lambda *_: False)
    monkeypatch.setattr(
        reports, "send_rich_event_alert",
        AsyncMock(side_effect=RichDeliveryUncertain("ack unknown")),
    )
    target = SimpleNamespace(
        chat_id=222, get_bot=lambda: SimpleNamespace(token="unit-test"),
        reply_text=AsyncMock(),
    )
    await reports.send_daily_report_message(target)
    target.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_manual_rich_report_close_and_next_command_cleanup_are_preserved():
    key = (556670, 12312)
    gen = 9941
    transient.sessions._sessions[key] = (gen, set())
    token = transient._active.set((key, gen, asyncio.current_task()))
    try:
        markup = transient.rich_reply_markup(key[0])
        assert markup["inline_keyboard"][0][0]["callback_data"] == "transient:close"
        transient.register_rich_reply(key[0], 7743)
        assert transient.sessions.token_for(*key, 7743) == gen
        assert transient.rich_reply_markup(12) is None
    finally:
        transient._active.reset(token)
        transient.sessions._sessions.pop(key, None)
        transient.sessions._origins.pop(key, None)



def test_rich_legacy_cached_weekly_report_is_compact_without_mutating_cache():
    from bot.alerting.market_report_rich import compact_report_for_display

    raw = (
        "📊 Weekly Market Report\n\n"
        "Week in one line:\nMarket slipped over the week.\n\n"
        "Weekly scoreboard:\n"
        "• BTC: $80,000, 7d -1.7%, 24h +0.0%, ▆▆▇▅▇▆▄▂▄▄▃▃ mid weekly range\n"
        "• ETH: $2,400, 7d -3.7%, 24h +0.4%, ▆▆▄▁▄▄ mid weekly range\n\n"
        "Market breadth:\n• 0/4 assets positive.\n\n"
        "Themes of the week:\n• BTC declined 1.7%.\n"
        "• ETH dropped 3.7%.\n\n"
        "Week timeline:\n• BTC opened at $83,000 and now near $80,000.\n\n"
        "Coin-specific recap:\n• BTC fell 1.7% in the week.\n\n"
        "Top catalysts of the week:\n"
        "• BTC: Verified BTC story (Source) https://example.org/btc\n"
        "• ETH: Same report (Source) https://example.org/btc\n\n"
        "Next week in focus:\nWatch weekly ranges.\n\n"
        "Not financial advice."
    )
    result = compact_report_for_display(raw, report_type="weekly")
    assert result.count("-1.7%") == 1
    assert result.count("-3.7%") == 1
    assert "▆▆" not in result
    assert "24h " not in result
    assert "Themes of the week:" not in result
    assert "Week timeline:" not in result
    assert "Coin-specific recap:" not in result
    assert result.count("https://example.org/btc") == 1
    assert raw.startswith("📊 Weekly Market Report")


def test_weekly_chart_includes_normalized_mini_lines_only_if_provider_supplied():
    from io import BytesIO

    from bot.alerting.market_report_rich import market_report_change_chart
    from PIL import Image

    with_trends = _input_json("weekly")
    without_trends = json.loads(with_trends)
    for item in without_trends["coins"]:
        if item["symbol"] == "BTC":
            item["sparkline_7d"] = "▁▂▃▄▅▆▇█"
    chart = market_report_change_chart(
        json.dumps(without_trends), report_type="weekly",
    )
    assert chart is not None
    image = Image.open(BytesIO(chart))
    assert image.size == (1040, 610)
    # Cached data is unchanged; only a real normalized series draws a mini-line.
    without_trends["coins"][0]["sparkline_7d"] = ""
    plain = market_report_change_chart(
        json.dumps(without_trends), report_type="weekly",
    )
    assert plain is not None and chart != plain


@pytest.mark.parametrize(
    ("report_type", "expected_size"),
    [("daily", (1040, 510)), ("weekly", (1040, 610))],
)
def test_telegram_infographic_size_and_missing_values(report_type, expected_size):
    from io import BytesIO

    from PIL import Image

    raw = _input_json(report_type)
    image = Image.open(BytesIO(market_report_change_chart(raw, report_type=report_type)))
    assert image.size == expected_size
    assert image.mode == "RGB"
    # The thumbnail matches the inline Telegram width used for visual review.
    thumbnail = image.resize((360, round(360 * image.height / image.width)))
    assert thumbnail.width == 360

    missing = {
        "report_type": report_type,
        "coins": [
            {"symbol": "BTC", "change_24h_percent": None, "change_7d_percent": None},
            {"symbol": "ETH", "change_24h_percent": "nan", "change_7d_percent": "inf"},
        ],
    }
    assert market_report_change_chart(json.dumps(missing), report_type=report_type) is None


def test_daily_bars_use_real_signs_not_missing_as_zero():
    from io import BytesIO

    from PIL import Image

    raw = json.dumps({
        "report_type": "daily",
        "coins": [
            {"symbol": "BTC", "change_24h_percent": 2.0},
            {"symbol": "ETH", "change_24h_percent": -2.0},
            {"symbol": "GRAM", "change_24h_percent": None},
            {"symbol": "SOL", "change_24h_percent": 0.0},
        ],
    })
    img = Image.open(BytesIO(market_report_change_chart(raw, report_type="daily")))
    assert img.getpixel((680, 155)) == (59, 211, 179)  # verified positive
    assert img.getpixel((450, 227)) == (255, 136, 135)  # verified negative
    assert img.getpixel((680, 299)) != (59, 211, 179)  # missing is not zero
    assert img.getpixel((680, 299)) != (255, 136, 135)


def test_weekly_source_path_and_range_are_strict_and_never_inferred():
    from bot.alerting.market_report_rich import _chart_source_rows, _range_label, _source_path

    assert _source_path("▁▂▃▄▅▆▇█") == list(range(8))
    assert _source_path("▁▂x▄") == []
    assert _source_path("▁") == []
    assert _source_path("▁" * 13) == []
    assert _range_label(0.1) == "NEAR WEEKLY LOW"
    assert _range_label(0.5) == "MID-WEEK RANGE"
    assert _range_label(0.9) == "NEAR WEEKLY HIGH"
    assert _range_label(None) is None
    assert _range_label("nan") is None
    assert _range_label(1.25) is None
    rows = _chart_source_rows([
        {"symbol": "BTC", "change_7d_percent": -3.14, "sparkline_7d": "▁▂"},
        {"symbol": "BTC", "change_7d_percent": 99, "sparkline_7d": "█▁"},
        {"symbol": "ETH", "change_7d_percent": None, "sparkline_7d": "▁█"},
    ], "7d")
    assert rows[0][0:2] == ("BTC", -3.14)
    assert rows[0][2]["sparkline_7d"] == "▁▂"
    assert rows[1][1] is None


def test_weekly_only_source_glyphs_change_drawn_path():
    from io import BytesIO

    from PIL import Image

    source = {
        "report_type": "weekly",
        "coins": [
            {"symbol": "BTC", "change_7d_percent": -2.4, "range_position": None},
        ],
    }
    no_path = market_report_change_chart(json.dumps(source), report_type="weekly")
    source["coins"][0]["sparkline_7d"] = "▁▂▃▄▅▆▇█"
    with_path = market_report_change_chart(json.dumps(source), report_type="weekly")
    assert no_path != with_path
    assert Image.open(BytesIO(with_path)).size == (1040, 610)
    source["coins"][0]["sparkline_7d"] = "invalid series"
    assert market_report_change_chart(json.dumps(source), report_type="weekly") == no_path
