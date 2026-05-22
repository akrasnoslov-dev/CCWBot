import pytest

from bot.alerting.market_report import (
    MarketReportValidationError,
    validate_market_report_output,
)


def _valid_report(report_type="daily", *, telegram_message="Daily Market Report"):
    title = "Daily Market Report" if report_type == "daily" else "Weekly Market Report"
    return {
        "report_type": report_type,
        "title": title,
        "market_overview": "BTC, ETH, TON, and SOL are mixed.",
        "coin_summaries": [
            {"symbol": "BTC", "summary": "BTC is steady."},
            {"symbol": "ETH", "summary": "ETH is steady."},
            {"symbol": "TON", "summary": "TON is steady."},
            {"symbol": "SOL", "summary": "SOL is steady."},
        ],
        "news_context": "No major market-wide news selected.",
        "possible_action": "Monitor conditions and avoid rushing decisions.",
        "telegram_message": telegram_message,
    }


def test_daily_report_without_disclaimer_is_accepted_after_append():
    decision = validate_market_report_output(
        _valid_report("daily", telegram_message="Daily Market Report\n\nCoins:\nBTC ETH TON SOL"),
        expected_report_type="daily",
    )

    assert decision.telegram_message.endswith("Not financial advice.")


def test_weekly_report_without_disclaimer_is_accepted_after_append():
    decision = validate_market_report_output(
        _valid_report("weekly", telegram_message="Weekly Market Report\n\nCoins:\nBTC ETH TON SOL"),
        expected_report_type="weekly",
    )

    assert decision.telegram_message.endswith("Not financial advice.")


def test_daily_report_advice_like_wording_is_accepted():
    decision = validate_market_report_output(
        _valid_report(
            "daily",
            telegram_message="Daily Market Report\n\nAdjust your strategy as needed.",
        ),
        expected_report_type="daily",
    )

    assert "Adjust your strategy" in decision.telegram_message


def test_weekly_report_advice_like_wording_is_accepted():
    decision = validate_market_report_output(
        _valid_report(
            "weekly",
            telegram_message=(
                "Weekly Market Report\n\nReview your portfolio and adjust your strategy."
            ),
        ),
        expected_report_type="weekly",
    )

    assert "your portfolio" in decision.telegram_message


def test_empty_telegram_message_is_rejected():
    with pytest.raises(MarketReportValidationError, match="telegram_message must be non-empty"):
        validate_market_report_output(
            _valid_report("daily", telegram_message=""),
            expected_report_type="daily",
        )


@pytest.mark.parametrize(
    "telegram_message",
    [
        "Daily Market Report\n\nYou should buy now.\n\nNot financial advice.",
        "Daily Market Report\n\nSell now.\n\nNot financial advice.",
        "Daily Market Report\n\nShort immediately.\n\nNot financial advice.",
        "Daily Market Report\n\nGo long.\n\nNot financial advice.",
    ],
)
def test_direct_trading_wording_is_accepted(telegram_message):
    decision = validate_market_report_output(
        _valid_report("daily", telegram_message=telegram_message),
        expected_report_type="daily",
    )

    assert decision.telegram_message == telegram_message


def test_wrong_symbol_is_rejected():
    report = _valid_report("daily")
    report["coin_summaries"] = [{"symbol": "XRP", "summary": "XRP is moving."}]

    with pytest.raises(MarketReportValidationError, match="symbol is not active"):
        validate_market_report_output(report, expected_report_type="daily")


def test_validation_errors_do_not_contain_financial_advice_messages():
    report = _valid_report("daily")
    report["coin_summaries"] = [{"symbol": "XRP", "summary": "XRP is moving."}]

    with pytest.raises(MarketReportValidationError) as exc_info:
        validate_market_report_output(report, expected_report_type="daily")

    message = str(exc_info.value)
    assert "personalized financial advice detected" not in message
    assert "direct financial advice" not in message
    assert "direct trading command" not in message
