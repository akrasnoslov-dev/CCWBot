from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import bot.application.trial_lifecycle as trial_lifecycle


class SessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


@pytest.mark.asyncio
async def test_trial_expiry_job_contains_lifecycle_failures(monkeypatch):
    logs = []
    monkeypatch.setattr(trial_lifecycle, "DB_ENABLED", True)
    monkeypatch.setattr(trial_lifecycle, "DB_SESSION_LOCAL", lambda: SessionContext())
    monkeypatch.setattr(
        trial_lifecycle,
        "expire_due_premium_trials",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )
    monkeypatch.setattr(trial_lifecycle, "log", logs.append)

    await trial_lifecycle.process_due_trial_expiries(SimpleNamespace())

    assert logs == ["ops_event=premium_trial_expiry_failed error_class=RuntimeError"]
