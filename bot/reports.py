from __future__ import annotations

import asyncio
import json
import time
from datetime import timedelta
from typing import Any

from bot.alerting.market_report import MarketReportValidationError, validate_market_report_output
from bot.db.database import (
    MarketReport,
    get_latest_market_report,
    save_market_report,
    utc_now,
)
from bot.domain.supported_coins import (
    SUPPORTED_SYMBOLS,
    coin_display_name,
    display_symbol,
)
from bot.news import fetch_report_news_context, remember_news_context
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log
from bot.services.ai_agent_groq import (
    GROQ_REPORT_MODEL,
    AIInvalidJsonError,
    AISchemaValidationError,
    ask_market_report_raw,
    classify_ai_error_reason,
    mark_llm_usage_log_status,
    sanitize_alert_message,
)
from bot.services.price_service import CoinGeckoRateLimitError, get_report_market_data_batch


class MarketReportDataUnavailable(RuntimeError):
    """Raised when report generation has no usable market data."""


REPORT_COOLDOWN_SECONDS = 60
REPORT_RATE_LIMIT_PRUNE_AFTER_SECONDS = 3600
REPORT_PROVIDER_BACKOFF_SECONDS = 300
REPORT_FRESHNESS_SECONDS = {"daily": 4 * 3600, "weekly": 24 * 3600}
REPORT_UNAVAILABLE_MESSAGES = {
    "daily": "Daily report is temporarily unavailable. Please try again later.",
    "weekly": "Weekly report is temporarily unavailable. Please try again later.",
}
_last_report_call: dict[tuple[int, str], float] = {}
_report_generation_locks = {
    "daily": asyncio.Lock(),
    "weekly": asyncio.Lock(),
}
_memory_report_cache: dict[str, dict[str, Any]] = {}
_report_provider_backoff_until: dict[str, float] = {}


def _target_chat_id(target) -> int | None:
    chat_id = getattr(target, "chat_id", None)
    if chat_id is not None:
        return int(chat_id)
    chat = getattr(target, "chat", None)
    chat_id = getattr(chat, "id", None)
    return int(chat_id) if chat_id is not None else None


def _is_report_rate_limited(chat_id: int | None, report_type: str) -> bool:
    if chat_id is None:
        return False
    now = time.monotonic()
    stale_before = now - REPORT_RATE_LIMIT_PRUNE_AFTER_SECONDS
    for key, last_seen_at in list(_last_report_call.items()):
        if last_seen_at < stale_before:
            _last_report_call.pop(key, None)
    key = (chat_id, report_type)
    last_call_at = _last_report_call.get(key)
    if last_call_at is not None and now - last_call_at < REPORT_COOLDOWN_SECONDS:
        return True
    _last_report_call[key] = now
    return False


def _freshness_seconds(report_type: str) -> int:
    return REPORT_FRESHNESS_SECONDS[report_type]


def _is_report_provider_backoff_active(report_type: str) -> bool:
    backoff_until = _report_provider_backoff_until.get(report_type)
    if backoff_until is None:
        return False
    if backoff_until <= time.monotonic():
        _report_provider_backoff_until.pop(report_type, None)
        return False
    return True


def _start_report_provider_backoff(report_type: str) -> None:
    _report_provider_backoff_until[report_type] = (
        time.monotonic() + REPORT_PROVIDER_BACKOFF_SECONDS
    )


def _is_fresh_report(report: MarketReport | None) -> bool:
    if report is None or report.status != "completed" or not report.telegram_message:
        return False
    expires_at = report.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=utc_now().tzinfo)
    return expires_at > utc_now()


def _is_fresh_memory_report(report: dict[str, Any] | None) -> bool:
    return bool(
        report
        and report.get("status") == "completed"
        and report.get("telegram_message")
        and report.get("expires_at") > utc_now()
    )


async def get_or_generate_report(report_type: str) -> MarketReport | dict[str, Any] | None:
    """Return a fresh cached report, generating one global report if needed."""
    report_type = _validate_report_type(report_type)
    cached = await _get_fresh_cached_report(report_type)
    if cached is not None:
        return cached
    if _is_report_provider_backoff_active(report_type):
        log(f"ops_event=market_report_skipped report_type={report_type} reason=provider_backoff")
        return None

    async with _report_generation_locks[report_type]:
        cached = await _get_fresh_cached_report(report_type)
        if cached is not None:
            return cached
        if _is_report_provider_backoff_active(report_type):
            log(
                "ops_event=market_report_skipped "
                f"report_type={report_type} reason=provider_backoff"
            )
            return None
        return await generate_report_cache(report_type)


