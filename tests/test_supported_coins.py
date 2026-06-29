from bot.domain.supported_coins import (
    SUPPORTED_COINS,
    coin_display_name,
    display_symbol,
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
