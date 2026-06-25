import asyncio
import time
from unittest.mock import AsyncMock

import pytest

import bot.services.price_service as price_service
from bot.domain.supported_coins import ACTIVE_SYMBOLS


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FakeClient:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.calls = 0

    async def get(self, url, params, timeout):
        self.calls += 1
        return self.responses.pop(0)


def clear_price_caches() -> None:
    price_service._PRICE_CACHE.clear()
    price_service._BTC_MARKET_CACHE = None


@pytest.fixture(autouse=True)
def clean_price_caches():
    clear_price_caches()
    yield
    clear_price_caches()


@pytest.mark.asyncio
async def test_get_coin_price_returns_cached_value(monkeypatch):
    price_service._set_cached_price("btc", 50000.0, 1.5)
    get_with_retry = AsyncMock(side_effect=AssertionError("HTTP should not be called"))
    monkeypatch.setattr(price_service, "_get_with_retry", get_with_retry)

    result = await price_service.get_coin_price("btc")

    assert result == (50000.0, 1.5, "btc")
    get_with_retry.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_coin_price_cache_expires(monkeypatch):
    price_service._set_cached_price(
        "btc",
        50000.0,
        1.5,
        cached_at=time.time() - price_service.PRICE_CACHE_TTL_SECONDS - 1,
    )
    get_with_retry = AsyncMock(return_value={"bitcoin": {"usd": 51000.0, "usd_24h_change": 2.0}})
    monkeypatch.setattr(price_service, "_get_with_retry", get_with_retry)

    result = await price_service.get_coin_price("btc")

    assert result == (51000.0, 2.0, "btc")
    get_with_retry.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_btc_market_data_does_not_request_unreliable_simple_price_7d(monkeypatch):
    get_with_retry = AsyncMock(return_value={"bitcoin": {"usd": 51000.0, "usd_24h_change": 2.0}})
    monkeypatch.setattr(price_service, "_get_with_retry", get_with_retry)

    result = await price_service.get_btc_market_data()

    assert result == (51000.0, 2.0, None)
    requested_params = get_with_retry.await_args.args[2]
    assert requested_params["include_24hr_change"] == "true"
    assert "include_7d_change" not in requested_params


@pytest.mark.asyncio
async def test_get_coin_price_unsupported_symbol_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported coin symbol"):
        await price_service.get_coin_price("usdt")


def test_coin_mapping_uses_active_symbols_only():
    assert ACTIVE_SYMBOLS == ("btc", "eth", "ton", "sol")
    assert price_service.COIN_SYMBOL_TO_ID == {
        "btc": "bitcoin",
        "eth": "ethereum",
        "ton": "the-open-network",
        "sol": "solana",
    }


@pytest.mark.asyncio
async def test_get_coin_price_accepts_gram_alias(monkeypatch):
    get_with_retry = AsyncMock(
        return_value={"the-open-network": {"usd": 1.75, "usd_24h_change": 3.2}}
    )
    monkeypatch.setattr(price_service, "_get_with_retry", get_with_retry)

    result = await price_service.get_coin_price("gram")

    requested_params = get_with_retry.await_args.args[2]
    assert requested_params == {
        "ids": "the-open-network",
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }
    assert result == (1.75, 3.2, "ton")


@pytest.mark.asyncio
async def test_get_coin_price_429_triggers_retry(monkeypatch):
    monkeypatch.setattr(price_service.asyncio, "sleep", AsyncMock())

    class FakeAsyncClient:
        def __init__(self):
            self.client = FakeClient(
                [
                    FakeResponse(429),
                    FakeResponse(
                        200,
                        {"bitcoin": {"usd": 52000.0, "usd_24h_change": 2.5}},
                    ),
                ]
            )

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    fake_client_context = FakeAsyncClient()
    monkeypatch.setattr(price_service.httpx, "AsyncClient", lambda: fake_client_context)

    result = await price_service.get_coin_price("btc")

    assert result == (52000.0, 2.5, "btc")
    assert fake_client_context.client.calls == 2
    price_service.asyncio.sleep.assert_awaited_once_with(5)


