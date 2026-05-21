"""Core alert-rule helpers used by automatic market checks."""

from datetime import datetime, timezone


def calculate_price_change_percent(old_price: float, new_price: float) -> float:
    """Calculate percentage change between old and new price."""
    return ((new_price - old_price) / old_price) * 100


def should_send_alert(price_change_percent: float, threshold_percent: float) -> bool:
    """Return True when movement since previous check meets threshold."""
    return abs(price_change_percent) >= threshold_percent


def is_cooldown_active(last_alert_at: datetime | None, cooldown_minutes: int) -> bool:
    """Return True while a previous alert is still inside the cooldown window."""
    if last_alert_at is None:
        return False
    if last_alert_at.tzinfo is None:
        last_alert_at = last_alert_at.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - last_alert_at).total_seconds()
    return elapsed < cooldown_minutes * 60
