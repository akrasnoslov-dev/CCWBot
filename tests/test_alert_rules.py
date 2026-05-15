from datetime import datetime, timedelta, timezone

from bot.alerting.alert_rules import (
    calculate_price_change_percent,
    is_cooldown_active,
    should_send_alert,
)


def test_should_send_alert_above_threshold():
    assert should_send_alert(price_change_percent=2.1, threshold_percent=2.0) is True


def test_should_not_send_alert_below_threshold():
    assert should_send_alert(price_change_percent=1.9, threshold_percent=2.0) is False


def test_calculate_price_change_percent_positive():
    assert calculate_price_change_percent(old_price=100.0, new_price=110.0) == 10.0


def test_calculate_price_change_percent_negative():
    assert calculate_price_change_percent(old_price=100.0, new_price=90.0) == -10.0


def test_cooldown_active_when_recent_alert():
    last_alert_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    assert is_cooldown_active(last_alert_at, cooldown_minutes=30) is True


def test_cooldown_inactive_when_no_previous_alert():
    assert is_cooldown_active(None, cooldown_minutes=30) is False


def test_cooldown_inactive_after_enough_time():
    last_alert_at = datetime.now(timezone.utc) - timedelta(minutes=31)

    assert is_cooldown_active(last_alert_at, cooldown_minutes=30) is False