@pytest.mark.asyncio
async def test_get_coin_market_data_batch_builds_supported_ids(monkeypatch):
    get_with_retry = AsyncMock(
        return_value={
            "bitcoin": {"usd": 60000.0, "usd_24h_change": 1.2},
            "ethereum": {"usd": 3000.0, "usd_24h_change": -0.5},
        }
    )
    monkeypatch.setattr(price_service, "_get_with_retry", get_with_retry)

    result = await price_service.get_coin_market_data_batch(["btc", "eth"])

    requested_params = get_with_retry.await_args.args[2]
    assert requested_params["ids"] == "bitcoin,ethereum"
    assert "tether" not in requested_params["ids"]
    assert result == {
        "btc": {"price": 60000.0, "change_24h": 1.2, "change_7d": None},
        "eth": {"price": 3000.0, "change_24h": -0.5, "change_7d": None},
    }


@pytest.mark.asyncio
async def test_get_coin_market_data_batch_uses_current_gram_coingecko_id(monkeypatch):
    get_with_retry = AsyncMock(
        return_value={"the-open-network": {"usd": 1.72, "usd_24h_change": -0.4}}
    )
    monkeypatch.setattr(price_service, "_get_with_retry", get_with_retry)

    result = await price_service.get_coin_market_data_batch(["ton"])

    requested_params = get_with_retry.await_args.args[2]
    assert requested_params["ids"] == "the-open-network"
    assert "toncoin" not in requested_params["ids"]
    assert result == {"ton": {"price": 1.72, "change_24h": -0.4, "change_7d": None}}


@pytest.mark.asyncio
async def test_get_coin_market_data_batch_accepts_gram_alias(monkeypatch):
    get_with_retry = AsyncMock(
        return_value={"the-open-network": {"usd": 1.72, "usd_24h_change": -0.4}}
    )
    monkeypatch.setattr(price_service, "_get_with_retry", get_with_retry)

    result = await price_service.get_coin_market_data_batch(["gram"])

    requested_params = get_with_retry.await_args.args[2]
    assert requested_params["ids"] == "the-open-network"
    assert result == {"ton": {"price": 1.72, "change_24h": -0.4, "change_7d": None}}


@pytest.mark.asyncio
async def test_get_coin_market_data_batch_skips_missing_symbol(monkeypatch):
    get_with_retry = AsyncMock(return_value={"bitcoin": {"usd": 60000.0}})
    monkeypatch.setattr(price_service, "_get_with_retry", get_with_retry)

    result = await price_service.get_coin_market_data_batch(["btc", "eth"])

    assert result == {"btc": {"price": 60000.0, "change_24h": 0.0, "change_7d": None}}


@pytest.mark.asyncio
async def test_get_report_market_data_batch_uses_markets_endpoint(monkeypatch):
    get_with_retry = AsyncMock(
        return_value=[
            {
                "id": "bitcoin",
                "current_price": 60000.0,
                "price_change_percentage_1h_in_currency": 0.2,
                "price_change_percentage_24h_in_currency": 1.2,
                "price_change_percentage_7d_in_currency": -3.5,
                "total_volume": 28000000000,
                "market_cap": 1180000000000,
                "market_cap_rank": 1,
                "sparkline_in_7d": {"price": [59000.0, 61000.0, 60000.0]},
            },
            {
                "id": "ethereum",
                "current_price": 3000.0,
                "price_change_percentage_24h_in_currency": -0.5,
                "sparkline_in_7d": {"price": []},
            },
        ]
    )
    monkeypatch.setattr(price_service, "_get_with_retry", get_with_retry)

    result = await price_service.get_report_market_data_batch(["btc", "eth"])

    requested_url = get_with_retry.await_args.args[1]
    requested_params = get_with_retry.await_args.args[2]
    assert requested_url.endswith("/coins/markets")
    assert requested_params == {
        "ids": "bitcoin,ethereum",
        "vs_currency": "usd",
        "price_change_percentage": "1h,24h,7d",
        "sparkline": "true",
        "per_page": "2",
    }
    assert get_with_retry.await_args.kwargs["allow_stale_price_fallback"] is False
    assert result == {
        "btc": {
            "price": 60000.0,
            "change_1h": 0.2,
            "change_24h": 1.2,
            "change_7d": -3.5,
            "volume_24h": 28000000000.0,
            "market_cap": 1180000000000.0,
            "rank": 1,
            "sparkline_7d": [59000.0, 61000.0, 60000.0],
            "weekly_high": 61000.0,
            "weekly_low": 59000.0,
            "range_position": 0.5,
        },
        "eth": {
            "price": 3000.0,
            "change_1h": None,
            "change_24h": -0.5,
            "change_7d": None,
            "volume_24h": None,
            "market_cap": None,
            "rank": None,
            "sparkline_7d": [],
            "weekly_high": None,
            "weekly_low": None,
            "range_position": None,
        },
    }


