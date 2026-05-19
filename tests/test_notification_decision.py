from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from bot import alerts
from bot.alerting.notification_decision import (
    NotificationSeverity,
    NotificationType,
    SignalContext,
    TriggerSource,
    decide_notification,
    notification_icon,
)
from bot.db.database import (
    get_user_symbol_alert_state,
    init_db,
    normalize_stored_severity,
    upsert_user_symbol_alert_state,
)


def _context(**overrides):
    data = {
        "symbol": "btc",
        "current_price": 78200.0,
        "latest_5m_change_percent": 0.1,
        "change_since_last_market_update_percent": 0.2,
        "user_period_change_percent": 0.2,
        "one_hour_change_percent": 0.2,
        "four_hour_change_percent": 0.5,
        "twenty_four_hour_change_percent": -0.8,
        "user_alert_frequency_seconds": 3600,
        "scheduled_market_update_due": False,
        "fast_movement_threshold_percent": 1.0,
        "cumulative_movement_threshold_percent": 1.0,
        "extreme_movement_threshold_percent": 5.0,
    }
    data.update(overrides)
    return SignalContext(**data)


def test_market_update_is_sent_on_frequency_when_market_is_calm():
    decision = decide_notification(_context(scheduled_market_update_due=True))

    assert decision.notification_type is NotificationType.MARKET_UPDATE
    assert decision.severity is NotificationSeverity.LOW
    assert decision.should_send is True
    assert decision.trigger_source is TriggerSource.SCHEDULED_MARKET_UPDATE


def test_fast_5m_movement_creates_important_alert():
    decision = decide_notification(_context(latest_5m_change_percent=-1.25))

    assert decision.notification_type is NotificationType.IMPORTANT_ALERT
    assert decision.trigger_source is TriggerSource.FAST_MOVEMENT


def test_extreme_5m_movement_creates_critical_alert():
    decision = decide_notification(_context(latest_5m_change_percent=-5.8))

    assert decision.notification_type is NotificationType.CRITICAL_ALERT
    assert decision.severity is NotificationSeverity.EXTREME


def test_same_direction_critical_alert_within_cooldown_is_suppressed():
    decision = decide_notification(
        _context(
            symbol="ton",
            current_price=1.005,
            latest_5m_change_percent=0.05,
            change_since_last_market_update_percent=5.4,
            user_period_change_percent=5.4,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            last_notification_type="critical_alert",
            last_notification_severity="extreme",
            last_notification_direction="up",
            suppression_context={"last_event_alert_price": 1.0},
        )
    )

    assert decision.notification_type is NotificationType.CRITICAL_ALERT
    assert decision.should_send is False
    assert decision.should_suppress is True


def test_ton_repeated_critical_pattern_sends_only_first_without_extension():
    first = decide_notification(
        _context(
            symbol="ton",
            current_price=1.0,
            latest_5m_change_percent=0.1,
            change_since_last_market_update_percent=5.6,
            user_period_change_percent=5.6,
        )
    )
    second = decide_notification(
        _context(
            symbol="ton",
            current_price=1.005,
            latest_5m_change_percent=0.05,
            change_since_last_market_update_percent=5.5,
            user_period_change_percent=5.5,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            last_notification_type="critical_alert",
            last_notification_severity="extreme",
            last_notification_direction="up",
            suppression_context={"last_event_alert_price": 1.0},
        )
    )
    third = decide_notification(
        _context(
            symbol="ton",
            current_price=1.01,
            latest_5m_change_percent=0.05,
            change_since_last_market_update_percent=5.7,
            user_period_change_percent=5.7,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=10),
            last_notification_type="critical_alert",
            last_notification_severity="extreme",
            last_notification_direction="up",
            suppression_context={"last_event_alert_price": 1.0},
        )
    )

    assert first.should_send is True
    assert second.should_send is False
    assert third.should_send is False


def test_same_direction_critical_with_btc_material_extension_is_allowed():
    decision = decide_notification(
        _context(
            symbol="btc",
            current_price=101.01,
            latest_5m_change_percent=0.05,
            change_since_last_market_update_percent=5.5,
            user_period_change_percent=5.5,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            last_notification_type="critical_alert",
            last_notification_severity="extreme",
            last_notification_direction="up",
            suppression_context={"last_event_alert_price": 100.0},
        )
    )

    assert decision.notification_type is NotificationType.CRITICAL_ALERT
    assert decision.should_send is True


