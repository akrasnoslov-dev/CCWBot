import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import ENABLE_NEWS_INTELLIGENCE
from bot.db.database import (
    NewsItem,
    cleanup_seen_news,
    make_news_key,
    mark_news_items_seen,
    was_news_seen,
)
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from bot.services.news_intelligence_service import NewsIntelligenceService
from bot.services.news_service import fetch_crypto_news


def _normalize_news_symbol(symbol: str) -> str:
    return str(symbol or "").strip().lower()


def _row_published_at(row: NewsItem) -> datetime | None:
    published_at = row.published_at
    if published_at is None:
        return None
    if published_at.tzinfo is None:
        return published_at.replace(tzinfo=timezone.utc)
    return published_at.astimezone(timezone.utc)


def _row_matches_symbol(row: NewsItem, symbol: str) -> tuple[bool, bool]:
    related_symbols = row.related_symbols if isinstance(row.related_symbols, list) else []
    normalized_related = set()
    for item in related_symbols:
        normalized_item = _normalize_news_symbol(item)
        if normalized_item:
            normalized_related.add(normalized_item)
    primary_match = _normalize_news_symbol(row.primary_symbol or "") == symbol
    related_match = symbol in normalized_related
    return primary_match, related_match


def _news_row_rank(row: NewsItem, symbol: str) -> tuple[int, int, int, int, int]:
    primary_match, related_match = _row_matches_symbol(row, symbol)
    if not (primary_match or related_match):
        return -1, -1, -1, 0, 0
    published_at = _row_published_at(row)
    return (
        1 if primary_match else 0,
        int(row.impact_score if row.impact_score is not None else -1),
        int(row.relevance_score if row.relevance_score is not None else -1),
        int(published_at.timestamp()) if published_at else 0,
        int(row.id or 0),
    )


def _news_row_to_compat_dict(row: NewsItem) -> dict:
    published_at = _row_published_at(row)
    published = published_at.isoformat() if published_at else ""
    url = str(row.url or "").strip()
    related_symbols = row.related_symbols if isinstance(row.related_symbols, list) else []
    return {
        "title": str(row.title or "").strip(),
        "source": str(row.source or "").strip(),
        "link": url,
        "url": url,
        "summary": str(row.llm_summary or row.raw_summary or "").strip(),
        "published": published,
        "published_at": published_at or "",
        "primary_symbol": _normalize_news_symbol(row.primary_symbol or ""),
        "related_symbols": [
            normalized
            for item in related_symbols
            if (normalized := _normalize_news_symbol(item))
        ],
        "category": str(row.category or "").strip().lower(),
        "impact_level": str(row.impact_level or "").strip().lower(),
        "impact_score": row.impact_score,
        "relevance_score": row.relevance_score,
    }


def _news_row_to_alert_dict(row: NewsItem, matched_symbols: list[str]) -> dict:
    published_at = _row_published_at(row)
    published = published_at.isoformat() if published_at else ""
    url = str(row.url or "").strip()
    related_symbols = row.related_symbols if isinstance(row.related_symbols, list) else []
    return {
        "news_item_id": row.id,
        "news_key": str(row.news_key or "").strip(),
        "dedup_group_id": str(row.dedup_group_id or "").strip(),
        "title": str(row.title or "").strip(),
        "source": str(row.source or "").strip(),
        "link": url,
        "url": url,
        "summary": str(row.llm_summary or row.raw_summary or "").strip(),
        "published": published,
        "published_at": published_at or "",
        "primary_symbol": _normalize_news_symbol(row.primary_symbol or ""),
        "related_symbols": [
            normalized
            for item in related_symbols
            if (normalized := _normalize_news_symbol(item))
        ],
        "matched_symbols": matched_symbols,
        "category": str(row.category or "").strip().lower(),
        "impact_level": str(row.impact_level or "").strip().lower(),
        "impact_score": row.impact_score,
        "relevance_score": row.relevance_score,
        "is_alert_worthy": bool(row.is_alert_worthy),
    }