async def generate_report_cache(report_type: str) -> MarketReport | dict[str, Any] | None:
    """Generate one market-wide LLM report and cache the completed or failed attempt."""
    report_type = _validate_report_type(report_type)
    generated_at = utc_now()
    expires_at = generated_at + timedelta(seconds=_freshness_seconds(report_type))
    raw_input_json: str | None = None
    raw_output_json: str | None = None
    usage_log_id: int | None = None

    try:
        input_payload, news_items = await _build_market_report_input(report_type, generated_at)
        raw_input_json = json.dumps(input_payload, ensure_ascii=False, sort_keys=True)
        llm_result = await ask_market_report_raw(input_payload)
        usage_log_id = getattr(llm_result, "usage_log_id", None)
        raw_output_json, parsed = llm_result
        decision = validate_market_report_output(
            parsed,
            expected_report_type=report_type,
            active_symbols=SUPPORTED_SYMBOLS,
        )
        message = _build_report_telegram_message(
            report_type=report_type,
            input_payload=input_payload,
            market_overview=decision.market_overview,
            news_context=decision.news_context,
            possible_action=decision.possible_action,
        )
        await remember_news_context(news_items)
        log(f"ops_event=market_report_generated report_type={report_type} status=completed")
        return await _save_or_remember_report(
            report_type=report_type,
            generated_at=generated_at,
            expires_at=expires_at,
            status="completed",
            raw_input_json=raw_input_json,
            raw_output_json=raw_output_json,
            telegram_message=message,
            error_message=None,
        )
    except (AIInvalidJsonError, AISchemaValidationError, MarketReportValidationError) as error:
        if isinstance(error, MarketReportValidationError):
            log(
                "ops_event=market_report_failed "
                f"report_type={report_type} reason=schema_error"
            )
            await mark_llm_usage_log_status(
                usage_log_id,
                status="schema_error",
                error_reason="schema_validation_failed",
                error_message=str(error)[:500],
            )
        raw_output_json = getattr(error, "raw_content", raw_output_json)
        return await _save_or_remember_report(
            report_type=report_type,
            generated_at=generated_at,
            expires_at=expires_at,
            status="failed",
            raw_input_json=raw_input_json,
            raw_output_json=raw_output_json,
            telegram_message=None,
            error_message=str(error),
        )
    except MarketReportDataUnavailable:
        log(
            "ops_event=market_report_failed "
            f"report_type={report_type} reason=data_unavailable"
        )
        return await _save_or_remember_report(
            report_type=report_type,
            generated_at=generated_at,
            expires_at=expires_at,
            status="failed",
            raw_input_json=raw_input_json,
            raw_output_json=raw_output_json,
            telegram_message=None,
            error_message="market data unavailable",
        )
    except CoinGeckoRateLimitError:
        _start_report_provider_backoff(report_type)
        log(
            "ops_event=market_report_failed "
            f"report_type={report_type} reason=coingecko_rate_limit"
        )
        return await _save_or_remember_report(
            report_type=report_type,
            generated_at=generated_at,
            expires_at=expires_at,
            status="failed",
            raw_input_json=raw_input_json,
            raw_output_json=raw_output_json,
            telegram_message=None,
            error_message="coingecko rate limit",
        )
    except Exception as error:
        log(
            "ops_event=market_report_failed "
            f"report_type={report_type} reason={classify_ai_error_reason(error).replace(' ', '_')}"
        )
        return await _save_or_remember_report(
            report_type=report_type,
            generated_at=generated_at,
            expires_at=expires_at,
            status="failed",
            raw_input_json=raw_input_json,
            raw_output_json=raw_output_json,
            telegram_message=None,
            error_message=classify_ai_error_reason(error),
        )


async def generate_daily_report_cache_job(context=None) -> None:
    await get_or_generate_report("daily")


async def generate_weekly_report_cache_job(context=None) -> None:
    await get_or_generate_report("weekly")


async def send_daily_report_message(target) -> None:
    await _send_report_message(target, "daily")


async def send_weekly_report_message(target) -> None:
    await _send_report_message(target, "weekly")


async def _send_report_message(target, report_type: str) -> None:
    chat_id = _target_chat_id(target)
    if _is_report_rate_limited(chat_id, report_type):
        await target.reply_text(
            f"Please wait a minute before requesting another {report_type} report."
        )
        return

    report = await get_or_generate_report(report_type)
    message = getattr(report, "telegram_message", None)
    if isinstance(report, dict):
        message = report.get("telegram_message")
    if message:
        await target.reply_text(str(message))
        return

    await target.reply_text(REPORT_UNAVAILABLE_MESSAGES[report_type])