def test_same_direction_critical_with_volatile_material_extension_is_allowed():
    decision = decide_notification(
        _context(
            symbol="ton",
            current_price=1.016,
            latest_5m_change_percent=0.05,
            change_since_last_market_update_percent=5.5,
            user_period_change_percent=5.5,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            last_notification_type="critical_alert",
            last_notification_severity="extreme",
            last_notification_direction="up",
            suppression_context={"last_event_alert_price": 1.0},
        )
    )

    assert decision.notification_type is NotificationType.CRITICAL_ALERT
    assert decision.should_send is True


def test_opposite_direction_critical_alert_is_allowed():
    decision = decide_notification(
        _context(
            latest_5m_change_percent=-5.5,
            change_since_last_market_update_percent=-5.5,
            user_period_change_percent=-5.5,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            last_notification_type="critical_alert",
            last_notification_severity="extreme",
            last_notification_direction="up",
            suppression_context={"last_event_alert_price": 100.0},
        )
    )

    assert decision.notification_type is NotificationType.CRITICAL_ALERT
    assert decision.should_send is True


def test_gradual_decline_creates_important_alert_without_fast_move():
    decision = decide_notification(
        _context(
            latest_5m_change_percent=-0.3,
            change_since_last_market_update_percent=-2.1,
            user_period_change_percent=-2.1,
            twenty_four_hour_change_percent=-3.4,
        )
    )

    assert decision.notification_type is NotificationType.IMPORTANT_ALERT
    assert decision.trigger_source in {
        TriggerSource.CUMULATIVE_MOVEMENT,
        TriggerSource.COMBINED_SIGNAL,
    }


def test_important_alert_suppression_prevents_repeated_same_direction_alert():
    decision = decide_notification(
        _context(
            change_since_last_market_update_percent=-1.4,
            user_period_change_percent=-1.4,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=20),
            last_notification_type="important_alert",
            last_notification_severity="medium",
            last_notification_direction="down",
            suppression_context={"previous_cumulative_movement_percent": -1.3},
        )
    )

    assert decision.should_send is False
    assert decision.should_suppress is True


def test_same_direction_important_alert_extending_materially_is_not_suppressed():
    decision = decide_notification(
        _context(
            current_price=99.0,
            latest_5m_change_percent=-0.2,
            change_since_last_market_update_percent=-2.2,
            user_period_change_percent=-2.2,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=20),
            last_notification_type="important_alert",
            last_notification_severity="medium",
            last_notification_direction="down",
            suppression_context={
                "previous_cumulative_movement_percent": -2.0,
                "last_important_alert_price": 100.0,
            },
        )
    )

    assert decision.should_send is True


def test_opposite_direction_important_alert_is_not_suppressed():
    decision = decide_notification(
        _context(
            latest_5m_change_percent=-1.2,
            change_since_last_market_update_percent=-1.2,
            user_period_change_percent=-1.2,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=20),
            last_notification_type="important_alert",
            last_notification_severity="medium",
            last_notification_direction="up",
            suppression_context={"previous_cumulative_movement_percent": 1.2},
        )
    )

    assert decision.notification_type is NotificationType.IMPORTANT_ALERT
    assert decision.should_send is True


def test_severity_escalation_bypasses_suppression():
    decision = decide_notification(
        _context(
            latest_5m_change_percent=-3.0,
            change_since_last_market_update_percent=-3.0,
            user_period_change_percent=-3.0,
            twenty_four_hour_change_percent=-4.0,
            relevant_news_items=[{"title": "Bitcoin ETF outflow accelerates"}],
            news_relevance_score="relevant",
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=20),
            last_notification_type="important_alert",
            last_notification_severity="medium",
            last_notification_direction="down",
            suppression_context={"previous_cumulative_movement_percent": -1.3},
        )
    )

    assert decision.should_send is True
    assert decision.severity in {NotificationSeverity.HIGH, NotificationSeverity.EXTREME}


def test_24h_trend_alone_does_not_spam_unscheduled_alerts():
    decision = decide_notification(_context(twenty_four_hour_change_percent=-6.0))

    assert decision.notification_type is NotificationType.NO_ALERT
    assert decision.should_send is False


def test_medium_news_without_price_reaction_does_not_send_important_alert():
    decision = decide_notification(
        _context(
            relevant_news_items=[{"title": "Bitcoin ETF flow update"}],
            news_candidates=[
                {
                    "title": "Bitcoin ETF flow update",
                    "source": "Example",
                    "url": "https://example.test/btc",
                    "relevance": "medium",
                }
            ],
            news_relevance_score="medium",
        )
    )

    assert decision.notification_type is NotificationType.NO_ALERT
    assert decision.should_send is False


