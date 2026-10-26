"""Bounded, observable RSS fetching for the existing free news sources."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen

import feedparser

from bot.db.database import make_news_key

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://feeds.feedburner.com/CoinDesk",
    "https://cointelegraph.com/rss",
]
RSS_TIMEOUT_SECONDS = 12
RSS_MAX_BYTES = 1_000_000
RSS_USER_AGENT = "CCWBot-RSS/1.0 (crypto news feed reader)"

NEWS_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "ether", "solana", "sol",
    "gram token", "gram usdt", "gram/usdt", "$gram", "toncoin", "ton",
    "ton rebrand", "toncoin rebrand", "the open network",
    "crypto", "cryptocurrency", "etf", "sec", "fed", "federal reserve",
    "regulation", "hack", "exchange", "war",
]


def _keyword_matches(keyword: str, text: str) -> bool:
    escaped = re.escape(keyword.lower())
    if re.fullmatch(r"[a-z0-9]+", keyword):
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None
    return keyword.lower() in text


def headline_is_relevant(title: str, summary: str = "") -> bool:
    """Low-cost, word-boundary-aware prefilter; not an alert decision."""
    text = f"{title} {summary}".lower()
    return any(_keyword_matches(keyword, text) for keyword in NEWS_KEYWORDS)


def _published_at(item: dict) -> datetime | None:
    value = str(item.get("published") or "").strip()
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (ValueError, TypeError, IndexError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    return (parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None
            else parsed.astimezone(timezone.utc))


def _read_rss_feed(feed_url: str):
    """Bound provider latency/response size; parse only successfully fetched bytes."""
    request = Request(
        feed_url,
        headers={
            "User-Agent": RSS_USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
    )
    with urlopen(request, timeout=RSS_TIMEOUT_SECONDS) as response:
        payload = response.read(RSS_MAX_BYTES + 1)
        if len(payload) > RSS_MAX_BYTES:
            raise ValueError("rss_response_too_large")
    return feedparser.parse(payload)


def fetch_crypto_news(limit: int = 5) -> list[dict]:
    """Merge available feeds by publication age *before* applying the batch limit.

    A failed/empty source must not block another. No automatic age-based
    rejection: old/unknown-dated items remain distinguishable in diagnostics,
    while fresh articles take precedence within the bounded batch.
    """
    if limit < 1:
        return []

    news_items: list[dict] = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    for source_index, feed_url in enumerate(RSS_FEEDS):
        try:
            feed = _read_rss_feed(feed_url)
        except Exception as error:
            # Do not log exception text, URLs, entries, or provider response bodies.
            logger.warning(
                "ops_event=news_rss_source source_index=%s status=failed reason=%s",
                source_index, type(error).__name__,
            )
            continue

        entries = feed.entries
        relevant = 0
        missing_title = 0
        fresh = 0
        missing_date = 0
        for entry in entries:
            title = entry.get("title", "")
            if not title:
                missing_title += 1
                continue
            summary = entry.get("summary", "")
            if not headline_is_relevant(title, summary):
                continue
            relevant += 1
            item = {
                "title": title,
                "link": entry.get("link", ""),
                "url": entry.get("link", ""),
                "summary": summary,
                "published": entry.get("published") or entry.get("updated") or "",
                "source": feed.feed.get("title") or feed_url,
            }
            published_at = _published_at(item)
            if published_at is None:
                missing_date += 1
            elif cutoff <= published_at <= now + timedelta(minutes=5):
                fresh += 1
            news_items.append(item)

        logger.info(
            "ops_event=news_rss_source source_index=%s status=%s entries=%s "
            "keyword_pass=%s missing_title=%s published_24h=%s missing_date=%s",
            source_index,
            "partial" if feed.get("bozo") else "ok",
            len(entries), relevant, missing_title, fresh, missing_date,
        )

    # Keep the stable key dedup rule; do not merge distinct stories by keyword.
    unique_news: list[dict] = []
    seen_keys: set[str] = set()
    for item in sorted(
        news_items,
        key=lambda item: (_published_at(item) or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    ):
        news_key = make_news_key(item)
        if not news_key or news_key in seen_keys:
            continue
        seen_keys.add(news_key)
        unique_news.append(item)
    logger.info(
        "ops_event=news_rss_batch candidates=%s unique=%s selected=%s",
        len(news_items), len(unique_news), min(limit, len(unique_news)),
    )
    return unique_news[:limit]
