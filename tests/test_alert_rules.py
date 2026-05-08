from datetime import datetime, timedelta, timezone

from alert_rules import is_cooldown_active


def test_cooldown_active_when_recent_alert():
    last_alert_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    assert is_cooldown_active(last_alert_at, cooldown_minutes=30) is True


def test_cooldown_inactive_when_no_previous_alert():
    assert is_cooldown_active(None, cooldown_minutes=30) is False


def test_cooldown_inactive_after_enough_time():
    last_alert_at = datetime.now(timezone.utc) - timedelta(minutes=31)

    assert is_cooldown_active(last_alert_at, cooldown_minutes=30) is False