def test_strong_non_shock_news_without_price_reaction_does_not_alert():
    decision = decide_notification(
        _context(
            relevant_news_items=[{"title": "Bitcoin ETF outflow accelerates"}],
            news_candidates=[
                {
                    "title": "Bitcoin ETF outflow accelerates",
                    "source": "Example",
                    "url": "https://example.test/btc",
                    "relevance": "strong",
                }
            ],
            news_relevance_score="strong",
        )
    )

    assert decision.notification_type is NotificationType.NO_ALERT
    assert decision.should_send is False


def test_strong_non_shock_news_with_flat_price_does_not_send_critical():
    decision = decide_notification(
        _context(
            latest_5m_change_percent=-0.04,
            change_since_last_market_update_percent=-0.02,
            user_period_change_percent=-0.30,
            one_hour_change_percent=-0.30,
            twenty_four_hour_change_percent=0.03,
            relevant_news_items=[
                {
                    "title": (
                        "Swan Bitcoin sued for nearly $1B over pre-bankruptcy transfers "
                        "from Prime Trust"
                    )
                }
            ],
            news_candidates=[
                {
                    "title": (
                        "Swan Bitcoin sued for nearly $1B over pre-bankruptcy transfers "
                        "from Prime Trust"
                    ),
                    "relevance": "weak",
                }
            ],
            news_relevance_score="weak",
        )
    )

    assert decision.notification_type is NotificationType.NO_ALERT
    assert decision.should_send is False
    assert decision.reasoning_summary != "Major market-shock news was detected."


def test_true_exchange_withdrawal_freeze_news_can_trigger_critical():
    decision = decide_notification(
        _context(
            latest_5m_change_percent=0.05,
            change_since_last_market_update_percent=0.1,
            user_period_change_percent=0.1,
            one_hour_change_percent=0.1,
            twenty_four_hour_change_percent=0.2,
            relevant_news_items=[
                {"title": "Major crypto exchange halted withdrawals amid insolvency fears"}
            ],
            news_candidates=[
                {
                    "title": "Major crypto exchange halted withdrawals amid insolvency fears",
                    "relevance": "strong",
                }
            ],
            news_relevance_score="strong",
        )
    )

    assert decision.notification_type is NotificationType.CRITICAL_ALERT
    assert decision.trigger_source is TriggerSource.NEWS


def test_major_hack_news_can_trigger_critical():
    decision = decide_notification(
        _context(
            latest_5m_change_percent=0.05,
            change_since_last_market_update_percent=0.1,
            user_period_change_percent=0.1,
            relevant_news_items=[
                {"title": "Major hack hits large crypto bridge as exploit drains funds"}
            ],
            news_candidates=[
                {
                    "title": "Major hack hits large crypto bridge as exploit drains funds",
                    "relevance": "strong",
                }
            ],
            news_relevance_score="strong",
        )
    )

    assert decision.notification_type is NotificationType.CRITICAL_ALERT
    assert decision.trigger_source is TriggerSource.NEWS


def test_major_btc_etf_rejection_news_can_trigger_critical():
    decision = decide_notification(
        _context(
            latest_5m_change_percent=0.05,
            change_since_last_market_update_percent=0.1,
            user_period_change_percent=0.1,
            relevant_news_items=[{"title": "SEC rejected spot Bitcoin ETF applications"}],
            news_candidates=[
                {
                    "title": "SEC rejected spot Bitcoin ETF applications",
                    "relevance": "strong",
                }
            ],
            news_relevance_score="strong",
        )
    )

    assert decision.notification_type is NotificationType.CRITICAL_ALERT
    assert decision.trigger_source is TriggerSource.NEWS


def test_relevant_news_with_price_movement_becomes_important_or_critical():
    decision = decide_notification(
        _context(
            latest_5m_change_percent=-2.5,
            change_since_last_market_update_percent=-2.8,
            relevant_news_items=[{"title": "Bitcoin liquidation cascade hits market"}],
            news_relevance_score="very_relevant",
        )
    )

    assert decision.notification_type in {
        NotificationType.IMPORTANT_ALERT,
        NotificationType.CRITICAL_ALERT,
    }
    assert decision.trigger_source in {TriggerSource.COMBINED_SIGNAL, TriggerSource.NEWS}


def test_negative_threshold_wording_uses_absolute_values():
    decision = decide_notification(_context(latest_5m_change_percent=-1.25))

    assert "moved down by 1.25%" in decision.reasoning_summary
    assert "1.0% movement threshold" in decision.reasoning_summary


