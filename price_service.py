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


async def get_coin_price(symbol: str = DEFAULT_SYMBOL) -> tuple[float, float, str]:
    """Get current coin price and 24h change from CoinGecko."""
    normalized_symbol = symbol.lower()

    if normalized_symbol not in COIN_SYMBOL_TO_ID:
        supported = ", ".join(COIN_SYMBOL_TO_ID.keys())
        raise ValueError(f"Unsupported coin symbol '{symbol}'. Supported: {supported}")

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

    return price, change_24h, normalized_symbol


async def get_btc_price() -> tuple[float, float]:
    """Backward-compatible helper for BTC-specific callers."""
    price, change_24h, _ = await get_coin_price("btc")
    return price, change_24h
