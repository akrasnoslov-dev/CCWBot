from bot.alerting.alert_severity import (
    AlertSeverity,
    AlertThresholds,
    AlertType,
    SeverityEvaluation,
    SeverityInput,
    alert_title_action,
    alert_type_label,
    evaluate_alert_decision,
    evaluate_alert_severity,
    render_severity_heading,
    severity_icon,
    severity_label,
)
from bot.alerts import _apply_severity_header


def test_icon_and_label_mapping_is_stable():
    assert severity_icon(AlertSeverity.INFO) == "ℹ️"
    assert severity_label(AlertSeverity.WATCH) == "Watch"
    assert render_severity_heading(AlertSeverity.HIGH) == "🚨 High"
    assert alert_type_label(AlertType.NEWS_SPIKE) == "News spike"
    assert alert_title_action(AlertType.VOLATILITY_SPIKE) == "volatility spike"


def test_small_btc_move_without_news_is_info_or_watch():
    result = evaluate_alert_severity(
        SeverityInput(
            symbol="btc",
            price_change_percent=0.4,
            change_24h=0.8,
            alert_threshold_percent=2.0,
            news_relevance="none",
        )
    )

    assert result.severity in {AlertSeverity.INFO, AlertSeverity.WATCH}
    assert result.primary_alert_type == AlertType.PRICE_MOVEMENT


def test_24h_threshold_crossing_is_high():
    result = evaluate_alert_severity(
        SeverityInput(
            symbol="btc",
            price_change_percent=0.8,
            change_24h=3.4,
            previous_24h_change=1.0,
            alert_threshold_percent=2.0,
        )
    )

    assert result.severity == AlertSeverity.HIGH
    assert result.primary_alert_type == AlertType.CHANGE_24H_THRESHOLD
    assert "24h threshold crossed" in result.signals


def test_volatility_spike_and_threshold_crossing_is_extreme():
    result = evaluate_alert_severity(
        SeverityInput(
            symbol="btc",
            price_change_percent=-4.2,
            change_24h=-6.2,
            previous_24h_change=-1.0,
            alert_threshold_percent=2.0,
        )
    )

    assert result.severity == AlertSeverity.EXTREME
    assert result.primary_alert_type == AlertType.VOLATILITY_SPIKE
    assert "Volatility spike detected" in result.signals


def test_strong_signal_with_relevant_news_escalates():
    result = evaluate_alert_severity(
        SeverityInput(
            symbol="btc",
            change_24h=2.6,
            change_7d=5.0,
            news_relevance="relevant",
            strong_signal_strength="strong",
        )
    )

    assert result.severity in {AlertSeverity.HIGH, AlertSeverity.EXTREME}
    assert result.primary_alert_type == AlertType.STRONG_SIGNAL


def test_weak_news_only_stays_low_severity():
    result = evaluate_alert_severity(
        SeverityInput(
            symbol="btc",
            price_change_percent=0.1,
            change_24h=0.2,
            news_relevance="weak",
        )
    )

    assert result.severity in {AlertSeverity.INFO, AlertSeverity.WATCH}


def test_ton_movement_below_threshold_is_not_price_movement_alert():
    decision = evaluate_alert_decision(
        symbol="ton",
        movement_percent=0.52,
        change_24h=1.0,
        thresholds=AlertThresholds(
            movement_percent=2.0,
            trend_24h_medium_percent=5.0,
            trend_24h_high_percent=8.0,
        ),
    )

    assert decision.should_alert is False
    assert decision.alert_type is None


def test_ton_24h_trend_trigger_is_not_price_movement_alert():
    decision = evaluate_alert_decision(
        symbol="ton",
        movement_percent=0.52,
        change_24h=-5.55,
        thresholds=AlertThresholds(
            movement_percent=2.0,
            trend_24h_medium_percent=5.0,
            trend_24h_high_percent=8.0,
        ),
    )

    assert decision.should_alert is True
    assert decision.alert_type == AlertType.TREND_24H
    assert decision.backend_severity_ceiling is AlertSeverity.WATCH


def test_combined_and_news_only_decisions_are_typed():
    thresholds = AlertThresholds(
        movement_percent=1.0,
        trend_24h_medium_percent=3.0,
        trend_24h_high_percent=5.0,
    )

    combined = evaluate_alert_decision(
        symbol="btc",
        movement_percent=1.5,
        change_24h=2.0,
        thresholds=thresholds,
        news_relevance="relevant",
    )
    news_only = evaluate_alert_decision(
        symbol="btc",
        movement_percent=0.2,
        change_24h=0.5,
        thresholds=thresholds,
        news_relevance="very_relevant",
    )

    assert combined.alert_type == AlertType.COMBINED
    assert news_only.alert_type == AlertType.NEWS
    assert news_only.backend_severity_ceiling is AlertSeverity.WATCH


