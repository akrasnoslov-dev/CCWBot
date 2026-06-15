"""News relevance and candidate formatting helpers for alert pipelines.

Belongs here: deterministic news relevance, symbol filtering, ordering, and
compact candidate formatting for alert LLM payloads.
Does not belong here: RSS fetching, persisted news writes, LLM calls, delivery,
or recipient eligibility.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bot.db.database import make_news_key
from bot.domain.supported_coins import SUPPORTED_COINS, normalize_symbol

# Preserve the legacy log source while this module is used through bot.alerts.
logger = logging.getLogger("bot.alerts")

COIN_ALIASES = {
    "btc": ("btc", "bitcoin"),
    "eth": ("eth", "ethereum", "ether"),
    "sol": ("sol", "solana"),
    "xrp": ("xrp", "ripple"),
    "bnb": ("bnb", "binance coin", "binancecoin"),
    "doge": ("doge", "dogecoin"),
    "ada": ("ada", "cardano"),
    "ton": (
        "ton",
        "toncoin",
        "gram",
        "$gram",
        "gram token",
        "gram usdt",
        "gram/usdt",
        "toncoin rebrand",
        "ton rebrand",
        "the open network",
    ),
    "link": ("link", "chainlink"),
    "trx": ("trx", "tron"),
}
MARKET_WIDE_NEWS_TERMS = (
    "crypto market",
    "cryptocurrency market",
    "cryptocurrencies",
    "digital asset",
    "digital assets",
    "market-wide",
    "market wide",
    "broader crypto",
    "broader cryptocurrency",
    "broader market",
    "altcoin",
    "altcoins",
    "crypto assets",
    "crypto prices",
    "crypto selloff",
    "crypto sell-off",
    "crypto rally",
    "regulation",
    "regulatory",
    "sec",
    "fed",
    "federal reserve",
    "interest rate",
    "rates",
    "macro",
    "inflation",
    "exchange",
    "hack",
    "etf",
    "dominance",
)
BTC_ONLY_NEWS_TERMS = ("bitcoin", "btc")
CLEAR_MARKET_WIDE_NEWS_TERMS = (
    "crypto market",
    "cryptocurrency market",
    "cryptocurrencies",
    "digital asset",
    "digital assets",
    "market-wide",
    "market wide",
    "broader crypto",
    "broader cryptocurrency",
    "broader market",
    "altcoin",
    "altcoins",
    "crypto assets",
    "crypto prices",
    "crypto selloff",
    "crypto sell-off",
    "crypto rally",
    "market-wide selloff",
    "market-wide rally",
)
MATERIAL_NEWS_TERMS = (
    "approval",
    "approved",
    "rejection",
    "rejected",
    "etf flow",
    "etf inflow",
    "etf outflow",
    "law passed",
    "bill passed",
    "regulation passed",
    "enforcement action",
    "lawsuit",
    "settlement",
    "major exchange",
    "outage",
    "hack",
    "bankruptcy",
    "exploit",
    "liquidation cascade",
    "central bank",
    "government statement",
    "institutional adoption",
    "institutional exit",
)
GENERIC_NEWS_TERMS = (
    "analysis",
    "analyst",
    "bear trap",
    "euphoria",
    "prediction",
    "price target",
    "could",
    "may",
    "might",
    "sentiment",
    "speculation",
    "commentary",
)
COMPANY_BACKGROUND_NEWS_TERMS = (
    "sued",
    "lawsuit",
    "pre-bankruptcy transfer",
    "transfers from",
    "revenue",
    "earnings",
    "hosting business",
    "treasury",
)
CRITICAL_NEWS_CATEGORIES = {"regulation", "exchange", "security", "macro", "etf"}
MARKET_MOVING_NEWS_TERMS = MATERIAL_NEWS_TERMS + (
    "sec",
    "federal reserve",
    "fed decision",
    "rate decision",
    "emergency",
    "halt",
    "halts",
    "freeze",
    "frozen",
    "sanction",
    "sanctions",
    "ban",
    "banned",
    "approval",
    "approved",
)

def _truncate_text(value: str, max_chars: int) -> str:
    text = value.strip()
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rstrip() + "…"

def _stable_news_link(link: str) -> str:
    parsed = urlsplit(link.strip())
    query_params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or parsed.path,
            urlencode(sorted(query_params)),
            "",
        )
    )

def _coin_name(symbol: str) -> str:
    return str(SUPPORTED_COINS[normalize_symbol(symbol)]["name"])

def _news_search_text(news_item: dict) -> str:
    title = str(news_item.get("title") or "")
    summary = str(news_item.get("summary") or "")
    return f" {title} {summary} ".lower()

def _matches_symbol_alias(symbol: str, text: str) -> bool:
    aliases = COIN_ALIASES.get(normalize_symbol(symbol), (normalize_symbol(symbol),))
    for alias in aliases:
        alias = alias.lower()
        if alias == "gram":
            if re_search_word(alias, text) and _has_gram_crypto_context(text):
                return True
            continue
        if re_search_word(alias, text):
            return True
    return False

def _has_gram_crypto_context(text: str) -> bool:
    return any(
        term in text
        for term in (
            "$gram",
            "gram token",
            "gram usdt",
            "gram/usdt",
            "toncoin",
            "ton rebrand",
            "the open network",
            "crypto",
            "cryptocurrency",
            "token",
            "blockchain",
        )
    )

def _news_metadata_matches_symbol(symbol: str, news_item: dict) -> bool:
    normalized_symbol = normalize_symbol(symbol)
    primary_symbol = str(news_item.get("primary_symbol") or "").strip().lower()
    if primary_symbol == normalized_symbol:
        return True
    related_symbols = news_item.get("related_symbols")
    if not isinstance(related_symbols, list):
        return False
    return normalized_symbol in {
        str(item or "").strip().lower() for item in related_symbols if str(item or "").strip()
    }

def _mentions_btc(text: str) -> bool:
    return any(re_search_word(term, text) for term in BTC_ONLY_NEWS_TERMS)

def _is_clearly_market_wide_news(text: str) -> bool:
    return any(term in text for term in CLEAR_MARKET_WIDE_NEWS_TERMS)

def classify_news_relevance(symbol: str, news_item: dict) -> str:
    """Classify RSS item relevance before it reaches the LLM."""
    normalized_symbol = normalize_symbol(symbol)
    if _news_metadata_matches_symbol(normalized_symbol, news_item):
        return "direct"
    text = _news_search_text(news_item)
    if _matches_symbol_alias(normalized_symbol, text):
        return "direct"
    if any(term in text for term in MARKET_WIDE_NEWS_TERMS):
        if normalized_symbol != "btc" and _mentions_btc(text):
            if not _is_clearly_market_wide_news(text):
                return "irrelevant"
        return "market_wide"
    return "irrelevant"

def is_material_news_item(news_item: dict) -> bool:
    text = _news_search_text(news_item)
    return any(term in text for term in MATERIAL_NEWS_TERMS)

def is_generic_news_item(news_item: dict) -> bool:
    text = _news_search_text(news_item)
    return any(term in text for term in GENERIC_NEWS_TERMS)

def re_search_word(term: str, text: str) -> bool:
    escaped = re.escape(term)
    if re.fullmatch(r"[a-z0-9]+", term):
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None
    return term in text

def filter_news_for_symbol(
    symbol: str,
    news_items: list[dict],
    *,
    max_direct: int = 5,
    max_market_wide: int = 3,
) -> list[dict]:
    direct: list[dict] = []
    market_wide: list[dict] = []
    for item in _sort_news_fresh_first(news_items):
        relevance = classify_news_relevance(symbol, item)
        if relevance == "direct" and len(direct) < max_direct:
            direct.append({**item, "relevance_label": "direct_symbol"})
        elif relevance == "market_wide" and len(market_wide) < max_market_wide:
            market_wide.append({**item, "relevance_label": "market_wide"})
    return direct + market_wide

def _candidate_news_relevance_label(symbol: str | None, item: dict) -> str:
    explicit_label = str(item.get("relevance_label") or "").strip().lower()
    if explicit_label:
        return explicit_label
    if not symbol:
        return ""
    relevance = classify_news_relevance(symbol, item)
    if relevance == "direct":
        return "direct_symbol"
    if relevance == "market_wide":
        return "market_wide"
    return "irrelevant"

def _log_news_selection_summary(
    *,
    symbol: str,
    source: str,
    raw_news_items: list[dict],
    selected_news_items: list[dict],
    fallback_used: bool,
    selection_stats: dict[str, int] | None = None,
) -> None:
    direct_count = 0
    market_wide_count = 0
    irrelevant_count = 0
    for item in raw_news_items:
        relevance = classify_news_relevance(symbol, item)
        if relevance == "direct":
            direct_count += 1
        elif relevance == "market_wide":
            market_wide_count += 1
        else:
            irrelevant_count += 1
    selected_titles = [
        _truncate_text(str(item.get("title") or "").strip(), 90)
        for item in selected_news_items
        if str(item.get("title") or "").strip()
    ]
    selected_labels = [
        _candidate_news_relevance_label(symbol, item) for item in selected_news_items
    ]
    logger.info(
        "related_news_selection symbol=%s source=%s candidate_count=%s "
        "direct_news_count=%s market_wide_news_count=%s irrelevant_filtered_count=%s "
        "selected_count=%s selected_news_titles=%s selected_news_relevance_labels=%s "
        "noise_filtered_count=%s dedup_filtered_count=%s fallback_used=%s",
        normalize_symbol(symbol).upper(),
        source,
        len(raw_news_items),
        direct_count,
        market_wide_count,
        irrelevant_count,
        len(selected_news_items),
        selected_titles,
        selected_labels,
        (selection_stats or {}).get("noise_filtered_count", 0),
        (selection_stats or {}).get("dedup_filtered_count", 0),
        fallback_used,
    )

def _sort_news_fresh_first(news_items: list[dict]) -> list[dict]:
    return sorted(news_items, key=_news_sort_key, reverse=True)

def _news_sort_key(item: dict) -> tuple[int, str]:
    parsed = _parse_news_datetime(item)
    timestamp = int(parsed.timestamp()) if parsed else 0
    return timestamp, make_news_key(item)

def _parse_news_datetime(item: dict) -> datetime | None:
    raw_value = (
        item.get("published_at_utc")
        or item.get("published_at")
        or item.get("published")
        or item.get("updated")
        or ""
    )
    if isinstance(raw_value, datetime):
        parsed = raw_value
    else:
        value = str(raw_value).strip()
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
            except (TypeError, ValueError):
                return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def _news_within_hours(news_items: list[dict], *, now: datetime, hours: int) -> list[dict]:
    cutoff = now.astimezone(timezone.utc) - timedelta(hours=hours)
    recent = []
    for item in news_items:
        published_at = _parse_news_datetime(item)
        if published_at is None or published_at >= cutoff:
            recent.append(item)
    return recent

def _news_id(index: int) -> str:
    return f"n{index + 1}"

def _format_candidate_news(
    news_items: list[dict],
    *,
    preserve_order: bool = False,
    symbol: str | None = None,
) -> list[dict]:
    candidates: list[dict] = []
    seen_keys: set[str] = set()
    ordered_items = news_items if preserve_order else _sort_news_fresh_first(news_items)
    for item in ordered_items:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        stable_key = make_news_key(item)
        dedupe_key = stable_key or title.lower()
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        candidates.append(
            {
                "news_id": _news_id(len(candidates)),
                "source": str(item.get("source") or "").strip() or "Unknown source",
                "title": title,
                "published_at": str(
                    item.get("published_at")
                    or item.get("published_at_utc")
                    or item.get("published")
                    or ""
                ),
                "url": str(item.get("url") or item.get("link") or "").strip(),
                "summary": str(item.get("summary") or "").strip(),
                "relevance_label": _candidate_news_relevance_label(symbol, item),
            }
        )
    return candidates

def _news_driven_identity(news_item: dict) -> str:
    return str(
        news_item.get("dedup_group_id")
        or news_item.get("news_key")
        or news_item.get("news_item_id")
        or make_news_key(news_item)
    ).strip()

def _news_symbols(news_item: dict, field_name: str) -> set[str]:
    raw_values = news_item.get(field_name)
    if not isinstance(raw_values, list):
        return set()
    return {
        normalized
        for item in raw_values
        if (normalized := normalize_symbol(str(item or "")))
    }

def _news_text(news_item: dict) -> str:
    return " ".join(
        str(news_item.get(field_name) or "")
        for field_name in ("title", "summary", "source")
    ).lower()