async def _get_fresh_cached_report(report_type: str) -> MarketReport | dict[str, Any] | None:
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            report = await get_latest_market_report(
                session,
                report_type=report_type,
                statuses={"completed"},
            )
            return report if _is_fresh_report(report) else None

    report = _memory_report_cache.get(report_type)
    return report if _is_fresh_memory_report(report) else None


async def _save_or_remember_report(
    *,
    report_type: str,
    generated_at,
    expires_at,
    status: str,
    raw_input_json: str | None,
    raw_output_json: str | None,
    telegram_message: str | None,
    error_message: str | None,
) -> MarketReport | dict[str, Any]:
    if DB_ENABLED and DB_SESSION_LOCAL:
        async with DB_SESSION_LOCAL() as session:
            return await save_market_report(
                session,
                report_type=report_type,
                generated_at=generated_at,
                expires_at=expires_at,
                status=status,
                raw_input_json=raw_input_json,
                raw_output_json=raw_output_json,
                telegram_message=telegram_message,
                error_message=error_message,
                provider="groq",
                model=GROQ_REPORT_MODEL,
            )

    cached = {
        "report_type": report_type,
        "generated_at": generated_at,
        "expires_at": expires_at,
        "status": status,
        "raw_input_json": raw_input_json,
        "raw_output_json": raw_output_json,
        "telegram_message": telegram_message,
        "error_message": error_message,
        "provider": "groq",
        "model": GROQ_REPORT_MODEL,
    }
    _memory_report_cache[report_type] = cached
    return cached


async def _build_market_report_input(report_type: str, generated_at) -> tuple[dict, list[dict]]:
    symbols = list(SUPPORTED_SYMBOLS)
    market_data = await get_report_market_data_batch(symbols)
    if not _has_usable_market_data(market_data):
        raise MarketReportDataUnavailable("market data unavailable")
    news_payload, news_items = await fetch_report_news_context(symbols, prefer_unseen=True)
    market_news = news_payload.get("market_news") if isinstance(news_payload, dict) else []
    coin_news = news_payload.get("coin_news") if isinstance(news_payload, dict) else {}
    news_fallback = news_payload.get("fallback") if isinstance(news_payload, dict) else ""
    return (
        {
            "report_type": report_type,
            "generated_at": generated_at.isoformat(),
            "active_symbols": [display_symbol(symbol) for symbol in symbols],
            "coins": [
                _build_report_coin_payload(symbol, market_data.get(symbol) or {})
                for symbol in symbols
            ],
            "market_news": market_news,
            "coin_news": coin_news,
            "news_fallback": news_fallback,
        },
        news_items,
    )


def _build_report_coin_payload(symbol: str, coin_data: dict[str, Any]) -> dict:
    return {
        "symbol": display_symbol(symbol),
        "name": coin_display_name(symbol),
        "price": _round_optional(coin_data.get("price")),
        "change_1h": _round_optional(coin_data.get("change_1h")),
        "change_24h": _round_optional(coin_data.get("change_24h")),
        "change_7d": _round_optional(coin_data.get("change_7d")),
        "volume_24h": _round_optional(coin_data.get("volume_24h")),
        "market_cap": _round_optional(coin_data.get("market_cap")),
        "rank": coin_data.get("rank"),
        "sparkline_7d": _format_sparkline(coin_data.get("sparkline_7d")),
        "weekly_high": _round_optional(coin_data.get("weekly_high")),
        "weekly_low": _round_optional(coin_data.get("weekly_low")),
        "range_position": _round_optional(coin_data.get("range_position")),
    }


def _build_report_telegram_message(
    *,
    report_type: str,
    input_payload: dict,
    market_overview: str,
    news_context: str,
    possible_action: str,
) -> str:
    is_weekly = report_type == "weekly"
    title = "Weekly Market Report" if is_weekly else "Daily Market Report"
    overview_label = "Weekly overview" if is_weekly else "Market overview"
    news_label = "Top catalysts of the week" if is_weekly else "News context"
    # Keep user-visible report news tied to selected title/source/link items, not model prose.
    news_context_text = _format_report_news_context(input_payload)
    coin_rows = [
        _format_coin_row(coin, weekly=is_weekly)
        for coin in input_payload.get("coins", [])
        if isinstance(coin, dict)
    ]
    message = (
        f"📊 {title}\n\n"
        f"{overview_label}:\n"
        f"{market_overview.strip()}\n\n"
        "Coins:\n"
        f"{chr(10).join(coin_rows)}\n\n"
        f"{news_label}:\n"
        f"{news_context_text}\n\n"
        "Possible action:\n"
        f"{possible_action.strip()}\n\n"
        "Not financial advice."
    )
    return sanitize_alert_message(message)


