from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import timedelta
from typing import Any

from bot.alerting.market_report import (
    MarketReportDecision,
    MarketReportValidationError,
    validate_market_report_output,
)
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
from bot.services.llm.telemetry import safe_error_message
from bot.services.price_service import CoinGeckoRateLimitError, get_report_market_data_batch


class MarketReportDataUnavailable(RuntimeError):
    """Raised when report generation has no usable market data."""


logger = logging.getLogger(__name__)

REPORT_COOLDOWN_SECONDS = 60
REPORT_RATE_LIMIT_PRUNE_AFTER_SECONDS = 3600
REPORT_PROVIDER_BACKOFF_SECONDS = 300
REPORT_FRESHNESS_SECONDS = {"daily": 4 * 3600, "weekly": 24 * 3600}
DETERMINISTIC_REPORT_PROVIDER = "deterministic"
DETERMINISTIC_REPORT_MODEL = "deterministic-market-report-v1"
# The scheduled cache-refresh jobs fire at exactly the cache expiry interval (daily 4h,
# weekly 24h), so at fire time the previous cache is always fresh by only a few seconds.
# Without this grace the job skips, the cache expires right after, and the effective
# regeneration cadence doubles (weekly: ~48h observed in production). A scheduled refresh
# therefore regenerates when the cache expires within this grace window.
REPORT_SCHEDULED_REFRESH_GRACE_SECONDS = 1800
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


def _sanitize_schema_failure_detail(error: Exception) -> str:
    """Collapse a validation message to one log-safe token.

    Validation messages are built from field names and fixed phrases (never payload
    content); this normalizes them for key=value log parsing as defense-in-depth.
    """
    text = " ".join(str(error).split()).replace("'", "").replace('"', "")
    return text[:160].replace(" ", "_")


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


def _report_cache_timestamps(report: MarketReport | dict[str, Any]) -> tuple[Any, Any]:
    """Return timezone-aware (generated_at, expires_at) for a DB or in-memory report."""
    if isinstance(report, dict):
        generated_at = report.get("generated_at")
        expires_at = report.get("expires_at")
    else:
        generated_at = getattr(report, "generated_at", None)
        expires_at = getattr(report, "expires_at", None)
    now_tzinfo = utc_now().tzinfo
    if generated_at is not None and generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=now_tzinfo)
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now_tzinfo)
    return generated_at, expires_at


def _scheduled_refresh_can_skip(report: MarketReport | dict[str, Any]) -> bool:
    """True when the cached report survives past the scheduled-refresh grace window."""
    _, expires_at = _report_cache_timestamps(report)
    if expires_at is None:
        return False
    remaining_seconds = (expires_at - utc_now()).total_seconds()
    return remaining_seconds > REPORT_SCHEDULED_REFRESH_GRACE_SECONDS


def _log_scheduled_refresh_skip(report_type: str, report: MarketReport | dict[str, Any]) -> None:
    generated_at, _ = _report_cache_timestamps(report)
    cache_age_seconds = (
        int((utc_now() - generated_at).total_seconds()) if generated_at is not None else "unknown"
    )
    log(
        "ops_event=market_report_refresh_skipped "
        f"report_type={report_type} cache_age_seconds={cache_age_seconds} "
        f"expiry_seconds={_freshness_seconds(report_type)}"
    )