@pytest.mark.asyncio
async def test_get_report_market_data_batch_keeps_btc_alert_cache_unchanged(monkeypatch):
    price_service._BTC_MARKET_CACHE = (59000.0, -1.0, None, time.time())
    price_service._set_cached_price("btc", 58000.0, -2.0, cached_at=0)
    get_with_retry = AsyncMock(
        return_value=[
            {
                "id": "bitcoin",
                "current_price": 60000.0,
                "price_change_percentage_24h_in_currency": 1.2,
            }
        ]
    )
    monkeypatch.setattr(price_service, "_get_with_retry", get_with_retry)

    await price_service.get_report_market_data_batch(["btc"])

    assert price_service._BTC_MARKET_CACHE is not None
    assert price_service._BTC_MARKET_CACHE[:3] == (59000.0, -1.0, None)
    assert price_service._PRICE_CACHE["btc"][:2] == (58000.0, -2.0)


def test_ton_simple_price_extractor_accepts_only_current_gram_id():
    payload = {
        "toncoin": {"usd": 0.38, "usd_24h_change": -77.0},
        "ton": {"usd": 0.37, "usd_24h_change": -78.0},
        "the-open-network": {"usd": 1.72, "usd_24h_change": 2.0},
    }

    assert price_service._extract_ton_coin_data_from_simple_price(payload) == {
        "usd": 1.72,
        "usd_24h_change": 2.0,
    }


def test_ton_simple_price_extractor_rejects_arbitrary_symbol_candidates():
    payload = {
        "toncoin": {"usd": 0.38, "usd_24h_change": -77.0},
        "ton": {"usd": 0.37, "usd_24h_change": -78.0},
        "some-ton-candidate": {"usd": 0.39, "usd_24h_change": -76.0},
    }

    assert price_service._extract_ton_coin_data_from_simple_price(payload) is None


def test_get_with_retry_returns_stale_cache_after_429_retries():
    price_service._set_cached_price("btc", 50000.0, 1.5, cached_at=0)
    client = FakeClient(
        [
            FakeResponse(429),
            FakeResponse(429),
            FakeResponse(429),
        ]
    )

    payload = asyncio.run(
        price_service._get_with_retry(
            client,
            "https://api.coingecko.com/api/v3/simple/price",
            {
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
            max_retries=2,
            base_delay=0,
        )
    )

    assert client.calls == 3
    assert payload == {
        "bitcoin": {
            "usd": 50000.0,
            "usd_24h_change": 1.5,
        }
    }
    assert price_service._PRICE_CACHE["btc"][2] == 0


def test_get_with_retry_can_disable_stale_cache_after_429_retries():
    price_service._set_cached_price("btc", 50000.0, 1.5, cached_at=0)
    client = FakeClient(
        [
            FakeResponse(429),
            FakeResponse(429),
            FakeResponse(429),
        ]
    )

    with pytest.raises(price_service.CoinGeckoRateLimitError):
        asyncio.run(
            price_service._get_with_retry(
                client,
                "https://api.coingecko.com/api/v3/coins/markets",
                {
                    "ids": "bitcoin",
                    "vs_currency": "usd",
                    "price_change_percentage": "1h,24h,7d",
                    "sparkline": "true",
                },
                max_retries=2,
                base_delay=0,
                allow_stale_price_fallback=False,
            )
        )

    assert client.calls == 3
    assert price_service._PRICE_CACHE["btc"][2] == 0


def test_btc_market_cache_hit_syncs_regular_btc_cache():
    cached_at = time.time()
    price_service._BTC_MARKET_CACHE = (60000.0, 2.5, 4.0, cached_at)
    price_service._set_cached_price("btc", 59000.0, -1.0)

    result = asyncio.run(price_service.get_btc_market_data())

    assert result == (60000.0, 2.5, 4.0)
    assert price_service._PRICE_CACHE["btc"] == (60000.0, 2.5, cached_at)