def test_market_update_is_not_blocked_by_important_alert_cooldown():
    decision = decide_notification(
        _context(
            scheduled_market_update_due=True,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=20),
            last_notification_type="important_alert",
            last_notification_severity="medium",
            last_notification_direction="down",
        )
    )

    assert decision.notification_type is NotificationType.MARKET_UPDATE
    assert decision.should_send is True


def test_same_direction_important_alert_respects_user_frequency_cooldown():
    decision = decide_notification(
        _context(
            change_since_last_market_update_percent=-1.4,
            user_period_change_percent=-1.4,
            last_notification_time=datetime.now(timezone.utc) - timedelta(minutes=90),
            last_notification_type="important_alert",
            last_notification_severity="medium",
            last_notification_direction="down",
            user_alert_frequency_seconds=7200,
            suppression_context={"previous_cumulative_movement_percent": -1.3},
        )
    )

    assert decision.should_send is False
    assert decision.should_suppress is True


def test_market_update_calm_period_weak_24h_is_medium_not_high():
    decision = decide_notification(
        _context(
            scheduled_market_update_due=True,
            user_period_change_percent=0.17,
            change_since_last_market_update_percent=0.17,
            twenty_four_hour_change_percent=-5.87,
        )
    )

    assert decision.notification_type is NotificationType.MARKET_UPDATE
    assert decision.severity is NotificationSeverity.LOW


def test_market_update_calm_period_mild_24h_is_low():
    decision = decide_notification(
        _context(
            scheduled_market_update_due=True,
            user_period_change_percent=-0.25,
            change_since_last_market_update_percent=-0.25,
            twenty_four_hour_change_percent=-2.48,
        )
    )

    assert decision.notification_type is NotificationType.MARKET_UPDATE
    assert decision.severity is NotificationSeverity.LOW


def test_market_update_meaningful_period_same_direction_can_be_high():
    decision = decide_notification(
        _context(
            scheduled_market_update_due=True,
            user_period_change_percent=3.11,
            change_since_last_market_update_percent=3.11,
            twenty_four_hour_change_percent=3.31,
            fast_movement_threshold_percent=5.0,
            cumulative_movement_threshold_percent=5.0,
            extreme_movement_threshold_percent=10.0,
        )
    )

    assert decision.notification_type is NotificationType.MARKET_UPDATE
    assert decision.severity in {NotificationSeverity.MEDIUM, NotificationSeverity.HIGH}


def test_icons_match_notification_type_and_direction():
    assert (
        notification_icon(
            NotificationType.IMPORTANT_ALERT,
            "down",
            NotificationSeverity.MEDIUM,
            TriggerSource.FAST_MOVEMENT,
        )
        == "📉"
    )
    assert (
        notification_icon(
            NotificationType.IMPORTANT_ALERT,
            "up",
            NotificationSeverity.MEDIUM,
            TriggerSource.FAST_MOVEMENT,
        )
        == "📈"
    )
    assert (
        notification_icon(
            NotificationType.CRITICAL_ALERT,
            "down",
            NotificationSeverity.EXTREME,
            TriggerSource.FAST_MOVEMENT,
        )
        == "🚨"
    )


def test_market_update_payload_is_per_symbol_not_grouped():
    payload = alerts._build_product_notification_payload(
        alerts.SignalContext(
            symbol="btc",
            current_price=100.0,
            user_period_change_percent=0.33,
            twenty_four_hour_change_percent=-1.55,
            news_relevance_score="none",
            user_alert_frequency_seconds=3600,
        ),
        alerts.NotificationDecision(
            notification_type=alerts.NotificationType.MARKET_UPDATE,
            severity=alerts.NotificationSeverity.LOW,
            direction=alerts.NotificationDirection.NEUTRAL,
            should_send=True,
            should_suppress=False,
            trigger_source=alerts.TriggerSource.SCHEDULED_MARKET_UPDATE,
            reasoning_summary="No significant short-term movement detected.",
            possible_action="No urgent action needed. Continue monitoring.",
            icon="📊",
        ),
    )

    message = payload["plain_text"]
    assert message.startswith("📊 Market Update - BTC")
    assert "ETH:" not in message
    assert "5m change" not in message


