import asyncio
import logging
import time

import httpx

from config import PRICE_CACHE_TTL_SECONDS


class CoinGeckoRateLimitError(Exception):
    """Raised when CoinGecko returns HTTP 429."""


# Keep this mapping intentionally small and explicit.
# Only these symbols are supported in command handlers and callbacks.
COIN_SYMBOL_TO_ID = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "ton": "toncoin",
    "usdt": "tether",
}

DEFAULT_SYMBOL = "btc"
_PRICE_CACHE: dict[str, tuple[float, float, float]] = {}
_BTC_MARKET_CACHE: tuple[float, float, float | None, float] | None = None
logger = logging.getLogger(__name__)
_COIN_ID_TO_SYMBOL = {coin_id: symbol for symbol, coin_id in COIN_SYMBOL_TO_ID.items()}


def _get_cached_price(normalized_symbol: str) -> tuple[float, float, str] | None:
    """Return cached symbol price when TTL is still valid.

    Caching reduces CoinGecko API traffic and helps avoid 429 responses.
    """
    cached = _PRICE_CACHE.get(normalized_symbol)
    if not cached:
        return None

    price, change_24h, cached_at = cached
    if time.time() - cached_at <= PRICE_CACHE_TTL_SECONDS:
        return price, change_24h, normalized_symbol

    return None


def _set_cached_price(
    normalized_symbol: str,
    price: float,
    change_24h: float,
    cached_at: float | None = None,
) -> None:
    _PRICE_CACHE[normalized_symbol] = (
        price,
        change_24h,
        time.time() if cached_at is None else cached_at,
    )


def _coingecko_bool(params: dict, key: str) -> bool:
    return str(params.get(key, "")).lower() == "true"


def _get_stale_cached_price(normalized_symbol: str) -> tuple[float, float] | None:
    cached = _PRICE_CACHE.get(normalized_symbol)
    if not cached:
        return None
    price, change_24h, _ = cached
    return price, change_24h


def _build_stale_price_payload(params: dict) -> dict | None:
    """Build a CoinGecko-like payload from expired in-memory cache entries."""
    requested_symbols: list[str] = []
    ids = str(params.get("ids") or "")
    if ids:
        requested_symbols.extend(
            _COIN_ID_TO_SYMBOL[coin_id.strip()]
            for coin_id in ids.split(",")
            if coin_id.strip() in _COIN_ID_TO_SYMBOL
        )

    symbols = str(params.get("symbols") or "")
    if symbols:
        requested_symbols.extend(
            symbol.strip().lower()
            for symbol in symbols.split(",")
            if symbol.strip().lower() in COIN_SYMBOL_TO_ID
        )

    names = str(params.get("names") or "").lower()
    if "toncoin" in names:
        requested_symbols.append("ton")

    payload: dict[str, dict[str, float]] = {}
    for symbol in dict.fromkeys(requested_symbols):
        stale_price = _get_stale_cached_price(symbol)
        if stale_price is None:
            continue

        price, change_24h = stale_price
        coin_data: dict[str, float] = {"usd": price}
        if _coingecko_bool(params, "include_24hr_change"):
            coin_data["usd_24h_change"] = change_24h
        payload[COIN_SYMBOL_TO_ID[symbol]] = coin_data

    return payload or None


