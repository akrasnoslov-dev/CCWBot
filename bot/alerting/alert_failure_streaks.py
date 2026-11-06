"""In-process, per-symbol Event Alert reliability counters.

These counters are advisory. They never change market significance or delivery.
The ops-agent's persisted terminal-outcome queries provide the cross-restart view.
"""

from __future__ import annotations


class AlertFailureStreaks:
    """Count consecutive failures for separate Stage-1 and Render operations."""

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = {}

    @staticmethod
    def _key(stage: str, symbol: str) -> tuple[str, str]:
        if stage not in {"stage1", "render"}:
            raise ValueError("unknown Event Alert stage")
        return stage, symbol.upper()

    def failure(self, stage: str, symbol: str) -> int:
        key = self._key(stage, symbol)
        streak = self._counts.get(key, 0) + 1
        self._counts[key] = streak
        return streak

    def success(self, stage: str, symbol: str) -> int:
        """Reset after a proven successful stage; return preceding streak."""
        return self._counts.pop(self._key(stage, symbol), 0)

    def get(self, stage: str, symbol: str) -> int:
        return self._counts.get(self._key(stage, symbol), 0)

    def clear(self) -> None:
        """Test isolation only; the bot creates one in-process tracker."""
        self._counts.clear()


alert_failure_streaks = AlertFailureStreaks()
STREAK_WARNING_THRESHOLD = 3
