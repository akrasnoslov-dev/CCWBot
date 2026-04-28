import httpx


async def get_btc_price() -> tuple[float, float]:
    """Get current BTC price and 24h change from CoinGecko."""
    url = "https://api.coingecko.com/api/v3/simple/price"

    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

    btc_price = data["bitcoin"]["usd"]
    change_24h = data["bitcoin"].get("usd_24h_change", 0)

    return btc_price, change_24h