async def refresh_report_cache_scheduled(report_type: str) -> MarketReport | dict[str, Any] | None:
    """Scheduled cache refresh: regenerate unless the cache stays fresh past the grace window.

    Unlike the on-command path, the scheduled job regenerates a cache that is expired *or*
    expiring within ``REPORT_SCHEDULED_REFRESH_GRACE_SECONDS``, and never skips silently:
    a kept cache is logged as ``market_report_refresh_skipped`` with its age.
    """
    report_type = _validate_report_type(report_type)
    cached = await _get_fresh_cached_report(report_type)
    if cached is not None and _scheduled_refresh_can_skip(cached):
        _log_scheduled_refresh_skip(report_type, cached)
        return cached
    if _is_report_provider_backoff_active(report_type):
        log(f"ops_event=market_report_skipped report_type={report_type} reason=provider_backoff")
        return None

    async with _report_generation_locks[report_type]:
        cached = await _get_fresh_cached_report(report_type)
        if cached is not None and _scheduled_refresh_can_skip(cached):
            _log_scheduled_refresh_skip(report_type, cached)
            return cached
        if _is_report_provider_backoff_active(report_type):
            log(
                "ops_event=market_report_skipped "
                f"report_type={report_type} reason=provider_backoff"
            )
            return None
        return await generate_report_cache(report_type)


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

    def _schema_check(parsed: dict) -> None:
        # Run report schema validation during the provider pass so a schema-invalid answer
        # from one provider falls back to the next provider before the deterministic fallback.
        try:
            validate_market_report_output(
                parsed,
                expected_report_type=report_type,
                active_symbols=SUPPORTED_SYMBOLS,
            )
        except MarketReportValidationError as error:
            raise AISchemaValidationError(str(error)) from error

    try:
        input_payload, news_items = await _build_market_report_input(report_type, generated_at)
        raw_input_json = json.dumps(input_payload, ensure_ascii=False, sort_keys=True)
        llm_result = await ask_market_report_raw(input_payload, schema_check=_schema_check)
        usage_log_id = getattr(llm_result, "usage_log_id", None)
        report_provider = getattr(llm_result, "provider", None) or "groq"
        report_model = getattr(llm_result, "model", None) or GROQ_REPORT_MODEL
        raw_output_json, parsed = llm_result
        decision = validate_market_report_output(
            parsed,
            expected_report_type=report_type,
            active_symbols=SUPPORTED_SYMBOLS,
        )
        message = _build_report_telegram_message(
            report_type=report_type,
            input_payload=input_payload,
            decision=decision,
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
            provider=report_provider,
            model=report_model,
        )
    except (AIInvalidJsonError, AISchemaValidationError, MarketReportValidationError) as error:
        if isinstance(error, (AISchemaValidationError, MarketReportValidationError)):
            # detail carries the sanitized validation reason (field names and kinds only,
            # never payload content) so recurring schema_error events stay diagnosable.
            logger.warning(
                "ops_event=market_report_failed report_type=%s reason=schema_error detail=%s",
                report_type,
                _sanitize_schema_failure_detail(error),
            )
            await mark_llm_usage_log_status(
                usage_log_id,
                status="schema_error",
                error_reason="schema_validation_failed",
                error_message=safe_error_message(error),
            )
        raw_output_json = getattr(error, "raw_content", raw_output_json)
        if raw_input_json:
            try:
                input_payload = json.loads(raw_input_json)
            except json.JSONDecodeError:
                input_payload = None
            if isinstance(input_payload, dict):
                fallback_decision = _build_deterministic_report_decision(
                    report_type,
                    input_payload,
                )
                message = _build_report_telegram_message(
                    report_type=report_type,
                    input_payload=input_payload,
                    decision=fallback_decision,
                )
                await remember_news_context(news_items)
                reason = classify_ai_error_reason(error)
                if isinstance(error, MarketReportValidationError):
                    reason = "schema_validation_failed"
                log(
                    "ops_event=market_report_generated "
                    f"report_type={report_type} status=completed fallback=deterministic "
                    f"reason={reason.replace(' ', '_')}"
                )
                return await _save_or_remember_report(
                    report_type=report_type,
                    generated_at=generated_at,
                    expires_at=expires_at,
                    status="completed",
                    raw_input_json=raw_input_json,
                    raw_output_json=raw_output_json,
                    telegram_message=message,
                    error_message=f"deterministic fallback after {reason}",
                    provider=DETERMINISTIC_REPORT_PROVIDER,
                    model=DETERMINISTIC_REPORT_MODEL,
                )
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
        logger.warning(
            "ops_event=market_report_failed report_type=%s reason=data_unavailable",
            report_type,
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
        logger.warning(
            "ops_event=market_report_failed report_type=%s reason=coingecko_rate_limit",
            report_type,
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
        logger.warning(
            "ops_event=market_report_failed report_type=%s reason=%s",
            report_type,
            classify_ai_error_reason(error).replace(" ", "_"),
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
    await refresh_report_cache_scheduled("daily")


async def generate_weekly_report_cache_job(context=None) -> None:
    await refresh_report_cache_scheduled("weekly")


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
    provider: str = "groq",
    model: str = GROQ_REPORT_MODEL,
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
                provider=provider,
                model=model,
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
        "provider": provider,
        "model": model,
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
            "weekly_context": _build_weekly_context(market_data)
            if report_type == "weekly"
            else {},
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
        "weekly_start": _round_optional(coin_data.get("weekly_start")),
        "weekly_end": _round_optional(coin_data.get("weekly_end")),
        "weekly_high": _round_optional(coin_data.get("weekly_high")),
        "weekly_low": _round_optional(coin_data.get("weekly_low")),
        "range_position": _round_optional(coin_data.get("range_position")),
    }


def _build_weekly_context(market_data: dict[str, dict[str, Any]]) -> dict:
    scoreboard = [
        _build_weekly_coin_context(symbol, market_data.get(symbol) or {})
        for symbol in SUPPORTED_SYMBOLS
    ]
    btc_change_7d = next(
        (
            item.get("change_7d")
            for item in scoreboard
            if item.get("symbol") == "BTC" and item.get("change_7d") is not None
        ),
        None,
    )
    for item in scoreboard:
        change_7d = item.get("change_7d")
        item["vs_btc_7d"] = (
            _round_optional(float(change_7d) - float(btc_change_7d))
            if change_7d is not None and btc_change_7d is not None and item.get("symbol") != "BTC"
            else None
        )
    timeline = _build_weekly_timeline(scoreboard)
    return {
        "scoreboard": scoreboard,
        "breadth": _build_weekly_breadth(scoreboard),
        "timeline": timeline,
    }


def _build_weekly_coin_context(symbol: str, coin_data: dict[str, Any]) -> dict:
    weekly_start = _round_optional(coin_data.get("weekly_start"))
    weekly_end = _round_optional(coin_data.get("weekly_end"))
    weekly_high = _round_optional(coin_data.get("weekly_high"))
    weekly_low = _round_optional(coin_data.get("weekly_low"))
    change_7d = _round_optional(coin_data.get("change_7d"))
    range_label = _format_range_position(coin_data.get("range_position"))
    return {
        "symbol": display_symbol(symbol),
        "weekly_start": weekly_start,
        "weekly_end": weekly_end,
        "weekly_high": weekly_high,
        "weekly_low": weekly_low,
        "change_7d": change_7d,
        "range_label": range_label or "weekly range unavailable from provider",
        "timeline_note": _weekly_coin_timeline_note(symbol, coin_data),
    }


def _weekly_coin_timeline_note(symbol: str, coin_data: dict[str, Any]) -> str:
    sparkline = coin_data.get("sparkline_7d")
    if not isinstance(sparkline, list) or len(sparkline) < 2:
        return f"{display_symbol(symbol)}: 7d path unavailable from provider"
    prices = [float(value) for value in sparkline if isinstance(value, int | float)]
    if len(prices) < 2:
        return f"{display_symbol(symbol)}: 7d path unavailable from provider"
    midpoint = prices[len(prices) // 2]
    return (
        f"{display_symbol(symbol)}: week opened near {_format_price(prices[0])}, "
        f"midweek near {_format_price(midpoint)}, now near {_format_price(prices[-1])}"
    )


def _build_weekly_breadth(scoreboard: list[dict]) -> dict:
    changes = [
        (str(item.get("symbol")), float(item["change_7d"]))
        for item in scoreboard
        if item.get("change_7d") is not None
    ]
    if not changes:
        return {
            "summary": "Weekly breadth unavailable from provider",
            "leaders": [],
            "laggards": [],
        }
    ordered = sorted(changes, key=lambda item: item[1], reverse=True)
    positive_count = sum(1 for _, change in changes if change > 0)
    leaders = [symbol for symbol, _ in ordered[:2]]
    laggards = [symbol for symbol, _ in ordered[-2:]]
    return {
        "summary": (
            f"{positive_count}/{len(changes)} tracked assets are positive over 7d; "
            f"leaders: {', '.join(leaders)}; laggards: {', '.join(laggards)}"
        ),
        "leaders": leaders,
        "laggards": laggards,
    }


def _build_weekly_timeline(scoreboard: list[dict]) -> list[str]:
    timeline = [
        str(item.get("timeline_note"))
        for item in scoreboard
        if str(item.get("timeline_note") or "").strip()
    ]
    return timeline or ["No strong tracked weekly catalyst in selected news"]


def _build_report_telegram_message(
    *,
    report_type: str,
    input_payload: dict,
    decision: MarketReportDecision,
) -> str:
    is_weekly = report_type == "weekly"
    # Keep user-visible report news tied to selected title/source/link items, not model prose.
    news_context_text = _format_report_news_context(input_payload)
    coin_rows = [
        _format_coin_row(coin, weekly=is_weekly)
        for coin in input_payload.get("coins", [])
        if isinstance(coin, dict)
    ]
    if is_weekly:
        message = _build_weekly_report_message(
            decision=decision,
            coin_rows=coin_rows,
            news_context_text=news_context_text,
            weekly_context=input_payload.get("weekly_context"),
        )
    else:
        message = _build_daily_report_message(
            decision=decision,
            coin_rows=coin_rows,
            news_context_text=news_context_text,
        )
    return sanitize_alert_message(message)


def _build_deterministic_report_decision(
    report_type: str,
    input_payload: dict,
) -> MarketReportDecision:
    coins = [coin for coin in input_payload.get("coins", []) if isinstance(coin, dict)]
    market_pulse = _deterministic_market_pulse(coins, weekly=report_type == "weekly")
    coin_cards = [
        {
            "symbol": str(coin.get("symbol") or "").upper(),
            "summary": _deterministic_coin_summary(coin, weekly=report_type == "weekly"),
            "watch": "Watch whether the next update confirms or fades this move.",
        }
        for coin in coins
        if str(coin.get("symbol") or "").strip()
    ]
    dashboard = [_format_coin_row(coin, weekly=report_type == "weekly") for coin in coins]
    if report_type == "weekly":
        weekly_context = input_payload.get("weekly_context")
        timeline = (
            weekly_context.get("timeline")
            if isinstance(weekly_context, dict)
            and isinstance(weekly_context.get("timeline"), list)
            else []
        )
        themes = [
            "Tracked assets were reviewed from available price and news data.",
            "Fallback report used deterministic market data because model output was malformed.",
        ]
        return MarketReportDecision(
            report_type="weekly",
            title="Weekly Market Report",
            market_pulse=market_pulse,
            dashboard=dashboard or ["Tracked market data is temporarily limited."],
            coin_cards=coin_cards,
            market_catalysts=[],
            why_it_matters="A data-only fallback avoids relying on malformed model output.",
            watch_next="Monitor whether next week's data confirms the current direction.",
            week_timeline=timeline or ["No strong tracked weekly catalyst in selected news"],
            themes=themes,
            next_week_focus="Watch whether market breadth improves across tracked assets.",
        )
    return MarketReportDecision(
        report_type="daily",
        title="Daily Market Report",
        market_pulse=market_pulse,
        dashboard=dashboard or ["Tracked market data is temporarily limited."],
        coin_cards=coin_cards,
        market_catalysts=[],
        why_it_matters="A data-only fallback avoids relying on malformed model output.",
        watch_next="Monitor whether the next update confirms or fades the current move.",
        week_timeline=[],
        themes=[],
        next_week_focus="",
    )


def _deterministic_market_pulse(coins: list[dict], *, weekly: bool) -> str:
    key = "change_7d" if weekly else "change_24h"
    moves = [
        (str(coin.get("symbol") or "").upper(), float(coin[key]))
        for coin in coins
        if coin.get(key) is not None and str(coin.get("symbol") or "").strip()
    ]
    if not moves:
        return "Tracked market data is available, but direction is limited."
    leaders = sorted(moves, key=lambda item: item[1], reverse=True)
    strongest = leaders[0]
    weakest = leaders[-1]
    return (
        f"{strongest[0]} is the strongest tracked asset at {strongest[1]:+.1f}%, "
        f"while {weakest[0]} is weakest at {weakest[1]:+.1f}%."
    )


def _deterministic_coin_summary(coin: dict, *, weekly: bool) -> str:
    symbol = str(coin.get("symbol") or "").upper()
    price = _format_price(coin.get("price"))
    change_key = "change_7d" if weekly else "change_24h"
    change_label = "7d" if weekly else "24h"
    change = _format_percent(coin.get(change_key))
    return f"{symbol} is near {price}, with {change_label} change at {change}."


def _build_daily_report_message(
    *,
    decision: MarketReportDecision,
    coin_rows: list[str],
    news_context_text: str,
) -> str:
    moved_today = _format_report_section_items(
        [*decision.dashboard, *decision.market_catalysts, decision.why_it_matters],
        fallback=decision.why_it_matters,
    )
    message = (
        "📊 Daily Market Report\n\n"
        "Market pulse:\n"
        f"{decision.market_pulse}\n\n"
        "Dashboard:\n"
        f"{_format_report_section_items(decision.dashboard)}\n\n"
        "Tracked assets:\n"
        f"{chr(10).join(coin_rows)}\n\n"
        "What moved today:\n"
        f"{moved_today}\n\n"
        "Coin-specific news:\n"
        f"{news_context_text}\n\n"
        "What to watch next:\n"
        f"{decision.watch_next}\n\n"
        "Not financial advice."
    )
    return message


def _build_weekly_report_message(
    *,
    decision: MarketReportDecision,
    coin_rows: list[str],
    news_context_text: str,
    weekly_context,
) -> str:
    themes = [
        *decision.themes,
        *decision.dashboard,
        *decision.market_catalysts,
        decision.why_it_matters,
    ]
    breadth_text = _format_weekly_breadth(weekly_context)
    timeline_text = _format_weekly_timeline(weekly_context)
    message = (
        "📊 Weekly Market Report\n\n"
        "Week in one line:\n"
        f"{decision.market_pulse}\n\n"
        "Weekly scoreboard:\n"
        f"{chr(10).join(coin_rows)}\n\n"
        "Market breadth:\n"
        f"{breadth_text}\n\n"
        "Themes of the week:\n"
        f"{_format_report_section_items(themes, fallback=decision.why_it_matters)}\n\n"
        "Week timeline:\n"
        f"{timeline_text}\n\n"
        "Coin-specific recap:\n"
        f"{_format_coin_cards(decision.coin_cards)}\n\n"
        "Top catalysts of the week:\n"
        f"{news_context_text}\n\n"
        "Next week in focus:\n"
        f"{decision.next_week_focus or decision.watch_next}\n\n"
        "Not financial advice."
    )
    return message


def _format_report_section_items(items: list[str], *, fallback: str | None = None) -> str:
    rows = [str(item or "").strip() for item in items if str(item or "").strip()]
    if not rows and fallback:
        rows = [fallback.strip()]
    return "\n".join(f"• {row}" for row in rows)


def _format_coin_cards(cards: list[dict[str, str]]) -> str:
    rows = []
    for card in cards:
        symbol = str(card.get("symbol") or "").strip().upper()
        summary = str(card.get("summary") or "").strip()
        watch = str(card.get("watch") or "").strip()
        if not (symbol and summary and watch):
            continue
        rows.append(f"• {symbol}: {summary} Watch: {watch}")
    return "\n".join(rows)


def _format_weekly_breadth(weekly_context) -> str:
    if not isinstance(weekly_context, dict):
        return "• Weekly breadth unavailable from provider"
    breadth = weekly_context.get("breadth")
    if not isinstance(breadth, dict):
        return "• Weekly breadth unavailable from provider"
    summary = str(breadth.get("summary") or "").strip()
    return f"• {summary}" if summary else "• Weekly breadth unavailable from provider"


def _format_weekly_timeline(weekly_context) -> str:
    if not isinstance(weekly_context, dict):
        return "• No strong tracked weekly catalyst in selected news"
    timeline = weekly_context.get("timeline")
    if not isinstance(timeline, list):
        return "• No strong tracked weekly catalyst in selected news"
    rows = [str(item or "").strip() for item in timeline if str(item or "").strip()]
    if not rows:
        rows = ["No strong tracked weekly catalyst in selected news"]
    return "\n".join(f"• {row}" for row in rows)


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