def test_calm_market_update_does_not_claim_meaningful_movement():
    payload = alerts._build_product_notification_payload(
        alerts.SignalContext(
            symbol="btc",
            current_price=100.0,
            user_period_change_percent=0.33,
            twenty_four_hour_change_percent=-1.0,
            news_relevance_score="none",
            user_alert_frequency_seconds=3600,
        ),
        alerts.NotificationDecision(
            notification_type=alerts.NotificationType.MARKET_UPDATE,
            severity=alerts.NotificationSeverity.LOW,
            direction=alerts.NotificationDirection.NEUTRAL,
            should_send=True,
            should_suppress=False,
            trigger_source=alerts.TriggerSource.SCHEDULED_MARKET_UPDATE,
            reasoning_summary="No significant short-term movement detected.",
            possible_action="No urgent action needed. Continue monitoring.",
            icon="📊",
        ),
    )

    assert "meaningful movement" not in payload["plain_text"]
    assert "No significant short-term movement detected." in payload["plain_text"]
    assert "relevant news" not in payload["plain_text"].lower()
    assert "News context:" not in payload["plain_text"]
    assert "Related news:" not in payload["plain_text"]


def test_conflicting_period_and_24h_direction_uses_mixed_timeframe_wording():
    summary = alerts._summary_sentence(
        "DOGE",
        alerts.NotificationDirection.DOWN,
        alerts.NotificationType.MARKET_UPDATE,
        period_change_percent=0.17,
        change_24h=-5.87,
        period_label="1h",
    )

    assert summary == "DOGE is stable over the last 1h, but remains weak on the 24h trend."
    assert "is weakening" not in summary


def test_market_update_slightly_lower_with_mild_negative_24h_wording():
    summary = alerts._summary_sentence(
        "BTC",
        alerts.NotificationDirection.DOWN,
        alerts.NotificationType.MARKET_UPDATE,
        period_change_percent=-0.55,
        change_24h=-2.17,
        period_label="1h",
    )

    assert summary == (
        "BTC is slightly lower over the last 1h, while the 24h trend "
        "remains mildly negative."
    )


def test_market_update_recovery_but_negative_24h_wording():
    summary = alerts._summary_sentence(
        "ETH",
        alerts.NotificationDirection.DOWN,
        alerts.NotificationType.MARKET_UPDATE,
        period_change_percent=0.46,
        change_24h=-2.66,
        period_label="1h",
    )

    assert summary == (
        "ETH recovered slightly over the last 1h, but the 24h trend "
        "remains mildly negative."
    )


def test_market_update_meaningful_period_and_positive_24h_wording():
    summary = alerts._summary_sentence(
        "TON",
        alerts.NotificationDirection.UP,
        alerts.NotificationType.MARKET_UPDATE,
        period_change_percent=3.11,
        change_24h=3.31,
        period_label="1h",
    )

    assert summary == (
        "TON strengthened meaningfully over the last 1h and remains "
        "positive on the 24h trend."
    )


def test_market_update_calm_period_and_mild_negative_24h_wording():
    summary = alerts._summary_sentence(
        "BNB",
        alerts.NotificationDirection.DOWN,
        alerts.NotificationType.MARKET_UPDATE,
        period_change_percent=-0.25,
        change_24h=-2.48,
        period_label="1h",
    )

    assert summary == (
        "BNB is stable over the last 1h, but remains mildly negative "
        "on the 24h trend."
    )


def test_weak_news_is_hidden_from_user_message():
    payload = alerts._build_product_notification_payload(
        alerts.SignalContext(
            symbol="btc",
            current_price=100.0,
            user_period_change_percent=0.2,
            twenty_four_hour_change_percent=-0.5,
            relevant_news_items=[{"title": "Weak related headline", "source": "Example"}],
            news_relevance_score="weak",
            user_alert_frequency_seconds=3600,
        ),
        alerts.NotificationDecision(
            notification_type=alerts.NotificationType.MARKET_UPDATE,
            severity=alerts.NotificationSeverity.LOW,
            direction=alerts.NotificationDirection.NEUTRAL,
            should_send=True,
            should_suppress=False,
            trigger_source=alerts.TriggerSource.SCHEDULED_MARKET_UPDATE,
            reasoning_summary="The market is calm over the last update window.",
            possible_action="No urgent action needed. Continue monitoring.",
            icon="📊",
        ),
    )

    assert "Weak related headline" not in payload["plain_text"]
    assert "No clear news catalyst found." not in payload["plain_text"]


