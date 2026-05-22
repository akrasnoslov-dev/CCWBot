"""Budget-aware structured intelligence for RSS news items."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import (
    NEWS_INTELLIGENCE_MAX_ITEMS_PER_RUN,
    NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_HOUR,
    NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_RUN,
    NEWS_LLM_TIMEOUT_SECONDS,
)
from bot.db.database import (
    NewsItem,
    count_recent_news_intelligence_llm_calls,
    get_cached_news_item_analysis,
    make_news_key,
    upsert_news_item,
    utc_now,
)
from bot.domain.supported_coins import ALL_SUPPORTED_COINS
from bot.services.ai_agent_groq import GROQ_NEWS_INTELLIGENCE_MODEL, ask_news_intelligence_raw

logger = logging.getLogger(__name__)

ALLOWED_SYMBOLS = set(ALL_SUPPORTED_COINS)
ALLOWED_CATEGORIES = {
    "regulation",
    "exchange",
    "security",
    "macro",
    "etf",
    "whale",
    "project",
    "technical",
    "market",
    "noise",
}
ALLOWED_IMPACT_LEVELS = {"low", "medium", "high", "critical"}
NOISE_PATTERNS = [
    r"\bprice prediction\b",
    r"\bbest crypto to buy\b",
    r"\btop coins? to buy\b",
    r"\b100x\b",
    r"\bpresale\b",
    r"\bsponsored\b",
    r"\badvertisement\b",
    r"\bcasino\b",
    r"\banalyst predicts\b",
    r"\bcould explode\b",
]

NewsLlmCallable = Callable[[list[dict], str, int], Awaitable[tuple[str, dict]]]


@dataclass(frozen=True)
class NormalizedNewsItem:
    title: str
    source: str | None
    url: str
    summary: str | None
    published_at: datetime | None
    published: str
    news_key: str

    def compatibility_dict(self) -> dict:
        return {
            "title": self.title,
            "source": self.source or "",
            "link": self.url,
            "url": self.url,
            "summary": self.summary or "",
            "published": self.published,
            "published_at": self.published_at,
        }


class NewsIntelligenceService:
    """Analyze RSS news with cache and strict LLM budgets."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        llm_client: NewsLlmCallable | None = None,
        model: str = GROQ_NEWS_INTELLIGENCE_MODEL,
        max_items_per_run: int = NEWS_INTELLIGENCE_MAX_ITEMS_PER_RUN,
        max_llm_calls_per_run: int = NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_RUN,
        max_llm_calls_per_hour: int = NEWS_INTELLIGENCE_MAX_LLM_CALLS_PER_HOUR,
        timeout_seconds: int = NEWS_LLM_TIMEOUT_SECONDS,
    ) -> None:
        self.session = session
        self.llm_client = llm_client or _default_llm_client
        self.model = model
        self.max_items_per_run = max_items_per_run
        self.max_llm_calls_per_run = max_llm_calls_per_run
        self.max_llm_calls_per_hour = max_llm_calls_per_hour
        self.timeout_seconds = timeout_seconds
        self._run_llm_calls = 0

    async def analyze_items(self, raw_items: list[dict]) -> list[dict]:
        """Persist/analyze a bounded subset and return existing-compatible news dicts."""
        if not raw_items:
            return []

        normalized_items = [normalize_news_item(item) for item in raw_items]
        compatibility_items = [item.compatibility_dict() for item in normalized_items if item]
        processable = [item for item in normalized_items if item][: self.max_items_per_run]
        if not processable:
            return compatibility_items

        hourly_calls = await count_recent_news_intelligence_llm_calls(
            self.session,
            since=utc_now() - timedelta(hours=1),
        )
        seen_dedup_groups: set[str] = set()
        for item in processable:
            try:
                await self._process_item(item, seen_dedup_groups, hourly_calls)
            except Exception as error:
                logger.warning("News intelligence item processing failed: %s", _safe_error(error))
        return compatibility_items

    async def _process_item(
        self,
        item: NormalizedNewsItem,
        seen_dedup_groups: set[str],
        hourly_calls: int,
    ) -> NewsItem:
        llm_payload = build_llm_payload(item)
        llm_input_hash = _hash_json(llm_payload)
        dedup_group_id = build_pre_llm_dedup_group_id(item)

        cached = await get_cached_news_item_analysis(
            self.session,
            news_key=item.news_key,
            llm_input_hash=llm_input_hash,
            llm_model=self.model,
        )
        if cached is not None:
            return cached

        if is_obvious_noise(item):
            return await self._persist(
                item,
                llm_input_hash=llm_input_hash,
                dedup_group_id=dedup_group_id,
                category="noise",
                impact_score=0,
                impact_level="low",
                relevance_score=0,
                is_noise=True,
                is_alert_worthy=False,
                llm_status="skipped_noise",
            )

        if dedup_group_id in seen_dedup_groups or await self._dedup_group_exists(
            dedup_group_id, item.news_key
        ):
            return await self._persist(
                item,
                llm_input_hash=llm_input_hash,
                dedup_group_id=dedup_group_id,
                is_duplicate=True,
                is_alert_worthy=False,
                llm_status="skipped_duplicate",
            )

        seen_dedup_groups.add(dedup_group_id)
        if not self._budget_allows(hourly_calls):
            return await self._persist(
                item,
                llm_input_hash=llm_input_hash,
                dedup_group_id=dedup_group_id,
                is_alert_worthy=False,
                llm_status="skipped_budget",
            )

        messages = build_llm_messages(llm_payload)
        raw_response: str | None = None
        try:
            raw_response, parsed = await self.llm_client(
                messages,
                self.model,
                self.timeout_seconds,
            )
            self._run_llm_calls += 1
            validated = validate_llm_output(parsed)
            post_dedup_group_id = build_post_llm_dedup_group_id(
                str(parsed.get("dedup_hint") or ""), dedup_group_id
            )
            return await self._persist(
                item,
                llm_input_hash=llm_input_hash,
                dedup_group_id=post_dedup_group_id,
                llm_summary=validated["summary"],
                llm_raw_response=raw_response,
                related_symbols=validated["related_symbols"],
                primary_symbol=validated["primary_symbol"],
                category=validated["category"],
                impact_score=validated["impact_score"],
                impact_level=validated["impact_level"],
                relevance_score=validated["relevance_score"],
                is_noise=validated["is_noise"],
                is_alert_worthy=validated["is_alert_worthy"],
                llm_status="success",
            )
        except Exception as error:
            self._run_llm_calls += 1
            return await self._persist(
                item,
                llm_input_hash=llm_input_hash,
                dedup_group_id=dedup_group_id,
                llm_raw_response=raw_response,
                is_alert_worthy=False,
                llm_status="failed",
                llm_error=_safe_error(error),
            )

    async def _dedup_group_exists(self, dedup_group_id: str, news_key: str) -> bool:
        existing = await self.session.scalar(
            select(NewsItem.id)
            .where(NewsItem.dedup_group_id == dedup_group_id)
            .where(NewsItem.news_key != news_key)
            .limit(1)
        )
        return existing is not None

    def _budget_allows(self, hourly_calls: int) -> bool:
        if self.max_llm_calls_per_run <= 0 or self.max_llm_calls_per_hour <= 0:
            return False
        return (
            self._run_llm_calls < self.max_llm_calls_per_run
            and hourly_calls + self._run_llm_calls < self.max_llm_calls_per_hour
        )

    async def _persist(
        self,
        item: NormalizedNewsItem,
        *,
        llm_input_hash: str,
        dedup_group_id: str,
        llm_summary: str | None = None,
        llm_raw_response: str | None = None,
        related_symbols: list[str] | None = None,
        primary_symbol: str | None = None,
        category: str | None = None,
        impact_score: int | None = None,
        impact_level: str | None = None,
        relevance_score: int | None = None,
        is_duplicate: bool = False,
        is_noise: bool = False,
        is_alert_worthy: bool = False,
        llm_status: str,
        llm_error: str | None = None,
    ) -> NewsItem:
        return await upsert_news_item(
            self.session,
            news_key=item.news_key,
            title=item.title,
            source=item.source,
            url=item.url,
            published_at=item.published_at,
            fetched_at=utc_now(),
            raw_summary=item.summary,
            llm_summary=llm_summary,
            llm_raw_response=llm_raw_response,
            related_symbols=related_symbols or [],
            primary_symbol=primary_symbol,
            category=category,
            impact_score=impact_score,
            impact_level=impact_level,
            relevance_score=relevance_score,
            dedup_group_id=dedup_group_id,
            is_duplicate=is_duplicate,
            is_noise=is_noise,
            is_alert_worthy=is_alert_worthy,
            llm_provider="groq",
            llm_model=self.model,
            llm_input_hash=llm_input_hash,
            llm_status=llm_status,
            llm_error=llm_error,
        )


