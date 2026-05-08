import asyncio
import time
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import price_service


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


def test_get_with_retry_returns_stale_cache_after_429_retries():
    clear_price_caches()
    try:
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
    finally:
        clear_price_caches()


def test_btc_market_cache_hit_syncs_regular_btc_cache():
    clear_price_caches()
    try:
        cached_at = time.time()
        price_service._BTC_MARKET_CACHE = (60000.0, 2.5, 4.0, cached_at)
        price_service._set_cached_price("btc", 59000.0, -1.0)

        result = asyncio.run(price_service.get_btc_market_data())

        assert result == (60000.0, 2.5, 4.0)
        assert price_service._PRICE_CACHE["btc"] == (60000.0, 2.5, cached_at)
    finally:
        clear_price_caches()