def test_medium_news_is_shown_in_scheduled_update():
    payload = alerts._build_product_notification_payload(
        alerts.SignalContext(
            symbol="btc",
            current_price=100.0,
            user_period_change_percent=1.2,
            twenty_four_hour_change_percent=-2.0,
            relevant_news_items=[{"title": "Material BTC headline", "source": "Example"}],
            news_candidates=[
                {
                    "title": "Material BTC headline",
                    "source": "Example",
                    "url": "https://example.test/btc",
                    "relevance": "medium",
                    "reason": "BTC-specific market context",
                }
            ],
            news_relevance_score="medium",
            user_alert_frequency_seconds=3600,
        ),
        alerts.NotificationDecision(
            notification_type=alerts.NotificationType.MARKET_UPDATE,
            severity=alerts.NotificationSeverity.MEDIUM,
            direction=alerts.NotificationDirection.DOWN,
            should_send=True,
            should_suppress=False,
            trigger_source=alerts.TriggerSource.SCHEDULED_MARKET_UPDATE,
            reasoning_summary="The scheduled update includes relevant news context.",
            possible_action="No urgent action needed. Continue monitoring.",
            icon="📰",
        ),
    )

    assert "Material BTC headline" in payload["plain_text"]
    assert "https://example.test/btc" in payload["plain_text"]


def test_important_no_news_uses_news_context_not_related_news():
    payload = alerts._build_product_notification_payload(
        alerts.SignalContext(
            symbol="btc",
            current_price=100.0,
            latest_5m_change_percent=1.2,
            user_period_change_percent=1.2,
            one_hour_change_percent=1.0,
            twenty_four_hour_change_percent=0.5,
            news_relevance_score="none",
            user_alert_frequency_seconds=3600,
        ),
        alerts.NotificationDecision(
            notification_type=alerts.NotificationType.IMPORTANT_ALERT,
            severity=alerts.NotificationSeverity.MEDIUM,
            direction=alerts.NotificationDirection.UP,
            should_send=True,
            should_suppress=False,
            trigger_source=alerts.TriggerSource.FAST_MOVEMENT,
            reasoning_summary="The coin moved up by 1.20% on the 5-minute move.",
            possible_action="Watch whether the move continues or fades.",
            icon="ðŸ“ˆ",
        ),
    )

    message = payload["plain_text"]
    assert "News context:\nNo clear news catalyst found." in message
    assert "Related news:" not in message
    assert "5m change" not in message


def test_runtime_swan_false_positive_message_shape_is_not_sharp_or_user_visible_news():
    context = alerts.SignalContext(
        symbol="btc",
        current_price=76743.0,
        latest_5m_change_percent=-0.0416,
        change_since_last_market_update_percent=-0.0234,
        user_period_change_percent=-0.30,
        one_hour_change_percent=-0.2962,
        twenty_four_hour_change_percent=0.0267,
        news_candidates=[
            {
                "reason": "Weak BTC mention without clear market catalyst",
                "relevance": "weak",
                "title": (
                    "Swan Bitcoin sued for nearly $1B over pre-bankruptcy transfers "
                    "from Prime Trust"
                ),
                "url": "https://example.test/swan",
                "source": "Cointelegraph.com News",
            }
        ],
        news_relevance_score="weak",
        user_alert_frequency_seconds=3600,
    )
    decision = alerts.NotificationDecision(
        notification_type=alerts.NotificationType.IMPORTANT_ALERT,
        severity=alerts.NotificationSeverity.LOW,
        direction=alerts.NotificationDirection.DOWN,
        should_send=True,
        should_suppress=False,
        trigger_source=alerts.TriggerSource.NEWS,
        reasoning_summary=(
            "Relevant market news appeared without a strong confirmed price reaction."
        ),
        possible_action="Monitor whether price starts reacting during the next update window.",
        icon="ðŸ“°",
    )

    message = alerts._build_product_notification_payload(context, decision)["plain_text"]

    assert "5m change" not in message
    assert "dropped sharply" not in message
    assert "jumped sharply" not in message
    assert "gaining momentum" not in message
    assert "Swan Bitcoin sued" not in message
    assert "Related news:" not in message


def test_product_message_grammar_does_not_include_bad_prepositions():
    decision = decide_notification(
        _context(
            change_since_last_market_update_percent=1.76,
            user_period_change_percent=1.76,
        )
    )

    assert "on the since" not in decision.reasoning_summary
    assert "on the over" not in decision.reasoning_summary
    assert "over the since" not in decision.reasoning_summary


def test_summary_does_not_gain_momentum_when_one_hour_move_is_negative():
    summary = alerts._summary_sentence(
        "BTC",
        alerts.NotificationDirection.UP,
        alerts.NotificationType.IMPORTANT_ALERT,
        trigger_source=alerts.TriggerSource.COMBINED_SIGNAL,
        alert_move_percent=1.2,
        one_hour_change_percent=-0.38,
    )

    assert "gaining momentum" not in summary
    assert "moving down" in summary


