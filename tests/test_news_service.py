from bot.services.news_service import headline_is_relevant


def test_headline_prefilter_keeps_supported_coin_aliases():
    assert headline_is_relevant("Ethereum ETF inflows accelerate")
    assert headline_is_relevant("Solana network outage hits validators")
    assert headline_is_relevant("Toncoin ecosystem upgrade expands The Open Network")


def test_headline_prefilter_uses_word_boundaries_for_short_aliases():
    assert not headline_is_relevant("Software solution provider reports earnings")
    assert not headline_is_relevant("Markets rally tonight after equity earnings")
