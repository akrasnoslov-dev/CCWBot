"""Supported coin metadata shared by price checks and Premium watchlists."""

from __future__ import annotations

SUPPORTED_COINS = {
    "btc": {"name": "Bitcoin", "coingecko_id": "bitcoin", "free": True},
    "eth": {"name": "Ethereum", "coingecko_id": "ethereum", "free": False},
    "sol": {"name": "Solana", "coingecko_id": "solana", "free": False},
    "xrp": {"name": "XRP", "coingecko_id": "ripple", "free": False},
    "bnb": {"name": "BNB", "coingecko_id": "binancecoin", "free": False},
    "doge": {"name": "Dogecoin", "coingecko_id": "dogecoin", "free": False},
    "ada": {"name": "Cardano", "coingecko_id": "cardano", "free": False},
    "ton": {"name": "Toncoin", "coingecko_id": "toncoin", "free": False},
    "link": {"name": "Chainlink", "coingecko_id": "chainlink", "free": False},
    "trx": {"name": "TRON", "coingecko_id": "tron", "free": False},
}

SUPPORTED_SYMBOLS = tuple(SUPPORTED_COINS.keys())
FREE_ALERT_FREQUENCY_SECONDS = 14400
PREMIUM_ALERT_FREQUENCY_SECONDS = (3600, 21600, 86400)
DEFAULT_PREMIUM_ALERT_FREQUENCY_SECONDS = 21600


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().lower()


def is_supported_symbol(symbol: str) -> bool:
    return normalize_symbol(symbol) in SUPPORTED_COINS


def is_symbol_free(symbol: str) -> bool:
    coin = SUPPORTED_COINS.get(normalize_symbol(symbol))
    return bool(coin and coin["free"])


def premium_symbols_display() -> str:
    return ", ".join(symbol.upper() for symbol in SUPPORTED_SYMBOLS if not is_symbol_free(symbol))

