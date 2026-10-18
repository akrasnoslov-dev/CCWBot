"""Report availability must survive exhausted LLM providers, but not unrelated failures."""

from unittest.mock import AsyncMock

import pytest

import bot.reports as reports
from bot.db.database import utc_now
from bot.services.llm.errors import (
    AIProviderRateLimitError,
    AllProvidersFailedError,
    LLMRateLimitBackoffActive,
)


def _verified_payload(report_type: str) -> dict:
    return {
        "report_type": report_type,
        "active_symbols": ["BTC", "ETH", "GRAM", "SOL"],
        "coins": [
            {
                "symbol": symbol,
                "name": symbol,
                "price": price,
                "change_24h_percent": 1.5,
                "change_7d_percent": 3.0,
            }
            for symbol, price in (
                ("BTC", 80000.0), ("ETH", 2400.0),
                ("GRAM", 1.4), ("SOL", 104.0),
            )
        ],
        "weekly_context": {"timeline": ["Tracked market observations only."]},
        "market_news": [],
        "coin_news": {},
        "news_fallback": "No relevant verified news.",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("report_type", "error"),
    [
        ("daily", AllProvidersFailedError("fallback chain exhausted")),
        ("weekly", AIProviderRateLimitError("rate limited", provider="groq")),
        (
            "daily",
            LLMRateLimitBackoffActive(
                provider="gemini", model="test-model", limited_until=utc_now(),
            ),
        ),
    ],
)
async def test_exhausted_provider_chain_uses_verified_data_fallback(
    monkeypatch, report_type, error,
):
    payload = _verified_payload(report_type)
    market = AsyncMock(return_value=(payload, []))
    query = AsyncMock(side_effect=error)
    remember = AsyncMock()
    persist = AsyncMock(side_effect=lambda **kw: kw)
    monkeypatch.setattr(reports, "_build_market_report_input", market)
    monkeypatch.setattr(reports, "ask_market_report_raw", query)
    monkeypatch.setattr(reports, "remember_news_context", remember)
    monkeypatch.setattr(reports, "_save_or_remember_report", persist)
    monkeypatch.setattr(
        reports, "_build_report_telegram_message",
        lambda *, report_type, input_payload, decision: (
            f"{decision.title}: verified {len(decision.coin_cards)} coins. "
            "Not financial advice."
        ),
    )

    result = await reports.generate_report_cache(report_type)

    assert result["status"] == "completed"
    assert result["provider"] == reports.DETERMINISTIC_REPORT_PROVIDER
    assert result["telegram_message"].endswith("Not financial advice.")
    assert result["error_message"].startswith("deterministic fallback after ")
    assert result["llm_operation_id"]
    assert query.await_count == 1
    assert market.await_count == 1
    assert remember.await_count == 1


@pytest.mark.asyncio
async def test_unexpected_report_programming_error_does_not_become_fake_success(monkeypatch):
    monkeypatch.setattr(
        reports, "_build_market_report_input",
        AsyncMock(return_value=(_verified_payload("daily"), [])),
    )
    monkeypatch.setattr(
        reports, "ask_market_report_raw",
        AsyncMock(side_effect=RuntimeError("unexpected parser error")),
    )
    persist = AsyncMock(side_effect=lambda **kw: kw)
    monkeypatch.setattr(reports, "_save_or_remember_report", persist)
    result = await reports.generate_report_cache("daily")
    assert result["status"] == "failed"
    assert result["telegram_message"] is None
    assert result["provider"] != reports.DETERMINISTIC_REPORT_PROVIDER
