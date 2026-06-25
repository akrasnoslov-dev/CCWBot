import pytest

from bot.alerting.market_report import (
    MarketReportValidationError,
    validate_market_report_output,
)


def _valid_report(report_type="daily", **overrides):
    title = "Daily Market Report" if report_type == "daily" else "Weekly Market Report"
    report = {
        "report_type": report_type,
        "title": title,
        "market_pulse": "BTC, ETH, GRAM, and SOL are mixed.",
        "dashboard": [
            "BTC is steady while ETH is slightly softer.",
            "Volume is moderate across tracked assets.",
        ],
        "coin_cards": [
            {"symbol": "BTC", "summary": "BTC is steady.", "watch": "Watch the weekly range."},
            {"symbol": "ETH", "summary": "ETH is steady.", "watch": "Watch ETF flow news."},
            {"symbol": "GRAM", "summary": "GRAM is steady.", "watch": "Watch liquidity."},
            {"symbol": "SOL", "summary": "SOL is steady.", "watch": "Watch network news."},
        ],
        "market_catalysts": ["No clearly relevant fresh news found for tracked coins."],
        "why_it_matters": "The market is mixed, so confirmation matters more than speed.",
        "watch_next": "Watch whether BTC holds its current range before reacting.",
        "week_timeline": [] if report_type == "daily" else ["Midweek: BTC tested its range."],
        "themes": [] if report_type == "daily" else ["BTC led while alt participation was mixed."],
        "next_week_focus": (
            ""
            if report_type == "daily"
            else "Watch whether BTC leadership broadens to ETH and SOL."
        ),
    }
    report.update(overrides)
    return report


def test_daily_structured_report_is_accepted():
    decision = validate_market_report_output(_valid_report("daily"), expected_report_type="daily")

    assert decision.market_pulse == "BTC, ETH, GRAM, and SOL are mixed."
    assert [coin["symbol"] for coin in decision.coin_cards] == ["BTC", "ETH", "GRAM", "SOL"]
    assert decision.week_timeline == []
    assert decision.next_week_focus == ""


def test_weekly_structured_report_requires_weekly_fields():
    decision = validate_market_report_output(_valid_report("weekly"), expected_report_type="weekly")

    assert decision.week_timeline == ["Midweek: BTC tested its range."]
    assert decision.themes == ["BTC led while alt participation was mixed."]
    assert decision.next_week_focus == "Watch whether BTC leadership broadens to ETH and SOL."


def test_weekly_timeline_dict_items_are_normalized_to_strings():
    decision = validate_market_report_output(
        _valid_report(
            "weekly",
            week_timeline=[
                {
                    "day": "Monday",
                    "event": "BTC tested its weekly range.",
                    "summary": "ETH stayed mixed.",
                },
                {
                    "period": "Late week",
                    "text": "SOL cooled while GRAM held steady.",
                },
            ],
            themes=["BTC led while alt participation was mixed."],
        ),
        expected_report_type="weekly",
    )

    assert decision.week_timeline == [
        "Monday: BTC tested its weekly range. ETH stayed mixed.",
        "Late week: SOL cooled while GRAM held steady.",
    ]
    assert decision.themes == ["BTC led while alt participation was mixed."]


def test_weekly_timeline_dict_direct_trading_instruction_is_rejected():
    with pytest.raises(MarketReportValidationError, match="direct trading instruction"):
        validate_market_report_output(
            _valid_report("weekly", week_timeline=[{"day": "Monday", "event": "Buy BTC."}]),
            expected_report_type="weekly",
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("week_timeline", [{"day": "Monday", "summary": {"nested": "value"}}]),
        ("themes", [{"title": "Debug: move=1.2"}]),
    ],
)
def test_weekly_text_lists_reject_complex_or_diagnostic_entries(field, value):
    with pytest.raises(MarketReportValidationError):
        validate_market_report_output(
            _valid_report("weekly", **{field: value}),
            expected_report_type="weekly",
        )