def test_news_only_with_near_zero_move_defaults_low():
    decision = evaluate_alert_decision(
        symbol="btc",
        movement_percent=0.0,
        change_24h=-1.02,
        thresholds=AlertThresholds(
            movement_percent=1.0,
            trend_24h_medium_percent=3.0,
            trend_24h_high_percent=5.0,
        ),
        news_relevance="relevant",
    )

    assert decision.alert_type == AlertType.NEWS
    assert decision.backend_severity_ceiling is AlertSeverity.INFO


def test_weak_generic_news_does_not_trigger_alert():
    decision = evaluate_alert_decision(
        symbol="btc",
        movement_percent=0.0,
        change_24h=-1.02,
        thresholds=AlertThresholds(
            movement_percent=1.0,
            trend_24h_medium_percent=3.0,
            trend_24h_high_percent=5.0,
        ),
        news_relevance="weak",
    )

    assert decision.should_alert is False
    assert decision.alert_type is None


def test_weekly_trend_change_alert_type():
    result = evaluate_alert_severity(
        SeverityInput(
            symbol="eth",
            price_change_percent=-1.2,
            change_24h=-2.5,
            change_7d=7.0,
            alert_threshold_percent=2.0,
        )
    )

    assert result.primary_alert_type == AlertType.WEEKLY_TREND_CHANGE
    assert "Weekly trend direction is changing" in result.signals


def test_missing_weekly_trend_does_not_block_severity_evaluation():
    result = evaluate_alert_severity(
        SeverityInput(
            symbol="eth",
            price_change_percent=-1.2,
            change_24h=-2.5,
            change_7d=None,
            alert_threshold_percent=2.0,
        )
    )

    assert result.primary_alert_type is not AlertType.WEEKLY_TREND_CHANGE
    assert result.severity in {
        AlertSeverity.INFO,
        AlertSeverity.WATCH,
        AlertSeverity.HIGH,
        AlertSeverity.EXTREME,
    }


def _format_message(
    *,
    symbol: str,
    severity: AlertSeverity,
    alert_type: AlertType,
    signals: tuple[str, ...] = ("Price movement threshold crossed",),
) -> str:
    payload = {
        "plain_text": (
            f"{symbol.upper()} movement alert\n\n"
            "Price: $2.27\n"
            "Since last check: +0.44% in 60 sec\n"
            "24h trend: -7.33%\n"
            "Risk level: Low\n"
            "Risk reason: The short-term move happened alongside a stronger 24h trend, "
            "increasing volatility risk.\n\n"
            "Possible action:\n"
            "Monitor the situation and wait for further confirmation.\n\n"
            "Not financial advice."
        ),
        "html_text": None,
    }
    result = _apply_severity_header(
        payload,
        symbol=symbol,
        severity=SeverityEvaluation(
            severity=severity,
            primary_alert_type=alert_type,
            signals=signals,
        ),
    )
    return result["plain_text"]


def test_formatted_alert_removes_risk_level_and_keeps_reason():
    message = _format_message(
        symbol="ton",
        severity=AlertSeverity.HIGH,
        alert_type=AlertType.PRICE_MOVEMENT,
    )

    assert "Risk level:" not in message
    assert "Risk reason:" not in message
    assert "Reason:\nThe short-term move happened" in message
    assert message.endswith("Not financial advice.")


def test_formatted_alert_shows_severity_title_type_and_coin():
    message = _format_message(
        symbol="ton",
        severity=AlertSeverity.HIGH,
        alert_type=AlertType.PRICE_MOVEMENT,
    )

    assert message.startswith("🔴 High - GRAM movement alert")
    assert "\nType:" not in message
    assert "\nCoin: GRAM\n" in message
    assert message.count("Coin:") == 1


def test_price_movement_alerts_include_severity_icons():
    info = _format_message(
        symbol="ton",
        severity=AlertSeverity.INFO,
        alert_type=AlertType.PRICE_MOVEMENT,
        signals=(),
    )
    watch = _format_message(
        symbol="xrp",
        severity=AlertSeverity.WATCH,
        alert_type=AlertType.PRICE_MOVEMENT,
    )
    high = _format_message(
        symbol="btc",
        severity=AlertSeverity.HIGH,
        alert_type=AlertType.PRICE_MOVEMENT,
    )

    assert info.startswith("🟢 Low - GRAM movement alert")
    assert watch.startswith("🟡 Medium - XRP movement alert")
    assert high.startswith("🔴 High - BTC movement alert")


def test_extreme_volatility_spike_uses_fire_icon():
    message = _format_message(
        symbol="btc",
        severity=AlertSeverity.EXTREME,
        alert_type=AlertType.VOLATILITY_SPIKE,
        signals=("Volatility spike detected",),
    )

    assert message.startswith("🔴 High - BTC volatility spike")
    assert "\nType:" not in message


def test_all_supported_alert_types_use_same_header_model():
    for alert_type in AlertType:
        message = _format_message(
            symbol="eth",
            severity=AlertSeverity.HIGH,
            alert_type=alert_type,
        )

        assert message.startswith(f"🔴 High - ETH {alert_title_action(alert_type)}")
        assert "\nType:" not in message
        assert "\nCoin: ETH / Ethereum\n" in message
        assert "Risk level:" not in message
