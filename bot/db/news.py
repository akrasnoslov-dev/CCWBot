"""News identity, seen-news, and news-intelligence persistence.

Belongs here: seen-news dedup rows and persisted news intelligence records.
Does not belong here: RSS fetching, LLM prompt construction, Telegram rendering,
or schema/model declarations.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import NewsItem, SeenNews, make_news_key, utc_now


async def was_news_seen(session: AsyncSession, news_key: str) -> bool:
    """Return True when a news key already exists in seen_news."""
    if not news_key:
        return False
    row = await session.scalar(select(SeenNews.id).where(SeenNews.news_key == news_key).limit(1))
    return row is not None



async def mark_news_seen(session: AsyncSession, news_item: dict):
    """Store one news item in seen_news if it has not been stored before."""
    news_key = make_news_key(news_item)
    if not news_key:
        return None

    existing = await session.scalar(select(SeenNews).where(SeenNews.news_key == news_key).limit(1))
    if existing:
        return existing

    row = SeenNews(
        news_key=news_key,
        title=str(news_item.get("title") or "")[:1000],
        link=str(news_item.get("link") or "")[:2000],
        source=str(news_item.get("source") or "")[:255] or None,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await session.scalar(select(SeenNews).where(SeenNews.news_key == news_key).limit(1))
    await session.refresh(row)
    return row



async def mark_news_items_seen(session: AsyncSession, news_items: list[dict]) -> list[SeenNews]:
    """Store multiple news items while skipping duplicates."""
    rows = []
    for item in news_items:
        news_key = make_news_key(item)
        if not news_key or await was_news_seen(session, news_key):
            continue
        row = SeenNews(
            news_key=news_key,
            title=str(item.get("title") or "")[:1000],
            link=str(item.get("link") or "")[:2000],
            source=str(item.get("source") or "")[:255] or None,
        )
        session.add(row)
        rows.append(row)

    if not rows:
        return []

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        stored_rows = []
        for item in news_items:
            row = await mark_news_seen(session, item)
            if row:
                stored_rows.append(row)
        return stored_rows

    for row in rows:
        await session.refresh(row)
    return rows



async def get_recent_seen_news(session: AsyncSession, limit: int = 100) -> list[SeenNews]:
    """Return recent seen news rows, newest first."""
    result = await session.scalars(
        select(SeenNews).order_by(SeenNews.seen_at.desc(), SeenNews.id.desc()).limit(limit)
    )
    return list(result.all())



async def cleanup_seen_news(session: AsyncSession, keep_latest: int = 100) -> int:
    """Keep only the latest seen_news rows and return how many were deleted."""
    if keep_latest < 1:
        raise ValueError("keep_latest must be at least 1.")

    result = await session.scalars(
        select(SeenNews).order_by(SeenNews.seen_at.desc(), SeenNews.id.desc()).offset(keep_latest)
    )
    rows_to_delete = list(result.all())
    for row in rows_to_delete:
        await session.delete(row)
    await session.commit()
    return len(rows_to_delete)



async def get_news_item_by_key(session: AsyncSession, news_key: str) -> NewsItem | None:
    """Return a structured news item by stable news key."""
    if not news_key:
        return None
    return await session.scalar(select(NewsItem).where(NewsItem.news_key == news_key).limit(1))



async def get_cached_news_item_analysis(
    session: AsyncSession,
    *,
    news_key: str,
    llm_input_hash: str,
    llm_model: str,
) -> NewsItem | None:
    """Return a reusable structured news analysis for the exact compact LLM input."""
    if not news_key or not llm_input_hash or not llm_model:
        return None
    return await session.scalar(
        select(NewsItem)
        .where(NewsItem.news_key == news_key)
        .where(NewsItem.llm_input_hash == llm_input_hash)
        .where(NewsItem.llm_model == llm_model)
        .where(NewsItem.llm_status.in_(["success", "skipped_noise", "skipped_duplicate"]))
        .limit(1)
    )



async def count_recent_news_intelligence_llm_calls(
    session: AsyncSession,
    *,
    since: datetime,
    provider: str = "groq",
) -> int:
    """Count recent news intelligence LLM attempts for budget enforcement."""
    return int(
        await session.scalar(
            select(func.count())
            .select_from(NewsItem)
            .where(NewsItem.llm_provider == provider)
            .where(NewsItem.llm_status.in_(["success", "failed"]))
            .where(NewsItem.updated_at >= since)
        )
        or 0
    )



async def upsert_news_item(
    session: AsyncSession,
    *,
    news_key: str,
    title: str,
    source: str | None,
    url: str,
    published_at: datetime | None,
    fetched_at: datetime,
    raw_summary: str | None,
    llm_summary: str | None = None,
    llm_raw_response: str | None = None,
    related_symbols: list[str] | None = None,
    primary_symbol: str | None = None,
    category: str | None = None,
    impact_score: int | None = None,
    impact_level: str | None = None,
    relevance_score: int | None = None,
    dedup_group_id: str | None = None,
    is_duplicate: bool = False,
    is_noise: bool = False,
    is_alert_worthy: bool = False,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    llm_input_hash: str | None = None,
    llm_status: str = "pending",
    llm_error: str | None = None,
) -> NewsItem:
    """Create or update one structured news intelligence row."""
    row = await get_news_item_by_key(session, news_key)
    if row is None:
        row = NewsItem(news_key=news_key, title=title[:1000], url=url[:2000])
        session.add(row)

    row.title = title[:1000]
    row.source = source[:255] if source else None
    row.url = url[:2000]
    row.published_at = published_at
    row.fetched_at = fetched_at
    row.raw_summary = raw_summary
    row.llm_summary = llm_summary
    row.llm_raw_response = llm_raw_response
    row.related_symbols = related_symbols or []
    row.primary_symbol = primary_symbol
    row.category = category
    row.impact_score = impact_score
    row.impact_level = impact_level
    row.relevance_score = relevance_score
    row.dedup_group_id = dedup_group_id
    row.is_duplicate = is_duplicate
    row.is_noise = is_noise
    row.is_alert_worthy = is_alert_worthy
    row.llm_provider = llm_provider
    row.llm_model = llm_model
    row.llm_input_hash = llm_input_hash
    row.llm_status = llm_status
    row.llm_error = llm_error
    row.updated_at = utc_now()

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_news_item_by_key(session, news_key)
        if existing is None:
            raise
        return existing
    await session.refresh(row)
    return row
