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
from bot.domain.supported_coins import SUPPORTED_COINS, SUPPORTED_SYMBOLS
from bot.news import fetch_news_context, remember_news_context
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
from bot.services.price_service import get_coin_market_data_batch


class MarketReportDataUnavailable(RuntimeError):
    """Raised when report generation has no usable market data."""


REPORT_COOLDOWN_SECONDS = 60
REPORT_RATE_LIMIT_PRUNE_AFTER_SECONDS = 3600
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

    async with _report_generation_locks[report_type]:
        cached = await _get_fresh_cached_report(report_type)
        if cached is not None:
            return cached
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
        message = sanitize_alert_message(decision.telegram_message)
        await remember_news_context(news_items)
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
            log(f"{report_type.capitalize()} report schema validation failed: {error}")
            await mark_llm_usage_log_status(
                usage_log_id,
                status="schema_error",
                error_reason="schema validation failed",
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
            error_message=classify_ai_error_reason(error),
        )
    except MarketReportDataUnavailable as error:
        log(f"{report_type.capitalize()} report generation skipped: {error}")
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
    except Exception as error:
        log(f"{report_type.capitalize()} report generation failed: {error}")
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
    market_data = await get_coin_market_data_batch(symbols)
    if not _has_usable_market_data(market_data):
        raise MarketReportDataUnavailable("market data unavailable")
    news_items = await fetch_news_context(limit=6, prefer_unseen=True)
    return (
        {
            "report_type": report_type,
            "generated_at": generated_at.isoformat(),
            "active_symbols": [symbol.upper() for symbol in symbols],
            "coins": [
                {
                    "symbol": symbol.upper(),
                    "name": str(SUPPORTED_COINS[symbol]["name"]),
                    "price": _round_optional((market_data.get(symbol) or {}).get("price")),
                    "change_24h": _round_optional(
                        (market_data.get(symbol) or {}).get("change_24h")
                    ),
                    "change_7d": _round_optional((market_data.get(symbol) or {}).get("change_7d")),
                }
                for symbol in symbols
            ],
            "news": [
                {
                    "news_id": str(index + 1),
                    "title": str(item.get("title", "")).strip()[:180],
                    "source": str(item.get("source", "")).strip()[:80],
                    "link": str(item.get("link", "")).strip(),
                }
                for index, item in enumerate(news_items[:6])
                if str(item.get("title", "")).strip()
            ],
        },
        news_items,
    )


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