async def select_recent_news_items_for_alerts(
    session: AsyncSession,
    symbols: list[str] | tuple[str, ...],
    *,
    max_age_hours: int,
    now: datetime | None = None,
    limit: int = 200,
) -> list[dict]:
    """Return recent structured news rows that mention currently active symbols.

    This is a read-only selector for persisted news intelligence. It does not
    call RSS providers or LLMs.
    """
    normalized_symbols = {
        normalized
        for symbol in symbols
        if (normalized := _normalize_news_symbol(symbol))
    }
    if not normalized_symbols or max_age_hours < 1 or limit < 1:
        return []

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    cutoff = current_time.astimezone(timezone.utc) - timedelta(hours=max_age_hours)

    result = await session.scalars(
        select(NewsItem)
        .where(NewsItem.is_noise.is_(False))
        .where(NewsItem.published_at.isnot(None))
        .where(NewsItem.published_at >= cutoff)
        .order_by(NewsItem.published_at.desc(), NewsItem.id.desc())
        .limit(limit)
    )

    rows: list[dict] = []
    for row in result.all():
        title = str(row.title or "").strip()
        source = str(row.source or "").strip()
        if not title or not source:
            continue
        matched_symbols = [
            symbol
            for symbol in sorted(normalized_symbols)
            if any(_row_matches_symbol(row, symbol))
        ]
        if not matched_symbols:
            continue
        rows.append(_news_row_to_alert_dict(row, matched_symbols))
    return rows


async def select_intelligence_news_for_symbol(
    session: AsyncSession,
    symbol: str,
    *,
    limit: int = 8,
    max_age_hours: int | None = None,
    now: datetime | None = None,
    selection_stats: dict[str, int] | None = None,
) -> list[dict]:
    """Return stored, intelligence-ranked news candidates for a symbol.

    This selector does not call the news intelligence LLM. It only reads persisted
    news_items rows produced by the existing ingestion path.
    """
    normalized_symbol = _normalize_news_symbol(symbol)
    if not normalized_symbol or limit < 1:
        return []

    query = select(NewsItem).where(NewsItem.is_noise.is_(False))
    if max_age_hours is not None:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        cutoff = current_time.astimezone(timezone.utc) - timedelta(hours=max_age_hours)
        query = query.where(or_(NewsItem.published_at.is_(None), NewsItem.published_at >= cutoff))

    result = await session.scalars(
        query.order_by(NewsItem.published_at.desc().nullslast(), NewsItem.id.desc()).limit(
            max(limit * 20, 200)
        )
    )
    ranked_rows: list[NewsItem] = []
    result_rows = result.all()
    if selection_stats is not None:
        selection_stats["candidate_count"] = len(result_rows)
        selection_stats["noise_filtered_count"] = 0
    for row in result_rows:
        primary_match, related_match = _row_matches_symbol(row, normalized_symbol)
        if not (primary_match or related_match):
            continue
        if not str(row.title or "").strip():
            continue
        ranked_rows.append(row)

    selected: list[dict] = []
    seen_groups: set[str] = set()
    dedup_filtered_count = 0
    for row in sorted(
        ranked_rows,
        key=lambda item: _news_row_rank(item, normalized_symbol),
        reverse=True,
    ):
        group_key = str(row.dedup_group_id or row.news_key or row.id).strip()
        if group_key in seen_groups:
            dedup_filtered_count += 1
            continue
        seen_groups.add(group_key)
        selected.append(_news_row_to_compat_dict(row))
        if len(selected) >= limit:
            break
    if selection_stats is not None:
        selection_stats["selected_count"] = len(selected)
        selection_stats["dedup_filtered_count"] = dedup_filtered_count
    return selected


async def fetch_news_context(
    limit: int,
    *,
    prefer_unseen: bool = True,
    use_intelligence: bool = True,
) -> list[dict]:
    """Fetch RSS news and use seen_news for dedupe when PostgreSQL is active."""
    fetch_limit = max(limit * 3, limit)
    news_items = await asyncio.to_thread(fetch_crypto_news, limit=fetch_limit)
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return news_items[:limit]

    async with DB_SESSION_LOCAL() as session:
        if use_intelligence and ENABLE_NEWS_INTELLIGENCE:
            try:
                service = NewsIntelligenceService(session)
                news_items = await service.analyze_items(news_items)
            except Exception:
                log("News intelligence failed; using RSS news without enrichment.")

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