def _format_report_news_context(input_payload: dict) -> str:
    rows: list[str] = []
    market_news = input_payload.get("market_news")
    if isinstance(market_news, list):
        for item in market_news:
            if not isinstance(item, dict):
                continue
            formatted = _format_report_news_item(item)
            if formatted:
                rows.append(formatted)

    coin_news = input_payload.get("coin_news")
    if isinstance(coin_news, dict):
        for symbol in input_payload.get("active_symbols", []):
            symbol_text = str(symbol or "").strip().upper()
            items = coin_news.get(symbol_text)
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                formatted = _format_report_news_item(item, prefix=symbol_text)
                if formatted:
                    rows.append(formatted)

    if rows:
        return "\n".join(rows)

    fallback = str(input_payload.get("news_fallback") or "").strip()
    return fallback or "No clearly relevant fresh news found for tracked coins"


def _format_report_news_item(item: dict, *, prefix: str | None = None) -> str:
    title = str(item.get("title") or "").strip()
    source = str(item.get("source") or "").strip()
    link = str(item.get("link") or "").strip()
    if not (title and source and link):
        return ""
    label = f"{prefix}: " if prefix else ""
    return f"• {label}{title} ({source}) {link}"


def _format_coin_row(coin: dict, *, weekly: bool) -> str:
    symbol = str(coin.get("symbol") or "").upper()
    price = _format_price(coin.get("price"))
    change_24h = _format_percent(coin.get("change_24h"))
    if weekly:
        change_7d = _format_percent(
            coin.get("change_7d"),
            unavailable_text="unavailable from provider",
        )
        sparkline = str(coin.get("sparkline_7d") or "").strip()
        range_text = _format_range_position(coin.get("range_position"))
        suffix_parts = [part for part in (sparkline, range_text) if part]
        suffix = f", {' '.join(suffix_parts)}" if suffix_parts else ""
        return f"• {symbol}: {price}, 7d {change_7d}, 24h {change_24h}{suffix}"
    return f"• {symbol}: {price}, 24h {change_24h}"


def _format_price(value) -> str:
    if value is None:
        return "not enough data yet"
    numeric_value = float(value)
    if numeric_value.is_integer():
        return f"${numeric_value:,.0f}"
    return f"${numeric_value:,.2f}"


def _format_percent(value, *, unavailable_text: str = "not enough data yet") -> str:
    if value is None:
        return unavailable_text
    return f"{float(value):+.1f}%"


def _format_sparkline(values) -> str | None:
    if not isinstance(values, list):
        return None
    numeric_values = [
        float(value)
        for value in values
        if isinstance(value, int | float)
    ]
    if not numeric_values:
        return None
    blocks = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
    low = min(numeric_values)
    high = max(numeric_values)
    if high == low:
        return blocks[0] * min(len(numeric_values), 12)
    if len(numeric_values) > 12:
        step = (len(numeric_values) - 1) / 11
        numeric_values = [numeric_values[round(index * step)] for index in range(12)]
    return "".join(
        blocks[
            max(
                0,
                min(
                    len(blocks) - 1,
                    round(((value - low) / (high - low)) * (len(blocks) - 1)),
                ),
            )
        ]
        for value in numeric_values
    )


def _format_range_position(value) -> str | None:
    if value is None:
        return None
    numeric_value = max(0.0, min(1.0, float(value)))
    if numeric_value >= 0.75:
        return "near weekly high"
    if numeric_value <= 0.25:
        return "near weekly low"
    return "mid weekly range"


def _round_optional(value) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _has_usable_market_data(market_data: dict[str, dict[str, Any]] | None) -> bool:
    if not market_data:
        return False
    for symbol in SUPPORTED_SYMBOLS:
        coin_data = market_data.get(symbol) or {}
        if coin_data.get("price") is not None:
            return True
    return False


def _validate_report_type(report_type: str) -> str:
    normalized = report_type.strip().lower()
    if normalized not in REPORT_FRESHNESS_SECONDS:
        raise ValueError(f"Unsupported report type: {report_type}")
    return normalized
