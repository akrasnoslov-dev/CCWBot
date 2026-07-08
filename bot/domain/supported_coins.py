"""Supported coin metadata shared by price checks and Premium watchlists."""

from __future__ import annotations

ALL_SUPPORTED_COINS = {
    "btc": {
        "name": "Bitcoin",
        "coingecko_id": "bitcoin",
        "display_symbol": "BTC",
        "aliases": (),
        "free": True,
    },
    "eth": {
        "name": "Ethereum",
        "coingecko_id": "ethereum",
        "display_symbol": "ETH",
        "aliases": (),
        "free": False,
    },
    "sol": {
        "name": "Solana",
        "coingecko_id": "solana",
        "display_symbol": "SOL",
        "aliases": (),
        "free": False,
    },
    "gram": {
        "name": "Gram",
        "coingecko_id": "the-open-network",
        "display_symbol": "GRAM",
        "aliases": ("ton", "toncoin"),
        "free": False,
    },
}

ACTIVE_SYMBOLS = ("btc", "eth", "gram", "sol")
SUPPORTED_COINS = {symbol: ALL_SUPPORTED_COINS[symbol] for symbol in ACTIVE_SYMBOLS}
SUPPORTED_SYMBOLS = ACTIVE_SYMBOLS
SYMBOL_ALIASES = {
    alias: symbol
    for symbol, metadata in ALL_SUPPORTED_COINS.items()
    for alias in tuple(metadata.get("aliases", ()))
}
FREE_ALERT_FREQUENCY_SECONDS = 14400
PREMIUM_ALERT_FREQUENCY_SECONDS = (3600, 21600, 86400)
DEFAULT_PREMIUM_ALERT_FREQUENCY_SECONDS = 21600


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().lower()
    return SYMBOL_ALIASES.get(normalized, normalized)


def display_symbol(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    metadata = ALL_SUPPORTED_COINS.get(normalized)
    if metadata is None:
        return normalized.upper()
    return str(metadata.get("display_symbol") or normalized.upper()).upper()


def coin_display_name(symbol: str) -> str:
    return str(ALL_SUPPORTED_COINS[normalize_symbol(symbol)]["name"])


def is_supported_symbol(symbol: str) -> bool:
    return normalize_symbol(symbol) in SUPPORTED_COINS


def is_symbol_free(symbol: str) -> bool:
    coin = SUPPORTED_COINS.get(normalize_symbol(symbol))
    return bool(coin and coin["free"])


def premium_symbols_display() -> str:
    return ", ".join(
        display_symbol(symbol) for symbol in SUPPORTED_SYMBOLS if not is_symbol_free(symbol)
    )


def supported_symbols_display(*, include_alias_note: bool = False) -> str:
    symbols = [display_symbol(symbol) for symbol in SUPPORTED_SYMBOLS]
    text = ", ".join(symbols)
    if include_alias_note and "gram" in SUPPORTED_SYMBOLS:
        text = f"{text} (TON legacy alias accepted for GRAM)"
    return text
