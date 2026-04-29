import time

import httpx


class CoinGeckoRateLimitError(Exception):
    """Raised when CoinGecko returns HTTP 429."""


COIN_SYMBOL_TO_ID = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "ton": "toncoin",
    "usdt": "tether",
}

DEFAULT_SYMBOL = "btc"
CACHE_TTL_SECONDS = 60
_PRICE_CACHE: dict[str, tuple[float, float, float]] = {}


def _get_cached_price(normalized_symbol: str) -> tuple[float, float, str] | None:
    cached = _PRICE_CACHE.get(normalized_symbol)
    if not cached:
        return None

    price, change_24h, cached_at = cached
    if time.time() - cached_at <= CACHE_TTL_SECONDS:
        return price, change_24h, normalized_symbol

    _PRICE_CACHE.pop(normalized_symbol, None)
    return None


def _set_cached_price(normalized_symbol: str, price: float, change_24h: float) -> None:
    _PRICE_CACHE[normalized_symbol] = (price, change_24h, time.time())


async def get_coin_price(symbol: str = DEFAULT_SYMBOL) -> tuple[float, float, str]:
    """Get current coin price and 24h change from CoinGecko."""
    normalized_symbol = symbol.lower()

    if normalized_symbol not in COIN_SYMBOL_TO_ID:
        supported = ", ".join(COIN_SYMBOL_TO_ID.keys())
        raise ValueError(f"Unsupported coin symbol '{symbol}'. Supported: {supported}")

    cached = _get_cached_price(normalized_symbol)
    if cached:
        return cached

    coin_id = COIN_SYMBOL_TO_ID[normalized_symbol]
    url = "https://api.coingecko.com/api/v3/simple/price"

    params = {
        "ids": coin_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10)
        if response.status_code == 429:
            raise CoinGeckoRateLimitError("CoinGecko rate limit reached")
        response.raise_for_status()
        data = response.json()

    coin_data = data[coin_id]
    price = coin_data["usd"]
    change_24h = coin_data.get("usd_24h_change", 0)
    _set_cached_price(normalized_symbol, price, change_24h)

    return price, change_24h, normalized_symbol


async def get_btc_price() -> tuple[float, float]:
    """Backward-compatible helper for BTC-specific callers."""
    price, change_24h, _ = await get_coin_price("btc")
    return price, change_24h
