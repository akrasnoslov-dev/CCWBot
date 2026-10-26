from bot.services.news_service import headline_is_relevant


def test_headline_prefilter_keeps_supported_coin_aliases():
    assert headline_is_relevant("Ethereum ETF inflows accelerate")
    assert headline_is_relevant("Solana network outage hits validators")
    assert headline_is_relevant("Toncoin ecosystem upgrade expands The Open Network")
    assert headline_is_relevant("GRAM token liquidity improves after TON rebrand")


def test_headline_prefilter_uses_word_boundaries_for_short_aliases():
    assert not headline_is_relevant("Software solution provider reports earnings")
    assert not headline_is_relevant("Markets rally tonight after equity earnings")
    assert not headline_is_relevant("Recipe calls for one gram of salt")


def _sample_rss_feed(*, entries=True, bozo=False):
    from datetime import datetime, timezone
    from email.utils import format_datetime

    import feedparser

    news_entries = [
        feedparser.FeedParserDict({
            "title": "Bitcoin network update",
            "link": "https://www.coindesk.com/markets/example",
            "summary": "Bitcoin market update",
            "published": format_datetime(datetime.now(timezone.utc)),
        })
    ] if entries else []
    return feedparser.FeedParserDict(
        entries=news_entries,
        feed=feedparser.FeedParserDict(title="CoinDesk"),
        bozo=bozo,
    )


def test_coindesk_fallback_only_on_primary_failure(monkeypatch):
    from bot.services import news_service as rss

    urls = []
    primary = rss.RSS_FEEDS[0]
    mirror = rss.RSS_FEED_FALLBACKS[primary]

    def reader(url):
        urls.append(url)
        if url == primary:
            return _sample_rss_feed()
        raise AssertionError("Fallback or unrelated source unexpectedly called")

    monkeypatch.setattr(rss, "_read_rss_feed", reader)
    feed, route = rss._read_rss_feed_with_fallback(primary)
    assert route == "primary"
    assert len(feed.entries) == 1
    assert urls == [primary]
    assert mirror not in urls


def test_coindesk_403_uses_mirror_once_and_preserves_second_source(monkeypatch, caplog):
    from urllib.error import HTTPError

    from bot.services import news_service as rss

    primary, second = rss.RSS_FEEDS
    mirror = rss.RSS_FEED_FALLBACKS[primary]
    calls = []

    def reader(url):
        calls.append(url)
        if url == primary:
            raise HTTPError(url, 403, "private response must not be logged", None, None)
        if url == mirror:
            return _sample_rss_feed()
        if url == second:
            return _sample_rss_feed(entries=False)
        raise AssertionError("Unknown source")

    monkeypatch.setattr(rss, "_read_rss_feed", reader)
    with caplog.at_level("INFO"):
        items = rss.fetch_crypto_news(limit=5)
    assert [item["link"] for item in items] == [
        "https://www.coindesk.com/markets/example"
    ]
    assert calls == [primary, mirror, second]
    assert "ops_event=news_rss_failover status=recovered primary_reason=HTTPError" in caplog.text
    assert "source_index=0 status=ok entries=1" in caplog.text
    assert "route=fallback" in caplog.text
    assert "private response must not be logged" not in caplog.text


def test_coindesk_empty_or_malformed_primary_uses_fallback(monkeypatch):
    from bot.services import news_service as rss

    primary = rss.RSS_FEEDS[0]
    mirror = rss.RSS_FEED_FALLBACKS[primary]
    def make_reader(unusable_feed, calls):
        def reader(url):
            calls.append(url)
            return unusable_feed if url == primary else _sample_rss_feed()
        return reader

    for unusable in (
        _sample_rss_feed(entries=False),
        _sample_rss_feed(bozo=True),
    ):
        calls = []
        monkeypatch.setattr(rss, "_read_rss_feed", make_reader(unusable, calls))
        feed, route = rss._read_rss_feed_with_fallback(primary)
        assert route == "fallback"
        assert feed.entries
        assert calls == [primary, mirror]


def test_coindesk_both_feeds_fail_but_cointelegraph_continues(monkeypatch, caplog):
    from bot.services import news_service as rss

    primary, second = rss.RSS_FEEDS
    mirror = rss.RSS_FEED_FALLBACKS[primary]
    calls = []

    def reader(url):
        calls.append(url)
        if url == primary:
            raise TimeoutError("primary private details")
        if url == mirror:
            raise ConnectionError("mirror private details")
        if url == second:
            return _sample_rss_feed()
        raise AssertionError("Unknown feed")

    monkeypatch.setattr(rss, "_read_rss_feed", reader)
    with caplog.at_level("INFO"):
        items = rss.fetch_crypto_news(limit=10)
    assert len(items) == 1
    assert calls == [primary, mirror, second]
    assert (
        "status=failed primary_reason=TimeoutError fallback_reason=ConnectionError"
        in caplog.text
    )
    assert "source_index=0 status=failed reason=ConnectionError" in caplog.text
    assert "primary private details" not in caplog.text
    assert "mirror private details" not in caplog.text
