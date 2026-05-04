import feedparser

from database import make_news_key

# Existing curated RSS feeds used by the bot for context in AI summaries.
RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
]

# Lightweight keyword filter to keep only BTC/crypto-related headlines.
NEWS_KEYWORDS = [
    "bitcoin",
    "btc",
    "crypto",
    "cryptocurrency",
    "etf",
    "sec",
    "fed",
    "federal reserve",
    "regulation",
    "hack",
    "exchange",
    "war",
]


def headline_is_relevant(title: str, summary: str = "") -> bool:
    """Check whether a news item looks relevant to BTC."""
    text = f"{title} {summary}".lower()
    return any(keyword in text for keyword in NEWS_KEYWORDS)


def fetch_crypto_news(limit: int = 5) -> list[dict]:
    """Fetch and filter recent crypto/BTC RSS entries.

    This function is intentionally simple: parse feed, filter by keywords,
    deduplicate by stable link/title key, then trim to requested limit.
    """
    news_items = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.get("title", "")
            if not title:
                continue

            summary = entry.get("summary", "")
            if not headline_is_relevant(title, summary):
                continue

            news_items.append(
                {
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": feed.feed.get("title", "Unknown source"),
                }
            )

    unique_news = []
    seen_keys = set()
    for item in news_items:
        news_key = make_news_key(item)
        if not news_key or news_key in seen_keys:
            continue
        seen_keys.add(news_key)
        unique_news.append(item)

    return unique_news[:limit]