async def _default_llm_client(
    messages: list[dict], model: str, timeout_seconds: int
) -> tuple[str, dict]:
    return await ask_news_intelligence_raw(messages, model=model, timeout=timeout_seconds)


def normalize_news_item(raw_item: dict) -> NormalizedNewsItem | None:
    title = _clean_text(raw_item.get("title"))
    if not title:
        return None
    url = _clean_text(raw_item.get("link") or raw_item.get("url"))
    source = _clean_text(raw_item.get("source")) or None
    summary = _clean_text(raw_item.get("summary") or raw_item.get("description")) or None
    published_at = _parse_published_at(raw_item.get("published_at") or raw_item.get("published"))
    published = _clean_text(raw_item.get("published")) or (
        published_at.isoformat() if published_at else ""
    )
    compatibility_item = {
        "title": title,
        "source": source or "",
        "link": url,
        "url": url,
        "summary": summary or "",
        "published": published,
        "published_at": published_at,
    }
    news_key = make_news_key(compatibility_item)
    if not news_key:
        return None
    return NormalizedNewsItem(
        title=title,
        source=source,
        url=url,
        summary=summary,
        published_at=published_at,
        published=published,
        news_key=news_key,
    )


def build_llm_payload(item: NormalizedNewsItem) -> dict:
    return {
        "title": item.title[:240],
        "source": item.source or "",
        "url": item.url[:500],
        "summary": (item.summary or "")[:500],
        "published_at": item.published_at.isoformat() if item.published_at else "",
        "allowed_symbols": sorted(ALLOWED_SYMBOLS),
    }


