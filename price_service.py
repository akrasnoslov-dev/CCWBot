import time
import logging

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
logger = logging.getLogger(__name__)


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

    if not isinstance(data, dict):
        raise ValueError("Unexpected CoinGecko response format.")

    coin_data = data.get(coin_id)
    if coin_data is None and normalized_symbol == "ton":
        logger.warning(
            "CoinGecko simple price response missing expected id for TON fallback. "
            "expected_id=%s returned_keys=%s",
            coin_id,
            list(data.keys()),
        )
        coin_data = await _fetch_ton_fallback_coin_data()
    if not isinstance(coin_data, dict):
        raise ValueError(f"CoinGecko response did not include expected coin data for '{coin_id}'.")

    price = coin_data.get("usd")
    if price is None:
        raise ValueError(f"CoinGecko response did not include USD price for '{coin_id}'.")
    price = float(price)

    change_24h = coin_data.get("usd_24h_change")
    if change_24h is None:
        change_24h = 0.0
    change_24h = float(change_24h)
    _set_cached_price(normalized_symbol, price, change_24h)

    return price, change_24h, normalized_symbol


async def get_btc_price() -> tuple[float, float]:
    """Backward-compatible helper for BTC-specific callers."""
    price, change_24h, _ = await get_coin_price("btc")
    return price, change_24h


async def _fetch_ton_fallback_coin_data() -> dict | None:
    """Fallback fetch for TON when /simple/price ids=toncoin does not include toncoin."""
    url = "https://api.coingecko.com/api/v3/simple/price"
    timeout = 10

    async with httpx.AsyncClient() as client:
        # First fallback: symbol-based lookup.
        symbol_params = {
            "symbols": "ton",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        }
        symbol_response = await client.get(url, params=symbol_params, timeout=timeout)
        if symbol_response.status_code == 429:
            raise CoinGeckoRateLimitError("CoinGecko rate limit reached")
        symbol_response.raise_for_status()
        symbol_data = symbol_response.json()

        symbol_coin_data = _extract_ton_coin_data_from_simple_price(symbol_data)
        if isinstance(symbol_coin_data, dict):
            logger.info("TON fallback succeeded via CoinGecko symbols=ton.")
            return symbol_coin_data

        logger.warning(
            "TON fallback via symbols=ton failed. returned_keys=%s",
            list(symbol_data.keys()) if isinstance(symbol_data, dict) else type(symbol_data).__name__,
        )

        # Second fallback: name-based lookup.
        name_params = {
            "names": "Toncoin",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        }
        name_response = await client.get(url, params=name_params, timeout=timeout)
        if name_response.status_code == 429:
            raise CoinGeckoRateLimitError("CoinGecko rate limit reached")
        name_response.raise_for_status()
        name_data = name_response.json()

        name_coin_data = _extract_ton_coin_data_from_simple_price(name_data)
        if isinstance(name_coin_data, dict):
            logger.info("TON fallback succeeded via CoinGecko names=Toncoin.")
            return name_coin_data

        logger.warning(
            "TON fallback via names=Toncoin failed. returned_keys=%s",
            list(name_data.keys()) if isinstance(name_data, dict) else type(name_data).__name__,
        )
        return None


def _extract_ton_coin_data_from_simple_price(payload: dict) -> dict | None:
    if not isinstance(payload, dict):
        return None

    # Prefer explicit toncoin result when present.
    preferred = payload.get("toncoin")
    if isinstance(preferred, dict) and preferred.get("usd") is not None:
        return preferred

    # For symbols/names lookups, CoinGecko may return one or multiple ids.
    candidates: list[tuple[str, dict]] = []
    for coin_id, coin_data in payload.items():
        if not isinstance(coin_data, dict):
            continue
        if coin_data.get("usd") is None:
            continue
        candidates.append((str(coin_id).lower(), coin_data))

    if not candidates:
        return None

    for coin_id, coin_data in candidates:
        if coin_id == "toncoin":
            return coin_data

    for coin_id, coin_data in candidates:
        if coin_id == "the-open-network" or ("ton" in coin_id and "ton" != coin_id):
            return coin_data

    for coin_id, coin_data in candidates:
        if coin_id == "ton":
            return coin_data

    return candidates[0][1]
