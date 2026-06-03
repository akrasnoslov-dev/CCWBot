from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from ops_agent.collectors.health import collect_health
from ops_agent.config import OpsAgentConfig
from ops_agent.redaction import RedactionReport, ReferenceMapper
from ops_agent.schemas import Period


class FakeAsyncClient:
    def __init__(self, response: httpx.Response, *, timeout: float) -> None:
        self.response = response
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url: str) -> httpx.Response:
        return self.response


@pytest.mark.asyncio
async def test_health_collector_treats_degraded_body_as_partial(monkeypatch, tmp_path):
    response = httpx.Response(200, json={"status": "degraded", "uptime_seconds": 10})
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda timeout: FakeAsyncClient(response, timeout=timeout),
    )
    period = Period(
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        source="test",
    )
    config = OpsAgentConfig(
        database_url=None,
        health_url="http://bot:8080/health",
        output_dir=tmp_path,
        logs_dir=tmp_path / "logs",
        legacy_state_path=tmp_path / "state.json",
    )

    payload, status = await collect_health(
        config=config,
        period=period,
        mapper=ReferenceMapper(salt=b"0" * 32),
        redaction_report=RedactionReport(),
    )

    assert payload["http_status"] == 200
    assert payload["status"] == "failed"
    assert payload["body_status"] == "degraded"
    assert status["status"] == "partial"
