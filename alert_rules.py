"""Core alert-rule helpers used by automatic BTC checks."""


def calculate_price_change_percent(old_price: float, new_price: float) -> float:
    """Calculate percentage change between old and new price."""
    return ((new_price - old_price) / old_price) * 100


def should_send_alert(price_change_percent: float, threshold_percent: float) -> bool:
    """Return True when movement since previous check meets threshold."""
    return abs(price_change_percent) >= threshold_percent