def test_news_triggered_flat_summary_does_not_claim_sharp_move():
    summary = alerts._summary_sentence(
        "BTC",
        alerts.NotificationDirection.DOWN,
        alerts.NotificationType.CRITICAL_ALERT,
        trigger_source=alerts.TriggerSource.NEWS,
        alert_move_percent=-0.30,
        one_hour_change_percent=-0.30,
    )

    assert "dropped sharply" not in summary
    assert "jumped sharply" not in summary
    assert "gaining momentum" not in summary
    assert summary == "BTC has relevant market news, while price remains mostly stable."


def test_news_candidates_are_stored_in_numeric_context():
    context = alerts.SignalContext(
        symbol="btc",
        current_price=100.0,
        user_period_change_percent=1.2,
        twenty_four_hour_change_percent=-2.0,
        news_candidates=[
            {
                "title": "Material BTC headline",
                "source": "Example",
                "url": "https://example.test/btc",
                "relevance": "medium",
                "reason": "BTC-specific market context",
            }
        ],
        news_relevance_score="medium",
        user_alert_frequency_seconds=3600,
    )
    decision = alerts.NotificationDecision(
        notification_type=alerts.NotificationType.IMPORTANT_ALERT,
        severity=alerts.NotificationSeverity.MEDIUM,
        direction=alerts.NotificationDirection.DOWN,
        should_send=True,
        should_suppress=False,
        trigger_source=alerts.TriggerSource.NEWS,
        reasoning_summary="Relevant market news appeared.",
        possible_action="Monitor whether price starts reacting.",
        icon="ðŸ“°",
    )

    payload = json.loads(alerts._format_signal_context_for_storage(context, decision))

    assert payload["news_relevance_score"] == "medium"
    assert payload["news_candidates"][0]["url"] == "https://example.test/btc"


def test_weak_news_is_stored_but_hidden_from_message():
    context = alerts.SignalContext(
        symbol="btc",
        current_price=100.0,
        user_period_change_percent=0.2,
        twenty_four_hour_change_percent=-0.2,
        news_candidates=[
            {
                "title": "Weak BTC mention",
                "source": "Example",
                "url": "https://example.test/weak",
                "relevance": "weak",
                "reason": "Weak BTC mention without clear market catalyst",
            }
        ],
        news_relevance_score="weak",
        user_alert_frequency_seconds=3600,
    )
    decision = alerts.NotificationDecision(
        notification_type=alerts.NotificationType.MARKET_UPDATE,
        severity=alerts.NotificationSeverity.LOW,
        direction=alerts.NotificationDirection.NEUTRAL,
        should_send=True,
        should_suppress=False,
        trigger_source=alerts.TriggerSource.SCHEDULED_MARKET_UPDATE,
        reasoning_summary="No significant short-term movement detected.",
        possible_action="No urgent action needed. Continue monitoring.",
        icon="ðŸ“Š",
    )

    payload = alerts._build_product_notification_payload(context, decision)["plain_text"]
    stored = json.loads(alerts._format_signal_context_for_storage(context, decision))

    assert "Weak BTC mention" not in payload
    assert stored["news_candidates"][0]["title"] == "Weak BTC mention"


def test_near_duplicate_calm_market_update_is_suppressed():
    previous = SimpleNamespace(
        alert_type="market_update",
        status="sent",
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        numeric_context=json.dumps(
            {
                "notification_type": "market_update",
                "notification_direction": "neutral",
                "notification_severity": "low",
                "user_period_change_percent": 0.15,
                "news_relevance_score": "none",
            }
        ),
    )
    context = alerts.SignalContext(
        symbol="btc",
        current_price=100.0,
        user_period_change_percent=0.2,
        news_relevance_score="none",
        user_alert_frequency_seconds=3600,
    )
    decision = alerts.NotificationDecision(
        notification_type=alerts.NotificationType.MARKET_UPDATE,
        severity=alerts.NotificationSeverity.LOW,
        direction=alerts.NotificationDirection.NEUTRAL,
        should_send=True,
        should_suppress=False,
        trigger_source=alerts.TriggerSource.SCHEDULED_MARKET_UPDATE,
        reasoning_summary="The market is calm over the last update window.",
        possible_action="No urgent action needed. Continue monitoring.",
        icon="ðŸ“Š",
    )

    assert alerts._should_skip_near_duplicate_market_update(
        notification_type=alerts.NotificationType.MARKET_UPDATE,
        previous_alert=previous,
        context=context,
        decision=decision,
        now=datetime.now(timezone.utc),
        frequency_seconds=3600,
    )


