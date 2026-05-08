from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from database import (
    cleanup_seen_news,
    make_news_key,
    mark_news_items_seen,
    was_news_seen,
)
from news_service import fetch_crypto_news


async def fetch_news_context(limit: int, *, prefer_unseen: bool = True) -> list[dict]:
    """Fetch RSS news and use seen_news for dedupe when PostgreSQL is active."""
    fetch_limit = max(limit * 3, limit)
    news_items = fetch_crypto_news(limit=fetch_limit)
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return news_items[:limit]

    async with DB_SESSION_LOCAL() as session:
        unseen_items = [
            item
            for item in news_items
            if not await was_news_seen(session, make_news_key(item))
        ]

    if unseen_items:
        return unseen_items[:limit]
    if prefer_unseen:
        log("No unseen RSS news found in PostgreSQL seen_news; reusing recent fetched news.")
    return news_items[:limit]


async def remember_news_context(news_items: list[dict]) -> None:
    """Mark news items as seen in PostgreSQL after they were used by the bot."""
    if not (DB_ENABLED and DB_SESSION_LOCAL and news_items):
        return

    async with DB_SESSION_LOCAL() as session:
        await mark_news_items_seen(session, news_items)
        await cleanup_seen_news(session, keep_latest=200)