def build_llm_messages(payload: dict) -> list[dict]:
    instruction = (
        "Return strict compact JSON only. Classify one RSS crypto news item. "
        "No reasoning. Summary and alert_reason max 240 chars."
    )
    schema = (
        'Fields: summary, category, related_symbols, primary_symbol, impact_score, '
        'impact_level, relevance_score, is_noise, is_alert_worthy, alert_reason, dedup_hint. '
        'Categories: regulation, exchange, security, macro, etf, whale, project, technical, '
        'market, noise. Impact levels: low, medium, high, critical.'
    )
    return [
        {"role": "system", "content": "You are a careful crypto news classifier."},
        {
            "role": "user",
            "content": f"{instruction}\n{schema}\nInput: {json.dumps(payload, sort_keys=True)}",
        },
    ]


def validate_llm_output(parsed: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object.")
    impact_score = _clamp_score(parsed.get("impact_score"))
    relevance_score = _clamp_score(parsed.get("relevance_score"))
    is_noise = bool(parsed.get("is_noise"))
    category = str(parsed.get("category") or "").strip().lower()
    if category not in ALLOWED_CATEGORIES:
        category = "noise" if is_noise else "market"
    if category == "noise":
        is_noise = True
    impact_level = str(parsed.get("impact_level") or "").strip().lower()
    if impact_level not in ALLOWED_IMPACT_LEVELS:
        impact_level = derive_impact_level(impact_score)
    raw_related_symbols = parsed.get("related_symbols")
    if not isinstance(raw_related_symbols, list):
        raw_related_symbols = []
    related_symbols = [
        symbol
        for symbol in dict.fromkeys(
            str(symbol).strip().lower() for symbol in raw_related_symbols
        )
        if symbol in ALLOWED_SYMBOLS
    ]
    primary_symbol = str(parsed.get("primary_symbol") or "").strip().lower() or None
    if primary_symbol not in ALLOWED_SYMBOLS:
        primary_symbol = related_symbols[0] if related_symbols else None
    is_alert_worthy = bool(parsed.get("is_alert_worthy")) and not is_noise
    return {
        "summary": _clean_text(parsed.get("summary"))[:240],
        "category": category,
        "related_symbols": related_symbols,
        "primary_symbol": primary_symbol,
        "impact_score": impact_score,
        "impact_level": impact_level,
        "relevance_score": relevance_score,
        "is_noise": is_noise,
        "is_alert_worthy": is_alert_worthy,
    }


def derive_impact_level(score: int) -> str:
    if score <= 24:
        return "low"
    if score <= 59:
        return "medium"
    if score <= 84:
        return "high"
    return "critical"


def is_obvious_noise(item: NormalizedNewsItem) -> bool:
    text = f"{item.title} {item.summary or ''}".lower()
    return any(re.search(pattern, text) for pattern in NOISE_PATTERNS)


def build_pre_llm_dedup_group_id(item: NormalizedNewsItem) -> str:
    normalized_title = _normalize_for_hash(item.title)
    if normalized_title:
        return "title:" + hashlib.sha256(normalized_title.encode("utf-8")).hexdigest()[:32]
    return item.news_key[:64]


def build_post_llm_dedup_group_id(dedup_hint: str, fallback: str) -> str:
    normalized_hint = _normalize_for_hash(dedup_hint)
    if not normalized_hint:
        return fallback
    return "hint:" + hashlib.sha256(normalized_hint.encode("utf-8")).hexdigest()[:32]


def _parse_published_at(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = _clean_text(value)
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _clean_text(value: Any) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def _normalize_for_hash(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _hash_json(value: dict) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _clamp_score(value: Any) -> int:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def _safe_error(error: Exception, max_chars: int = 300) -> str:
    return " ".join(str(error).split())[:max_chars]