def test_meaningful_market_update_is_not_suppressed_as_duplicate():
    previous = SimpleNamespace(
        alert_type="market_update",
        status="sent",
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        numeric_context=json.dumps(
            {
                "notification_type": "market_update",
                "notification_direction": "neutral",
                "notification_severity": "low",
                "user_period_change_percent": 0.1,
                "news_relevance_score": "none",
            }
        ),
    )
    context = alerts.SignalContext(
        symbol="btc",
        current_price=100.0,
        user_period_change_percent=1.1,
        news_relevance_score="none",
        user_alert_frequency_seconds=3600,
    )
    decision = alerts.NotificationDecision(
        notification_type=alerts.NotificationType.MARKET_UPDATE,
        severity=alerts.NotificationSeverity.MEDIUM,
        direction=alerts.NotificationDirection.UP,
        should_send=True,
        should_suppress=False,
        trigger_source=alerts.TriggerSource.SCHEDULED_MARKET_UPDATE,
        reasoning_summary="The scheduled update shows mild movement over the last update window.",
        possible_action="Watch whether the move continues or fades.",
        icon="ðŸ“Š",
    )

    assert not alerts._should_skip_near_duplicate_market_update(
        notification_type=alerts.NotificationType.MARKET_UPDATE,
        previous_alert=previous,
        context=context,
        decision=decision,
        now=datetime.now(timezone.utc),
        frequency_seconds=3600,
    )


def test_llm_severity_is_normalized_to_allowed_values():
    assert normalize_stored_severity("info") == "low"
    assert normalize_stored_severity("watch") == "medium"
    assert normalize_stored_severity("moderate") == "medium"
    assert normalize_stored_severity("critical") == "extreme"


def test_new_user_facing_alert_types_are_limited_to_product_model():
    assert alerts.PRODUCT_ALERT_TYPES == {"market_update", "important_alert", "critical_alert"}


def test_recent_important_alert_suppresses_market_update_same_symbol():
    recent = SimpleNamespace(
        alert_type="important_alert",
        status="sent",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    assert alerts._should_skip_market_update_after_recent_event_alert(
        notification_type=alerts.NotificationType.MARKET_UPDATE,
        recent_event_alert=recent,
        now=datetime.now(timezone.utc),
    )


def test_recent_critical_alert_suppresses_market_update_same_symbol():
    recent = SimpleNamespace(
        alert_type="critical_alert",
        status="sent",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    assert alerts._should_skip_market_update_after_recent_event_alert(
        notification_type=alerts.NotificationType.MARKET_UPDATE,
        recent_event_alert=recent,
        now=datetime.now(timezone.utc),
    )


def test_failed_important_alert_does_not_suppress_market_update():
    recent = SimpleNamespace(
        alert_type="important_alert",
        status="failed",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    assert not alerts._should_skip_market_update_after_recent_event_alert(
        notification_type=alerts.NotificationType.MARKET_UPDATE,
        recent_event_alert=recent,
        now=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_last_market_update_time_persists_after_restart(tmp_path):
    db_path = tmp_path / "market_update.sqlite"
    engine, session_local = await init_db(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    update_time = datetime.now(timezone.utc)
    async with session_local() as session:
        await upsert_user_symbol_alert_state(
            session,
            user_id=1,
            symbol="btc",
            last_market_update_time=update_time,
        )

    async with session_local() as restarted_session:
        row = await get_user_symbol_alert_state(
            restarted_session,
            user_id=1,
            symbol="btc",
        )

    assert row is not None
    assert row.last_market_update_time is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_important_alert_updates_effective_baseline(tmp_path, monkeypatch):
    db_path = tmp_path / "important_baseline.sqlite"
    engine, session_local = await init_db(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", session_local)

    await alerts._persist_successful_product_alert_state(
        recipient=alerts.AlertRecipient(chat_id=123, user_id=1, alert_frequency_seconds=3600),
        symbol="eth",
        event_type=alerts.NotificationType.IMPORTANT_ALERT.value,
        severity="medium",
        numeric_context=json.dumps(
            {
                "notification_direction": "up",
                "change_since_last_market_update_percent": 1.4,
                "current_price": 2500.0,
            }
        ),
    )

    async with session_local() as session:
        row = await get_user_symbol_alert_state(session, user_id=1, symbol="eth")

    assert row is not None
    assert row.last_important_alert_time is not None
    assert row.last_market_update_time is not None
    assert row.last_cumulative_movement_percent == 1.4
    await engine.dispose()
