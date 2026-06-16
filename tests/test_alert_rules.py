from datetime import datetime, timedelta, timezone

from bot.alerting.alert_rules import (
    calculate_price_change_percent,
    is_cooldown_active,
    should_send_alert,
)


def test_should_send_alert_compares_absolute_move_to_threshold():
    assert should_send_alert(price_change_percent=2.1, threshold_percent=2.0) is True
    assert should_send_alert(price_change_percent=1.9, threshold_percent=2.0) is False


def test_calculate_price_change_percent_preserves_direction():
    assert calculate_price_change_percent(old_price=100.0, new_price=110.0) == 10.0
    assert calculate_price_change_percent(old_price=100.0, new_price=90.0) == -10.0


def test_cooldown_active_only_inside_window():
    assert (
        is_cooldown_active(
            datetime.now(timezone.utc) - timedelta(minutes=5),
            cooldown_minutes=30,
        )
        is True
    )
    assert is_cooldown_active(None, cooldown_minutes=30) is False
    assert (
        is_cooldown_active(
            datetime.now(timezone.utc) - timedelta(minutes=31),
            cooldown_minutes=30,
        )
        is False
    )
