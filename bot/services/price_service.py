import asyncio
import logging
import time

import httpx

from bot.config import PRICE_CACHE_TTL_SECONDS
from bot.domain.supported_coins import (
    SUPPORTED_COINS,
    display_symbol,
    normalize_symbol,
    supported_symbols_display,
)


class CoinGeckoRateLimitError(Exception):
    """Raised when CoinGecko returns HTTP 429."""


# Keep this mapping intentionally explicit. Only these symbols are supported in
# command handlers and callbacks.
COIN_SYMBOL_TO_ID = {
    symbol: str(metadata["coingecko_id"]) for symbol, metadata in SUPPORTED_COINS.items()
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
            normalize_symbol(symbol)
            for symbol in symbols.split(",")
            if normalize_symbol(symbol) in COIN_SYMBOL_TO_ID
        )

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
    for attempt in range(max_retries + 1):
        response = await client.get(url, params=params, timeout=10)
        if response.status_code != 429:
            response.raise_for_status()
            return response.json()

        if attempt < max_retries:
            delay = base_delay * (2**attempt)
            logger.warning(
                "ops_event=coingecko_rate_limit attempt=%s max_retries=%s "
                "stale_cache_available=%s retry_delay_seconds=%s",
                attempt + 1,
                max_retries,
                _build_stale_price_payload(params) is not None,
                delay,
            )
            await asyncio.sleep(delay)

    stale_payload = _build_stale_price_payload(params)
    if stale_payload is not None:
        logger.warning(
            "ops_event=coingecko_rate_limit attempt=%s max_retries=%s "
            "stale_cache_available=true",
            max_retries,
            max_retries,
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
    from bot.db.database import get_price_state
    from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL
    from bot.storage import load_state

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
    normalized_symbol = normalize_symbol(symbol)

    if normalized_symbol not in COIN_SYMBOL_TO_ID:
        supported = supported_symbols_display(include_alias_note=True)
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
    if coin_data is None:
        logger.warning(
            "CoinGecko simple price response missing expected id. symbol=%s "
            "expected_id=%s returned_keys=%s",
            display_symbol(normalized_symbol),
            coin_id,
            list(data.keys()),
        )
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


async def get_coin_market_data_batch(
    symbols: list[str] | tuple[str, ...] | set[str],
) -> dict[str, dict[str, float | None]]:
    """Fetch market data for supported symbols with one CoinGecko request.

    Missing symbols are logged and skipped so one partial CoinGecko response
    does not fail the whole automatic monitoring cycle.
    """
    global _BTC_MARKET_CACHE

    normalized_symbols = list(dict.fromkeys(normalize_symbol(symbol) for symbol in symbols))
    unsupported = [symbol for symbol in normalized_symbols if symbol not in COIN_SYMBOL_TO_ID]
    if unsupported:
        supported = supported_symbols_display(include_alias_note=True)
        raise ValueError(f"Unsupported coin symbol(s) {unsupported}. Supported: {supported}")
    if not normalized_symbols:
        return {}

    coin_ids = [COIN_SYMBOL_TO_ID[symbol] for symbol in normalized_symbols]
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    async with httpx.AsyncClient() as client:
        data = await _get_with_retry(client, url, params)

    if not isinstance(data, dict):
        raise ValueError("Unexpected CoinGecko response format.")

    result: dict[str, dict[str, float | None]] = {}
    for symbol, coin_id in zip(normalized_symbols, coin_ids, strict=True):
        coin_data = data.get(coin_id)
        if not isinstance(coin_data, dict):
            logger.warning(
                "CoinGecko batch response missing data for %s. expected_id=%s "
                "returned_keys=%s. Skipping symbol.",
                display_symbol(symbol),
                coin_id,
                list(data.keys()),
            )
            continue
        price = coin_data.get("usd")
        if price is None:
            logger.warning(
                "CoinGecko batch response missing USD price for %s. Skipping symbol.",
                display_symbol(symbol),
            )
            continue
        change_24h = coin_data.get("usd_24h_change")
        price_value = float(price)
        change_24h_value = float(change_24h) if change_24h is not None else 0.0
        _set_cached_price(symbol, price_value, change_24h_value)
        if symbol == "btc":
            cached_at = time.time()
            _BTC_MARKET_CACHE = (price_value, change_24h_value, None, cached_at)
            _sync_btc_price_cache(price_value, change_24h_value, cached_at)
        result[symbol] = {
            "price": price_value,
            "change_24h": change_24h_value,
            "change_7d": None,
        }

    return result


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


def _extract_ton_coin_data_from_simple_price(payload: dict) -> dict | None:
    """Accept only the current exact CoinGecko id for GRAM/legacy TON payloads."""
    if not isinstance(payload, dict):
        return None

    preferred = payload.get("the-open-network")
    if isinstance(preferred, dict) and preferred.get("usd") is not None:
        return preferred
    return None
