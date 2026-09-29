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


_GROQ_STRICT_SCHEMA_MODELS = frozenset(
    {
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
    }
)

_EVENT_ANALYSIS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string"},
        "should_alert": {"type": "boolean"},
        "event_key": {"type": ["string", "null"]},
        "title": {"type": ["string", "null"]},
        "message_body": {"type": ["string", "null"]},
        "related_news_ids": {
            "type": ["array", "null"],
            "items": {"type": "string"},
        },
        "possible_action": {"type": ["string", "null"]},
        "urgency": {
            "type": ["string", "null"],
            "enum": ["low", "normal", "high", None],
        },
        "confidence": {
            "type": ["string", "null"],
            "enum": ["low", "medium", "high", None],
        },
        "reason_for_no_alert": {"type": ["string", "null"]},
    },
    "required": [
        "symbol",
        "should_alert",
        "event_key",
        "title",
        "message_body",
        "related_news_ids",
        "possible_action",
        "urgency",
        "confidence",
        "reason_for_no_alert",
    ],
    "additionalProperties": False,
}

_MARKET_HEARTBEAT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string"},
        "title": {"type": "string"},
        "message_body": {"type": "string"},
        "related_news_ids": {"type": "array", "items": {"type": "string"}},
        "possible_action": {"type": "string"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": [
        "symbol",
        "title",
        "message_body",
        "related_news_ids",
        "possible_action",
        "confidence",
    ],
    "additionalProperties": False,
}


def _structured_response_formats(
    *, call_type: str, schema_name: str, schema: dict
) -> tuple[dict | None, dict[str, dict | None] | None]:
    """Return the shared JSON mode plus a strict Groq override when supported."""
    if not _groq_json_mode_enabled():
        return None, None

    json_object = {"type": "json_object"}
    groq_model = llm_config.model_for("groq", call_type)
    if groq_model not in _GROQ_STRICT_SCHEMA_MODELS:
        return json_object, None

    return (
        json_object,
        {
            "groq": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            }
        },
    )


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


_EVENT_ANALYSIS_INSTRUCTIONS = "\n".join(
    (
        "JSON English retail; useful, nonrepeat alerts. Keys: symbol, should_alert, event_key, "
        "title, message_body, related_news_ids, possible_action, urgency, confidence, "
        "reason_for_no_alert. urgency=low|normal|high; confidence=low|medium|high.",
        "Market first; news never alone true. LLM judges qualitatively: no backend/invented "
        "threshold; say a threshold was missed only if supplied. Routine/ordinary/modest/stable/"
        "insignificant normally false unless market facts are noteworthy.",
        "Data: sym; at=observation time; m={p:USD,s:snapshots,w:min,cw:window %,c24:24h %,"
        "cl:since alert %}; lm={t:time,p:price}; n={i,src,t,tm,x,r,mat}; prev={t,k,f,cw,nh,a}. "
        "Snapshot m=minutes before observation,p=USD.",
        "cw=change over w; c24=24h; cl=since lm.t/p. All %: 0.042=0.042%, not 4.2%; no x100. "
        "null unknown: never derive cw from cl/c24 or claim trajectory without cw. Only s shows "
        "trajectory; one snapshot or w does not.",
        "true: stable event_key; concise title on verified cw, not c24; body interprets, no raw "
        "numbers. Supplied evidence only; news coincident, not cause. possible_action=conditional "
        "monitoring, never trade/generic risk advice; related_news_ids only n.i. false: event_key/"
        "title/message_body/possible_action null or empty, related_news_ids=[], urgency=null, "
        "reason_for_no_alert non-empty. No guaranteed outcomes/hard trading commands.",
    )
)


def _event_analysis_prompt_payload(input_payload: dict) -> dict:
    """Return the lossless semantic model view without runtime or repeated static fields."""
    market = input_payload.get("market")
    market = market if isinstance(market, dict) else {}
    last_message = input_payload.get("last_msg")
    last_message = last_message if isinstance(last_message, dict) else {}
    previous_alert = input_payload.get("previous_event_alert")
    previous_alert = previous_alert if isinstance(previous_alert, dict) else {}
    news_items = input_payload.get("news")
    news_items = news_items if isinstance(news_items, list) else []

    payload = {
        "sym": input_payload.get("symbol"),
        "at": input_payload.get("timestamp_utc"),
        "m": {
            "p": market.get("price"),
            "s": market.get("snapshots"),
            "w": market.get("analysed_window_minutes"),
            "cw": market.get("chg_window_percent"),
            "c24": market.get("chg24h_percent"),
            "cl": market.get("chg_since_msg_percent"),
        },
        "lm": {"t": last_message.get("time"), "p": last_message.get("price")},
        "n": [
            {
                "i": item.get("news_id"),
                "src": item.get("source"),
                "t": item.get("title"),
                "tm": item.get("time"),
                "x": item.get("summary"),
                "r": item.get("relevance_label"),
                "mat": item.get("material"),
            }
            for item in news_items
            if isinstance(item, dict)
        ],
    }
    if previous_alert:
        payload["prev"] = {
            "t": previous_alert.get("title"),
            "k": previous_alert.get("canonical_event_key"),
            "f": previous_alert.get("semantic_family"),
            "cw": previous_alert.get("analysed_window_move"),
            "nh": previous_alert.get("stable_related_news_ids_hash"),
            "a": previous_alert.get("possible_action"),
        }
    return payload


def build_event_analysis_prompt(input_payload: dict) -> str:
    payload = _json_dumps(_event_analysis_prompt_payload(input_payload))
    return f"{_EVENT_ANALYSIS_INSTRUCTIONS}\nInput JSON:\n{payload}"


async def ask_event_analysis_raw(input_payload: dict, *, schema_check=None) -> tuple[str, dict]:
    symbol = str(input_payload.get("symbol") or "").strip() or None
    max_tokens = llm_config.max_tokens_for("event_analysis")
    response_format, response_format_overrides = _structured_response_formats(
        call_type="event_analysis",
        schema_name="event_analysis",
        schema=_EVENT_ANALYSIS_JSON_SCHEMA,
    )
    return await get_router().chat_completion(
        call_type="event_analysis",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_event_analysis_prompt(input_payload)},
        ],
        max_tokens=max_tokens,
        response_format=response_format,
        response_format_overrides=response_format_overrides,
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
    response_format, response_format_overrides = _structured_response_formats(
        call_type="market_heartbeat",
        schema_name="market_heartbeat",
        schema=_MARKET_HEARTBEAT_JSON_SCHEMA,
    )
    return await get_router().chat_completion(
        call_type="market_heartbeat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_market_heartbeat_prompt(input_payload)},
        ],
        max_tokens=max_tokens,
        response_format=response_format,
        response_format_overrides=response_format_overrides,
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
