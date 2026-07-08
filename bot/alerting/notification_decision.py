"""Product-level notification type used for persisted alert-state bookkeeping."""

from __future__ import annotations

from enum import Enum


class NotificationType(str, Enum):
    NO_ALERT = "no_alert"
    MARKET_UPDATE = "market_update"
    IMPORTANT_ALERT = "important_alert"
    CRITICAL_ALERT = "critical_alert"
