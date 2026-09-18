"""Core alert-rule helpers used by automatic market checks."""

from datetime import datetime, timezone
from decimal import Decimal


def calculate_price_change_percent(
    old_price: Decimal | float | int,
    new_price: Decimal | float | int,
) -> Decimal:
    """Calculate a percent change without mixing binary floats and ``Decimal`` values."""
    old = Decimal(str(old_price))
    new = Decimal(str(new_price))
    return ((new - old) / old) * Decimal("100")


def is_cooldown_active(last_alert_at: datetime | None, cooldown_minutes: int) -> bool:
    """Return True while a previous alert is still inside the cooldown window."""
    if last_alert_at is None:
        return False
    if last_alert_at.tzinfo is None:
        last_alert_at = last_alert_at.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - last_alert_at).total_seconds()
    return elapsed < cooldown_minutes * 60
