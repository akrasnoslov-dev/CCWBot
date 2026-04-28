from datetime import datetime, timezone, timedelta


def calculate_price_change_percent(old_price: float, new_price: float) -> float:
    """Calculate percentage change between old and new price."""
    return ((new_price - old_price) / old_price) * 100


def is_alert_cooldown_active(
    last_alert_at: str | None,
    cooldown_minutes: int,
) -> bool:
    """Return True if the previous alert was sent recently."""
    if last_alert_at is None:
        return False

    try:
        last_alert_time = datetime.fromisoformat(last_alert_at)
    except ValueError:
        return False

    cooldown_until = last_alert_time + timedelta(minutes=cooldown_minutes)
    now = datetime.now(timezone.utc)

    return now < cooldown_until


def should_send_alert(
    price_change_percent: float,
    threshold_percent: float,
    last_alert_at: str | None,
    cooldown_minutes: int,
) -> tuple[bool, bool, bool]:
    """
    Decide whether to send alert.

    Returns:
    - movement_is_big_enough
    - cooldown_is_active
    - should_alert
    """
    movement_is_big_enough = abs(price_change_percent) >= threshold_percent
    cooldown_is_active = is_alert_cooldown_active(
        last_alert_at=last_alert_at,
        cooldown_minutes=cooldown_minutes,
    )

    should_alert = movement_is_big_enough and not cooldown_is_active

    return movement_is_big_enough, cooldown_is_active, should_alert
