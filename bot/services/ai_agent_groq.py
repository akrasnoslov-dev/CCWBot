"""Structured LLM facade used by Event Analysis, heartbeats, reports, and news.

The legacy threshold-driven alert-generation API was removed. Event Alert significance belongs
only to the schema-validated Event Analysis decision.
"""

import json
import logging
import os
import re

from dotenv import load_dotenv

from bot.alerting.event_identity import _json_dumps
from bot.services.llm import config as llm_config
from bot.services.llm import get_router
from bot.services.llm.env import get_int_env
from bot.services.llm.errors import AIInvalidJsonError
from bot.services.llm.errors import AIProviderRateLimitError as AIProviderRateLimitError
from bot.services.llm.errors import AISchemaValidationError as AISchemaValidationError
from bot.services.llm.errors import AllProvidersFailedError as AllProvidersFailedError
from bot.services.llm.errors import LLMRateLimitBackoffActive as LLMRateLimitBackoffActive
from bot.services.llm.telemetry import _llm_rate_limit_backoffs as _llm_rate_limit_backoffs
from bot.services.llm.telemetry import classify_ai_error_reason as classify_ai_error_reason
from bot.services.llm.telemetry import get_llm_rate_limit_backoff as get_llm_rate_limit_backoff
from bot.services.llm.telemetry import mark_llm_usage_log_status as mark_llm_usage_log_status
from bot.services.llm.telemetry import (
    reset_llm_rate_limit_backoffs as reset_llm_rate_limit_backoffs,
)
from bot.services.llm.telemetry import safe_error_message, write_llm_usage_log

load_dotenv()
logger = logging.getLogger(__name__)
SYSTEM_PROMPT = "You are a careful crypto monitoring assistant."
GROQ_MODEL = llm_config.model_for("groq", "default")
GROQ_EVENT_ANALYSIS_MODEL = llm_config.model_for("groq", "event_analysis")
GROQ_EVENT_ANALYSIS_MAX_TOKENS = llm_config.max_tokens_for("event_analysis")
GROQ_MARKET_HEARTBEAT_MODEL = llm_config.model_for("groq", "market_heartbeat")
GROQ_REPORT_MODEL = llm_config.model_for("groq", "daily_report")
GROQ_NEWS_INTELLIGENCE_MODEL = llm_config.model_for("groq", "news_intelligence")
AIGroqRateLimitError = AIProviderRateLimitError


def _get_int_env(name: str, default: int, minimum: int = 0) -> int:
    return get_int_env(name, default, minimum=minimum)


class LLMJsonResult(tuple):
    """A compatible ``(raw_content, parsed)`` result with provider attribution."""

    def __new__(
        cls,
        raw_content: str,
        parsed: dict,
        usage_log_id: int | None = None,
        *,
        provider: str | None = None,
        model: str | None = None,
    ):
        value = super().__new__(cls, (raw_content, parsed))
        value.usage_log_id, value.provider, value.model = usage_log_id, provider, model
        return value


def _json_response_validator(
    *, call_type: str, symbol: str | None, max_tokens: int, schema_check=None
):
    async def _validate(result) -> LLMJsonResult:
        raw_content = result.raw_content
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_content.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
            if not isinstance(parsed, dict):
                raise ValueError("top-level JSON is not an object")
        except (json.JSONDecodeError, ValueError) as error:
            failure = AIInvalidJsonError(str(error), raw_content=raw_content)
            failure.provider, failure.model = result.provider, result.model
            await write_llm_usage_log(
                provider=result.provider,
                call_type=call_type,
                symbol=symbol,
                model=result.model,
                status="invalid_json",
                input_chars=result.input_chars,
                output_chars=len(raw_content),
                max_tokens=getattr(result, "max_tokens", max_tokens),
                headers=result.headers,
                response=result.response,
                error_reason="invalid_json",
                error_message=safe_error_message(failure),
            )
            raise failure from error
        if schema_check is not None:
            try:
                schema_check(parsed)
            except AISchemaValidationError as error:
                error.raw_content = error.raw_content or raw_content
                error.provider, error.model = result.provider, result.model
                await write_llm_usage_log(
                    provider=result.provider,
                    call_type=call_type,
                    symbol=symbol,
                    model=result.model,
                    status="schema_error",
                    input_chars=result.input_chars,
                    output_chars=len(raw_content),
                    max_tokens=getattr(result, "max_tokens", max_tokens),
                    headers=result.headers,
                    response=result.response,
                    error_reason="schema_validation_failed",
                    error_message=safe_error_message(error),
                )
                raise
        usage_log_id = await write_llm_usage_log(
            provider=result.provider,
            call_type=call_type,
            symbol=symbol,
            model=result.model,
            status="success",
            input_chars=result.input_chars,
            output_chars=len(raw_content),
            max_tokens=getattr(result, "max_tokens", max_tokens),
            headers=result.headers,
            response=result.response,
        )
        return LLMJsonResult(
            raw_content, parsed, usage_log_id, provider=result.provider, model=result.model
        )

    return _validate