def test_weekly_empty_next_week_focus_is_rejected():
    with pytest.raises(MarketReportValidationError, match="next_week_focus must be non-empty"):
        validate_market_report_output(
            _valid_report("weekly", next_week_focus=""),
            expected_report_type="weekly",
        )


def test_legacy_telegram_message_schema_is_rejected():
    report = _valid_report("daily")
    report["telegram_message"] = "Daily Market Report"

    with pytest.raises(MarketReportValidationError, match="unexpected fields"):
        validate_market_report_output(report, expected_report_type="daily")


def test_legacy_ton_symbol_is_normalized_to_gram():
    report = _valid_report("daily")
    report["coin_cards"][2] = {
        "symbol": "TON",
        "summary": "Legacy TON wording from the LLM.",
        "watch": "Watch liquidity.",
    }

    decision = validate_market_report_output(report, expected_report_type="daily")

    assert decision.coin_cards[2] == {
        "symbol": "GRAM",
        "summary": "Legacy TON wording from the LLM.",
        "watch": "Watch liquidity.",
    }


def test_wrong_coin_card_symbol_is_rejected():
    report = _valid_report("daily")
    report["coin_cards"] = [{"symbol": "USDT", "summary": "USDT is moving.", "watch": "Watch it."}]

    with pytest.raises(MarketReportValidationError, match="symbol is not active"):
        validate_market_report_output(report, expected_report_type="daily")


def test_missing_coin_card_symbol_is_rejected():
    report = _valid_report("daily")
    report["coin_cards"] = report["coin_cards"][:1]

    with pytest.raises(MarketReportValidationError, match="each active symbol exactly once"):
        validate_market_report_output(report, expected_report_type="daily")


def test_duplicate_coin_card_symbol_is_rejected():
    report = _valid_report("daily")
    report["coin_cards"][1]["symbol"] = "BTC"

    with pytest.raises(MarketReportValidationError, match="duplicated"):
        validate_market_report_output(report, expected_report_type="daily")


@pytest.mark.parametrize(
    "field,value",
    [
        ("market_pulse", "You should buy now."),
        ("watch_next", "Sell now."),
        ("why_it_matters", "Short immediately."),
        ("next_week_focus", "Go long."),
        ("watch_next", "Buy BTC today."),
        ("watch_next", "Sell SOL into strength."),
        ("watch_next", "Increase ETH exposure."),
        ("watch_next", "Reduce BTC position."),
        ("watch_next", "Increase exposure to ETH."),
        ("watch_next", "Exit SOL position."),
    ],
)
def test_direct_trading_wording_is_rejected(field, value):
    report = _valid_report("weekly", **{field: value})

    with pytest.raises(MarketReportValidationError, match="direct trading instruction"):
        validate_market_report_output(report, expected_report_type="weekly")


@pytest.mark.parametrize(
    "field,value",
    [
        ("market_pulse", "There was an increase in ETH volume during the session."),
        ("dashboard", ["A decrease in BTC dominance coincided with mixed altcoin breadth."]),
        ("market_catalysts", ["Increase in SOL network activity supported relative interest."]),
        ("why_it_matters", "The decrease in Bitcoin volatility may affect market breadth."),
        ("watch_next", "Watch whether the increase in ETH volume continues."),
    ],
)
def test_market_observation_wording_is_accepted(field, value):
    report = _valid_report("daily", **{field: value})

    decision = validate_market_report_output(report, expected_report_type="daily")

    assert decision.report_type == "daily"


def test_validation_errors_do_not_contain_financial_advice_messages():
    report = _valid_report("daily")
    report["coin_cards"] = [{"symbol": "XRP", "summary": "XRP is moving.", "watch": "Watch it."}]

    with pytest.raises(MarketReportValidationError) as exc_info:
        validate_market_report_output(report, expected_report_type="daily")

    message = str(exc_info.value)
    assert "personalized financial advice detected" not in message
    assert "direct financial advice" not in message
