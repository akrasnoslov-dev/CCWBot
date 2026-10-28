"""Offline regression coverage for read-only OpenAI project cost monitoring."""

import asyncio  # noqa: I001 - allow mixed imports in this isolated mock suite
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db.database import Base, OpenAIBudgetReservation
from bot.services.llm.openai_budget import OpenAIBudget
from bot.services.llm import openai_costs as costs


REAL_ASYNC_CLIENT = httpx.AsyncClient
START = datetime(2026, 10, 1, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
PROJECT = "proj_ccwbot"


def bucket(day, value="0.1", project=PROJECT):
    begin = int((START + timedelta(days=day)).timestamp())
    return {
        "object": "bucket",
        "start_time": begin,
        "end_time": begin + 86400,
        "results": [{
            "object": "organization.costs.result",
            "project_id": project,
            "amount": {"value": Decimal(value), "currency": "usd"},
        }],
    }


def page(data, *, more=False, cursor=None):
    return {
        "object": "page", "data": data, "has_more": more, "next_page": cursor,
    }


def client_mock(monkeypatch, responses):
    """Mock every HTTP request without outbound API calls."""
    seen = []
    original_client = REAL_ASYNC_CLIENT

    def handler(request):
        seen.append(request)
        idx = len(seen) - 1
        response = responses[min(idx, len(responses) - 1)]
        if isinstance(response, Exception):
            raise response
        status, payload = response
        return httpx.Response(
            status,
            text=json.dumps(
                payload, default=lambda value: float(value) if isinstance(value, Decimal) else value
            ),
        )

    monkeypatch.setattr(
        costs.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    return seen


def configured(monkeypatch):
    monkeypatch.setenv("OPENAI_COSTS_ADMIN_KEY", "synthetic-admin-key")
    monkeypatch.setenv("OPENAI_COSTS_PROJECT_ID", PROJECT)


def test_decimal_parser_sums_daily_buckets_exactly():
    raw = '{"object":"page","data":[{"object":"bucket","start_time":1790812800,'
    raw += '"end_time":1790899200,"results":[{"object":"organization.costs.result",'
    raw += '"project_id":"proj_ccwbot","amount":{"value":0.1,"currency":"usd"}},'
    raw += '{"object":"organization.costs.result","project_id":"proj_ccwbot",'
    raw += '"amount":{"value":0.2,"currency":"usd"}}]}],'
    raw += '"has_more":false,"next_page":null}'
    payload = json.loads(raw, parse_float=Decimal)
    total, cursor, has_more, _ = costs._parse_page(
        payload, project_id=PROJECT, next_bucket=1790812800, end_time=1790899200,
    )
    assert total == Decimal("0.3")
    assert cursor == 1790899200
    assert has_more is False


@pytest.mark.asyncio
async def test_missing_configuration_never_calls_provider(monkeypatch):
    called = AsyncMock(side_effect=AssertionError("must not call provider"))
    monkeypatch.setattr(costs, "_fetch", called)
    monkeypatch.delenv("OPENAI_COSTS_ADMIN_KEY", raising=False)
    monkeypatch.setenv("OPENAI_COSTS_PROJECT_ID", PROJECT)
    assert (await costs.OpenAICostsMonitor().get(now=NOW))[0] == "NOT CONFIGURED"
    monkeypatch.setenv("OPENAI_COSTS_ADMIN_KEY", "dummy")
    monkeypatch.delenv("OPENAI_COSTS_PROJECT_ID", raising=False)
    assert (await costs.OpenAICostsMonitor().get(now=NOW))[0] == "NOT CONFIGURED"
    monkeypatch.setenv("OPENAI_COSTS_PROJECT_ID", "organization-wide")
    assert (await costs.OpenAICostsMonitor().get(now=NOW))[0] == "NOT CONFIGURED"
    called.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_reused_inference_key(monkeypatch):
    configured(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-admin-key")
    loader = AsyncMock(side_effect=AssertionError("no administrative request allowed"))
    monkeypatch.setattr(costs, "_fetch", loader)
    assert (await costs.OpenAICostsMonitor().get(now=NOW))[0] == "NOT CONFIGURED"
    loader.assert_not_awaited()


@pytest.mark.asyncio
async def test_success_multiple_days_with_pagination_and_scoping(monkeypatch):
    configured(monkeypatch)
    # Use native JSON numeric encoding, not a float calculated in Python.
    p1 = page([bucket(0, "1")], more=True, cursor="next")
    p2 = page([bucket(1, "2")])
    seen = client_mock(monkeypatch, [(200, p1), (200, p2)])
    state, snapshot = await costs.OpenAICostsMonitor().get(now=NOW)
    assert state == "OK"
    assert snapshot.total_usd == Decimal("3")
    assert snapshot.month_start == START
    assert snapshot.coverage_end == datetime(2026, 10, 3, tzinfo=timezone.utc)
    assert len(seen) == 2
    for request in seen:
        assert request.method == "GET"
        assert request.url.path == "/v1/organization/costs"
        assert request.url.params.get_list("project_ids") == [PROJECT]
        assert request.url.params.get_list("group_by") == ["project_id"]
        assert int(request.url.params["start_time"]) == int(START.timestamp())
        assert int(request.url.params["end_time"]) == int(snapshot.coverage_end.timestamp())
        assert request.headers["Authorization"] == "Bearer synthetic-admin-key"
    assert seen[1].url.params["page"] == "next"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
async def test_http_errors_return_unavailable(monkeypatch, status):
    configured(monkeypatch)
    client_mock(monkeypatch, [(status, {"error": {"message": "SECRET"}})])
    state, snapshot = await costs.OpenAICostsMonitor().get(now=NOW)
    assert (state, snapshot) == ("UNAVAILABLE", None)


@pytest.mark.asyncio
async def test_timeouts_return_unavailable_and_no_secrets(monkeypatch, caplog):
    configured(monkeypatch)
    client_mock(monkeypatch, [httpx.ReadTimeout("synthetic-admin-key; private payload")])
    state, _ = await costs.OpenAICostsMonitor().get(now=NOW)
    assert state == "UNAVAILABLE"
    assert "synthetic-admin-key" not in caplog.text
    assert "private payload" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", [
    lambda p: p.update(object="other"),
    lambda p: p["data"][0]["results"][0]["amount"].update(currency="eur"),
    lambda p: p["data"][0]["results"][0].update(project_id="proj_unrelated"),
    lambda p: p["data"][0]["results"][0].update(project_id=None),
    lambda p: p["data"][0]["results"][0].update(amount=None),
    lambda p: p["data"][0]["results"][0]["amount"].update(value="NaN"),
    lambda p: p["data"][0].update(start_time=0),
    lambda p: p.update(has_more=True, next_page=None),
])
async def test_malformed_provider_data_fails_closed(monkeypatch, mutation):
    configured(monkeypatch)
    payload = page([bucket(0), bucket(1)])
    mutation(payload)
    client_mock(monkeypatch, [(200, payload)])
    assert (await costs.OpenAICostsMonitor().get(now=NOW))[0] == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_missing_daily_bucket_and_cyclic_page_are_unavailable(monkeypatch):
    configured(monkeypatch)
    client_mock(monkeypatch, [(200, page([bucket(1)]))])
    assert (await costs.OpenAICostsMonitor().get(now=NOW))[0] == "UNAVAILABLE"
    client_mock(monkeypatch, [(200, page([], more=True, cursor="again"))])
    assert (await costs.OpenAICostsMonitor().get(now=NOW))[0] == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_success_cache_hour_ttl_and_utc_day_rollover(monkeypatch):
    configured(monkeypatch)
    seen = client_mock(monkeypatch, [(200, page([bucket(0), bucket(1)]))])
    monitor = costs.OpenAICostsMonitor()
    assert (await monitor.get(now=NOW))[0] == "OK"
    assert (await monitor.get(now=NOW + timedelta(minutes=59)))[0] == "OK"
    assert len(seen) == 1
    assert (await monitor.get(now=NOW + timedelta(hours=1)))[0] == "OK"
    assert len(seen) == 2
    # New UTC day requires its own daily bucket, not stale cached totals.
    assert (await monitor.get(now=NOW + timedelta(days=1)))[0] == "UNAVAILABLE"


def test_utc_month_transition_uses_new_calendar_month():
    nov_start, nov_end = costs._window(
        datetime(2026, 11, 1, 0, 1, tzinfo=timezone.utc)
    )
    assert nov_start == datetime(2026, 11, 1, tzinfo=timezone.utc)
    assert nov_end == nov_start
    oct_start, oct_end = costs._window(
        datetime(2026, 10, 31, 23, 59, tzinfo=timezone.utc)
    )
    assert oct_start == START
    assert oct_end == datetime(2026, 10, 31, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_concurrent_open_coalesces_fetch_and_first_day_has_no_data(monkeypatch):
    configured(monkeypatch)
    first_day = START + timedelta(hours=8)
    assert (await costs.OpenAICostsMonitor().get(now=first_day))[0] == "UNAVAILABLE"
    seen = client_mock(monkeypatch, [(200, page([bucket(0), bucket(1)]))])
    monitor = costs.OpenAICostsMonitor()
    results = await asyncio.gather(*(monitor.get(now=NOW) for _ in range(5)))
    assert all(state == "OK" for state, _ in results)
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_internal_ledger_partition_and_matching_window(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'costs.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_USD", "2.50")
    try:
        async with sessions.begin() as session:
            for i, (status, actual, reserved, day) in enumerate([
                ("settled", Decimal("0.10"), Decimal("0.50"), 0),
                ("reserved", None, Decimal("0.30"), 1),
                ("conservative", None, Decimal("0.40"), 1),
                ("cap_breach", Decimal("0.12"), Decimal("0.10"), 2),
            ]):
                session.add(OpenAIBudgetReservation(
                    id=str(i), month_start=date(2026, 10, 1), model="gpt-6-luna",
                    call_type="event_analysis", reserved_usd=reserved,
                    input_rate_usd_per_million=Decimal("0.25"),
                    output_rate_usd_per_million=Decimal("0.75"),
                    actual_usd=actual, status=status,
                    created_at=START + timedelta(days=day),
                ))
        summary = await costs.read_internal_costs(
            sessions, start=START, end=START + timedelta(days=2),
        )
        assert summary.used == Decimal("0.92")
        assert summary.settled == Decimal("0.22")
        assert summary.pending == Decimal("0.30")
        assert summary.conservative == Decimal("0.40")
        assert summary.comparable_used == Decimal("0.80")
        assert summary.remaining == Decimal("1.58")
        assert summary.cap_breach is True
        screen = costs.format_costs_screen(
            now=NOW, state="OK",
            provider=costs.ProviderCosts(PROJECT, START, START + timedelta(days=2),
                                        NOW, Decimal("0.60")),
            internal=summary, scope_confirmed=True,
        )
        assert "Difference (provider - local, same window): $-0.2000" in screen
        assert "Current UTC day is excluded" in screen
        assert "WARNING" in screen
    finally:
        await engine.dispose()


def test_no_difference_without_scope_confirmation_or_coverage():
    provider = costs.ProviderCosts(PROJECT, START, START + timedelta(days=2),
                                   NOW, Decimal("0.5"))
    internal = costs.InternalCosts(
        used=Decimal("1"), limit=Decimal("2.5"), remaining=Decimal("1.5"),
        settled=Decimal("1"), pending=Decimal("0"), conservative=Decimal("0"),
        cap_breach=False, comparable_used=Decimal("1"),
    )
    for verified in (False, True):
        screen = costs.format_costs_screen(
            now=NOW, state="UNAVAILABLE" if verified else "OK",
            provider=provider if not verified else None,
            internal=internal, scope_confirmed=verified,
        )
        assert "Difference: NOT COMPARABLE" in screen


@pytest.mark.asyncio
async def test_admin_callback_rejects_unauthorized_and_nonprivate(monkeypatch):
    from bot.handlers.callbacks import button_router
    admin = import_module("bot.handlers.admin")

    def update(chat_type):
        query = SimpleNamespace(
            data="admin:openai_costs",
            from_user=SimpleNamespace(id=20),
            message=SimpleNamespace(
                message_id=21, chat_id=20,
                chat=SimpleNamespace(type=chat_type),
                reply_text=AsyncMock(),
            ),
            answer=AsyncMock(), edit_message_text=AsyncMock(),
        )
        return SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(
            type=chat_type, id=20
        ), effective_user=query.from_user), SimpleNamespace(
            user_data={}, application=SimpleNamespace(), bot=SimpleNamespace()
        )
    builder = AsyncMock(return_value="secret cost screen")
    monkeypatch.setattr(admin, "_build_admin_openai_costs_text", builder)
    monkeypatch.setattr("bot.handlers.is_admin_user", AsyncMock(return_value=False))
    incoming, context = update("private")
    await button_router(incoming, context)
    builder.assert_not_awaited()
    incoming, context = update("group")
    monkeypatch.setattr("bot.handlers.is_admin_user", AsyncMock(return_value=True))
    await button_router(incoming, context)
    builder.assert_not_awaited()
    incoming.callback_query.edit_message_text.assert_awaited()
    incoming, context = update("private")
    await button_router(incoming, context)
    builder.assert_awaited_once()
    assert "secret cost screen" in str(incoming.callback_query.edit_message_text.await_args)


@pytest.mark.asyncio
async def test_monitor_never_changes_admission_guard(monkeypatch):
    configured(monkeypatch)
    monkeypatch.setenv("OPENAI_MONTHLY_BUDGET_USD", "0")
    client_mock(monkeypatch, [(200, page([bucket(0), bucket(1)]))])
    assert (await costs.OpenAICostsMonitor().get(now=NOW))[0] == "OK"
    from bot.services.llm.openai_budget import OpenAIBudgetExhausted
    with pytest.raises(OpenAIBudgetExhausted, match="invalid_cap"):
        await OpenAIBudget().reserve(
            model="gpt-6-luna", call_type="daily_report",
            input_chars=1, max_tokens=1,
        )
