from bot.domain.supported_coins import (
    ACTIVE_SYMBOLS,
    ALL_SUPPORTED_COINS,
    SUPPORTED_COINS,
    coin_display_name,
    display_symbol,
    is_supported_symbol,
    normalize_symbol,
    premium_symbols_display,
    supported_symbols_display,
)


def test_gram_rebrand_uses_primary_gram_symbol_with_legacy_ton_alias():
    assert SUPPORTED_COINS["gram"]["coingecko_id"] == "the-open-network"
    assert normalize_symbol("gram") == "gram"
    assert normalize_symbol("ton") == "gram"
    assert normalize_symbol("toncoin") == "gram"
    assert display_symbol("ton") == "GRAM"
    assert display_symbol("gram") == "GRAM"
    assert coin_display_name("ton") == "Gram"


def test_premium_and_supported_symbol_display_use_gram():
    assert premium_symbols_display() == "ETH, GRAM, SOL"
    assert supported_symbols_display(include_alias_note=True) == (
        "BTC, ETH, GRAM, SOL (TON legacy alias accepted for GRAM)"
    )


def test_deprecated_ghost_symbols_are_fully_removed():
    assert set(ALL_SUPPORTED_COINS) == set(ACTIVE_SYMBOLS) == {"btc", "eth", "gram", "sol"}
    for ghost in ("ada", "bnb", "doge", "link", "trx", "xrp"):
        assert ghost not in ALL_SUPPORTED_COINS
        assert not is_supported_symbol(ghost)
        # Unknown symbols still degrade safely for historical DB rows.
        assert display_symbol(ghost) == ghost.upper()