def _groq_json_mode_enabled() -> bool:
    return os.getenv("GROQ_JSON_MODE", "true").strip().lower() not in {"0", "false", "no", "off"}


def _parse_json(raw_content: str | None) -> dict | None:
    """Parse a JSON-object response without relaxing schema validation."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", str(raw_content or "").strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def sanitize_alert_message(message: str) -> str:
    """Keep user-visible LLM text concise and remove accidental diagnostic lines."""
    kept = []
    for line in str(message or "").splitlines():
        if re.search(r"(?i)\b(?:threshold|interval|previous|current)\s*=", line):
            continue
        kept.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def build_event_analysis_prompt(input_payload: dict) -> str:
    return (
        "Return valid JSON only. Write English.\n"
        "Use exactly: symbol, should_alert, event_key, title, message_body, related_news_ids, "
        "possible_action, urgency, confidence, reason_for_no_alert.\n"
        "urgency: low, normal, high. confidence: low, medium, high.\n"
        "Analyze one symbol. Event Alerts are market-event-first: market facts and snapshots are "
        "primary; news supports interpretation but news alone must not set should_alert=true.\n"
        "LLM owns market significance. Do not invent backend price thresholds. "
        "market.chg_window_percent is primary short-term context and "
        "market.chg24h_percent is broader context. All Event Analysis change fields "
        "(chg_window_percent, chg24h_percent, chg_since_msg_percent) are already percentage "
        "values / percentage points, never decimal fractions: 0.042 means 0.042%, not 4.2%. "
        "Never multiply a supplied change value by 100. Use qualitative significance reasoning "
        "from the supplied market evidence; never say a move did not meet a threshold unless an "
        "explicit threshold is present in the input.\n"
        "should_alert=true means you judge this supplied market event noteworthy enough to "
        "interrupt the user with an Event Alert. Keep that boolean and your qualitative "
        "reasoning internally consistent: if you describe the state as routine, ordinary, "
        "modest, stable, insignificant, or otherwise not meaningfully noteworthy, normally "
        "return should_alert=false. You may return true despite a modest individual metric only "
        "when other supplied market evidence clearly makes the event noteworthy; state that "
        "market-evidence reason. News alone must never make a routine market state alertable.\n"
        "When should_alert=true use a stable non-random event_key. When false, event_key/title/"
        "message_body/possible_action are empty or null, related_news_ids is [], urgency is null, "
        "and reason_for_no_alert is non-empty.\n"
        "For should_alert=true, make title concise and centered on the analysed-window move; do "
        "not repeat 24h change in the title when that move is available. message_body must be a "
        "short, useful interpretation, not a restatement of supplied price or percentage values. "
        "Use only supplied evidence: describe news as coincident context, never as proven cause. "
        "possible_action must be concise, conditional monitoring of supplied snapshots, trend, or "
        "selected news; do not give trading commands or generic risk-plan advice.\n"
        "Use news.news_id only for related_news_ids. Be cautious; no guaranteed outcomes or "
        "hard trading commands.\n"
        "In snapshots, m is minutes before timestamp_utc and p is USD price.\n\nInput JSON:\n"
        f"{_json_dumps(input_payload)}"
    )


async def ask_event_analysis_raw(input_payload: dict, *, schema_check=None) -> tuple[str, dict]:
    symbol = str(input_payload.get("symbol") or "").strip() or None
    max_tokens = llm_config.max_tokens_for("event_analysis")
    return await get_router().chat_completion(
        call_type="event_analysis",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_event_analysis_prompt(input_payload)},
        ],
        max_tokens=max_tokens,
        response_format={"type": "json_object"} if _groq_json_mode_enabled() else None,
        symbol=symbol,
        validate_response=_json_response_validator(
            call_type="event_analysis",
            symbol=symbol,
            max_tokens=max_tokens,
            schema_check=schema_check,
        ),
    )


def build_market_heartbeat_prompt(input_payload: dict) -> str:
    return (
        "Return valid JSON only, in English. Use exactly: symbol, title, message_body, "
        "related_news_ids, possible_action, confidence. This is a calm Market Heartbeat, not "
        "an Event Alert. Do not return should_alert or event_key. Use supplied news only; "
        "related_news_ids must be candidate_news IDs. Do not repeat exact price values, "
        "the current price, exact percentage values, the since-last-message change, or the 24h "
        "change when a "
        "directional summary is sufficient. All fields ending in _percent are already percentage "
        "values, not decimal fractions: 0.042 means 0.042%, not 4.2%; never multiply them by "
        "100. No hard "
        "financial advice.\n\n"
        "Input JSON:\n"
        f"{_json_dumps(input_payload)}"
    )


async def ask_market_heartbeat_raw(input_payload: dict, *, schema_check=None) -> tuple[str, dict]:
    symbol = str(input_payload.get("symbol") or "").strip() or None
    max_tokens = llm_config.max_tokens_for("market_heartbeat")
    return await get_router().chat_completion(
        call_type="market_heartbeat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_market_heartbeat_prompt(input_payload)},
        ],
        max_tokens=max_tokens,
        response_format={"type": "json_object"} if _groq_json_mode_enabled() else None,
        symbol=symbol,
        validate_response=_json_response_validator(
            call_type="market_heartbeat",
            symbol=symbol,
            max_tokens=max_tokens,
            schema_check=schema_check,
        ),
    )


def build_market_report_prompt(input_payload: dict) -> str:
    report_type = str(input_payload.get("report_type") or "daily").strip().lower()
    return (
        "Return valid JSON only, in English. Use exactly: report_type, title, market_pulse, "
        "dashboard, coin_cards, market_catalysts, why_it_matters, watch_next, week_timeline, "
        "themes, next_week_focus. "
        f"report_type must be {report_type!r}. title, market_pulse, why_it_matters, and "
        "watch_next must be non-empty text. dashboard must be a non-empty array of text; "
        "market_catalysts must be an array of text. coin_cards must contain exactly one object "
        "for each supplied active symbol. Each coin-card object must have the symbol, summary, "
        "and watch fields, each with non-empty text. "
        "For weekly reports, week_timeline and themes must be non-empty arrays of text and "
        "next_week_focus must be non-empty text. For daily reports, week_timeline and themes "
        "may be empty arrays and next_week_focus may be empty text. Use supplied context only; "
        "all fields ending in _percent are already percentage values, not decimal fractions: "
        "0.042 means 0.042%, not 4.2%; never multiply them by 100. "
        f"no direct financial advice.\n\nInput JSON:\n{_json_dumps(input_payload)}"
    )


async def ask_market_report_raw(input_payload: dict, *, schema_check=None) -> tuple[str, dict]:
    report_type = str(input_payload.get("report_type") or "").strip().lower()
    call_type = f"{report_type}_report" if report_type in {"daily", "weekly"} else "market_report"
    max_tokens = llm_config.max_tokens_for(call_type)
    return await get_router().chat_completion(
        call_type=call_type,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_market_report_prompt(input_payload)},
        ],
        max_tokens=max_tokens,
        response_format={"type": "json_object"} if _groq_json_mode_enabled() else None,
        timeout=20,
        symbol=None,
        validate_response=_json_response_validator(
            call_type=call_type,
            symbol=None,
            max_tokens=max_tokens,
            schema_check=schema_check,
        ),
    )


async def ask_news_intelligence_raw(
    messages: list[dict],
    *,
    model: str | None = None,
    timeout: int = 20,
    max_tokens: int | None = None,
    schema_check=None,
) -> tuple[str, dict]:
    max_tokens = (
        max_tokens if max_tokens is not None else llm_config.max_tokens_for("news_intelligence")
    )
    return await get_router().chat_completion(
        call_type="news_intelligence",
        messages=messages,
        max_tokens=max_tokens,
        response_format={"type": "json_object"} if _groq_json_mode_enabled() else None,
        timeout=timeout,
        symbol=None,
        model_overrides={"groq": model} if model else None,
        validate_response=_json_response_validator(
            call_type="news_intelligence",
            symbol=None,
            max_tokens=max_tokens,
            schema_check=schema_check,
        ),
    )