async def _get_with_retry(
    client,
    url,
    params,
    max_retries: int = 3,
    base_delay: int = 5,
) -> dict:
    """Fetch CoinGecko data, retrying 429s and falling back to stale cache."""
    last_status_code = None
    for attempt in range(max_retries + 1):
        response = await client.get(url, params=params, timeout=10)
        last_status_code = response.status_code
        if response.status_code != 429:
            response.raise_for_status()
            return response.json()

        if attempt < max_retries:
            delay = base_delay * (2**attempt)
            logger.warning(
                "CoinGecko returned 429. Retrying after %s seconds. attempt=%s max_retries=%s",
                delay,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(delay)

    stale_payload = _build_stale_price_payload(params)
    if stale_payload is not None:
        logger.warning(
            "CoinGecko returned %s after retries. Returning stale cached price data.",
            last_status_code,
        )
        return stale_payload

    raise CoinGeckoRateLimitError("CoinGecko rate limit reached and no stale cache is available")


def _sync_btc_price_cache(
    price: float,
    change_24h: float,
    cached_at: float | None = None,
) -> None:
    cached = _PRICE_CACHE.get("btc")
    if cached is None or cached[0] != price or cached[1] != change_24h:
        _set_cached_price("btc", price, change_24h, cached_at)


async def warm_up_price_cache() -> None:
    """Populate price cache from persisted runtime state on startup."""
    from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL
    from database import get_price_state
    from storage import load_state

    warmed_symbols: list[str] = []
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            for symbol in COIN_SYMBOL_TO_ID:
                row = await get_price_state(session, symbol)
                if row is None or row.last_price is None:
                    continue
                change_24h = row.last_24h_change if row.last_24h_change is not None else 0.0
                _set_cached_price(symbol, float(row.last_price), float(change_24h), cached_at=0)
                warmed_symbols.append(symbol)
    else:
        state = load_state()
        last_price = state.get("last_price")
        if last_price is not None:
            change_24h = state.get("last_24h_change") or 0.0
            _set_cached_price(DEFAULT_SYMBOL, float(last_price), float(change_24h), cached_at=0)
            warmed_symbols.append(DEFAULT_SYMBOL)

    if warmed_symbols:
        logger.info(
            "Warmed price cache from persisted state for symbols: %s",
            ", ".join(sorted(warmed_symbols)),
        )


async def get_coin_price(symbol: str = DEFAULT_SYMBOL) -> tuple[float, float, str]:
    """Get current coin price and 24h change from CoinGecko.

    Unsupported symbols raise ValueError so callers can return a clear user message.
    """
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
        data = await _get_with_retry(client, url, params)

    if not isinstance(data, dict):
        raise ValueError("Unexpected CoinGecko response format.")

    coin_data = data.get(coin_id)
    # TON has a fallback because CoinGecko occasionally omits toncoin in ids-based responses.
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


async def get_btc_market_data() -> tuple[float, float, float | None]:
    """Get BTC price and 24h change.

    CoinGecko's simple price endpoint does not reliably return a BTC 7d
    change, so this intentionally leaves change_7d unset until a future
    endpoint-specific implementation is added.
    """
    global _BTC_MARKET_CACHE

    if _BTC_MARKET_CACHE is not None:
        price, change_24h, change_7d, cached_at = _BTC_MARKET_CACHE
        if time.time() - cached_at <= PRICE_CACHE_TTL_SECONDS:
            _sync_btc_price_cache(price, change_24h, cached_at)
            return price, change_24h, change_7d

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": COIN_SYMBOL_TO_ID["btc"],
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    async with httpx.AsyncClient() as client:
        data = await _get_with_retry(client, url, params)

    if not isinstance(data, dict):
        raise ValueError("Unexpected CoinGecko response format.")

    coin_data = data.get("bitcoin")
    if not isinstance(coin_data, dict):
        raise ValueError("CoinGecko response did not include expected coin data for 'bitcoin'.")

    price = float(coin_data["usd"])
    change_24h_raw = coin_data.get("usd_24h_change")
    change_24h = float(change_24h_raw) if change_24h_raw is not None else 0.0
    change_7d = None

    cached_at = time.time()
    _sync_btc_price_cache(price, change_24h, cached_at)
    _BTC_MARKET_CACHE = (price, change_24h, change_7d, cached_at)
    return price, change_24h, change_7d


async def _fetch_ton_fallback_coin_data() -> dict | None:
    """Fallback fetch for TON when ids=toncoin does not return toncoin data.

    This keeps TON support stable without expanding supported symbols or APIs.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"

    async with httpx.AsyncClient() as client:
        # First fallback: symbol-based lookup.
        symbol_params = {
            "symbols": "ton",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        }
        symbol_data = await _get_with_retry(client, url, symbol_params)

        symbol_coin_data = _extract_ton_coin_data_from_simple_price(symbol_data)
        if isinstance(symbol_coin_data, dict):
            logger.info("TON fallback succeeded via CoinGecko symbols=ton.")
            return symbol_coin_data

        logger.warning(
            "TON fallback via symbols=ton failed. returned_keys=%s",
            (
                list(symbol_data.keys())
                if isinstance(symbol_data, dict)
                else type(symbol_data).__name__
            ),
        )

        # Second fallback: name-based lookup.
        name_params = {
            "names": "Toncoin",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        }
        name_data = await _get_with_retry(client, url, name_params)

        name_coin_data = _extract_ton_coin_data_from_simple_price(name_data)
        if isinstance(name_coin_data, dict):
            logger.info("TON fallback succeeded via CoinGecko names=Toncoin.")
            return name_coin_data

        logger.warning(
            "TON fallback via names=Toncoin failed. returned_keys=%s",
            (list(name_data.keys()) if isinstance(name_data, dict) else type(name_data).__name__),
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
