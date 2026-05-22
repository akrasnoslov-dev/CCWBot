from bot.news_titles import clean_news_title, clean_related_news_text


def test_clean_news_title_removes_known_source_suffixes():
    assert (
        clean_news_title(
            "XRP ETFs attract inflows amid wallet surge. bitcoin, ethereum funds struggle. "
            "- CoinDesk: Bitcoin, Ethereum, Crypto News and Price Data"
        )
        == "XRP ETFs attract inflows amid wallet surge. bitcoin, ethereum funds struggle."
    )
    assert (
        clean_news_title("SEC seeks public comment as it weighs ETFs - Cointelegraph.com News")
        == "SEC seeks public comment as it weighs ETFs"
    )


def test_clean_news_title_preserves_non_matching_titles():
    assert clean_news_title("Bitcoin ETF flow update - Example News") == (
        "Bitcoin ETF flow update - Example News"
    )


def test_clean_related_news_text_removes_final_display_source_metadata():
    assert (
        clean_related_news_text(
            "SEC's Peirce expectations over tokenized stocks exemption - Cointelegraph.com News",
            source="Cointelegraph.com News",
        )
        == "SEC's Peirce expectations over tokenized stocks exemption"
    )
    assert (
        clean_related_news_text("Bitcoin ETF flow update - Example News", source="Example News")
        == "Bitcoin ETF flow update"
    )
