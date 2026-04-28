import feedparser


RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
]


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
    """Fetch recent crypto/BTC-related news from RSS feeds."""
    news_items = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            published = entry.get("published", "")

            if not title:
                continue

            if not headline_is_relevant(title, summary):
                continue

            news_items.append(
                {
                    "title": title,
                    "link": link,
                    "published": published,
                    "source": feed.feed.get("title", "Unknown source"),
                }
            )

    # Remove duplicates by title
    unique_news = []
    seen_titles = set()

    for item in news_items:
        normalized_title = item["title"].strip().lower()

        if normalized_title in seen_titles:
            continue

        seen_titles.add(normalized_title)
        unique_news.append(item)

    return unique_news[:limit]
