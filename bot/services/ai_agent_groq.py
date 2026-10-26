"""Structured LLM facade used by Event Analysis, heartbeats, reports, and news.

The legacy threshold-driven alert-generation API was removed. Event Alert significance belongs
only to the schema-validated Event Analysis decision.
"""

import json
import logging
import os
import re
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv

from bot.alerting.event_identity import (
    _event_analysis_news_age_hours,
    _event_analysis_news_summary,
    _json_dumps,
)
from bot.domain.supported_coins import ALL_SUPPORTED_COINS
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
# Only the shipped Workers AI model is verified to accept the native, bare JSON
# Schema shape. Unlike Groq's OpenAI envelope, Cloudflare expects json_schema to
# be the schema itself (without name/strict/schema wrapping).
_CLOUDFLARE_JSON_SCHEMA_MODELS = frozenset(
    {"@cf/meta/llama-3.3-70b-instruct-fp8-fast"}
)

_EVENT_SIGNIFICANCE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string"},
        "materiality": {
            "type": "string",
            "enum": ["material", "routine", "unclear"],
        },
        "novelty": {
            "type": "string",
            "enum": ["new", "continuation", "repeated", "unclear"],
        },
        "should_alert": {"type": "boolean"},
        "reason_code": {
            "type": "string",
            "enum": [
                "unusual_move",
                "fast_move",
                "reversal",
                "trend_acceleration",
                "market_news_alignment",
                "routine_move",
                "news_only",
                "unclear",
            ],
        },
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": [
        "symbol",
        "materiality",
        "novelty",
        "should_alert",
        "reason_code",
        "confidence",
    ],
    "additionalProperties": False,
}


_EVENT_ALERT_RENDER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "message_body": {"type": "string"},
        "related_news_ids": {"type": "array", "items": {"type": "string"}},
        "possible_action": {"type": "string"},
    },
    "required": [
        "message_body",
        "related_news_ids",
        "possible_action",
    ],
    "additionalProperties": False,
}


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

_NEWS_INTELLIGENCE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "category": {
            "type": "string",
            "enum": [
                "regulation", "exchange", "security", "macro", "etf", "whale",
                "project", "technical", "market", "noise",
            ],
        },
        "related_symbols": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(ALL_SUPPORTED_COINS)},
        },
        "primary_symbol": {
            "type": ["string", "null"],
            "enum": [None, *sorted(ALL_SUPPORTED_COINS)],
        },
        "impact_score": {"type": "integer"},
        "impact_level": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
        },
        "relevance_score": {"type": "integer"},
        "is_noise": {"type": "boolean"},
        "is_alert_worthy": {"type": "boolean"},
        "alert_reason": {"type": "string"},
        "dedup_hint": {"type": "string"},
    },
    "required": [
        "summary", "category", "related_symbols", "primary_symbol",
        "impact_score", "impact_level", "relevance_score", "is_noise",
        "is_alert_worthy", "alert_reason", "dedup_hint",
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


_MARKET_REPORT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "report_type": {"type": "string"},
        "title": {"type": "string"},
        "market_pulse": {"type": "string"},
        "dashboard": {"type": "array", "items": {"type": "string"}},
        "coin_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "summary": {"type": "string"},
                    "watch": {"type": "string"},
                },
                "required": ["symbol", "summary", "watch"],
                "additionalProperties": False,
            },
        },
        "market_catalysts": {"type": "array", "items": {"type": "string"}},
        "why_it_matters": {"type": "string"},
        "watch_next": {"type": "string"},
        "week_timeline": {"type": "array", "items": {"type": "string"}},
        "themes": {"type": "array", "items": {"type": "string"}},
        "next_week_focus": {"type": "string"},
    },
    "required": [
        "report_type",
        "title",
        "market_pulse",
        "dashboard",
        "coin_cards",
        "market_catalysts",
        "why_it_matters",
        "watch_next",
        "week_timeline",
        "themes",
        "next_week_focus",
    ],
    "additionalProperties": False,
}


def _structured_response_formats(
    *, call_type: str, schema_name: str, schema: dict,
    model_overrides: dict[str, str] | None = None,
) -> tuple[dict | None, dict[str, dict | None] | None]:
    """Return JSON mode and provider-specific schemas for verified model attempts."""
    groq_json_mode = _groq_json_mode_enabled()
    json_object = {"type": "json_object"} if groq_json_mode else None
    strict_format = {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": schema,
        },
    }
    overrides = {}
    for provider, configured_model in llm_config.provider_attempts(call_type):
        override = (model_overrides or {}).get(provider)
        model = (
            llm_config.resolve_model_override(override, default=configured_model)
            if override
            else configured_model
        )
        if provider == "groq" and groq_json_mode and model in _GROQ_STRICT_SCHEMA_MODELS:
            overrides[f"{provider}:{model}"] = strict_format
        elif provider == "openai":
            # OpenAI Structured Outputs uses the same named strict-schema envelope. The
            # application validator still runs after provider acceptance for every feature.
            overrides[f"{provider}:{model}"] = strict_format
    # Event Analysis has six mandatory fields. Plain json_object protects syntax
    # but not their shape; ask the supported Cloudflare model to constrain types
    # and enums before the unchanged backend semantic validator runs. This is
    # provider-specific: Workers AI requires a *bare* JSON Schema, unlike Groq.
    if call_type == "event_analysis":
        for provider, model in llm_config.provider_attempts(call_type):
            if provider == "cloudflare" and model in _CLOUDFLARE_JSON_SCHEMA_MODELS:
                overrides[f"{provider}:{model}"] = {
                    "type": "json_schema",
                    "json_schema": schema,
                }
    return json_object, overrides or None


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
        "JSON English. Market decides;news alone cannot alert. No invented thresholds. "
        "Routine/modest/stable=>false unless other supplied facts warrant alert.",
        "Keys:symbol,should_alert,event_key,title,message_body,related_news_ids,"
        "possible_action,urgency,confidence,reason_for_no_alert.",
        "Input:sym;m={s,w,cw,c24,cl};s=[[min,USD],...],0=now,<0=older;"
        "cw=% over w;c24=24h%;cl=since alert%;n={i,src,t,x,r,mat,h},h=hours old;"
        "prev={k,f,cw}. .042=.042%;null=unknown.",
        "Facts:no derived cw or invented prior/sub-window moves,%,trajectory. "
        "consistent/persistent/throughout requires s;news not causal.",
        "symbol=sym. false=>event_key/title/message_body/possible_action/urgency=null;"
        "related_news_ids=[];reason set. true=>stable event_key;urgency=low|normal|high;"
        "confidence=low|medium|high;reason_for_no_alert=null;title uses cw;"
        "body concise/no extra numbers;action monitor-only/no trade;news IDs only n.i.",
    )
)


def _event_analysis_percent(value: object) -> object:
    """Bound model-visible percent precision without erasing a non-zero sign."""
    if value is None:
        return None
    try:
        rounded = round(value, 6)
    except (TypeError, ValueError):
        return value
    return value if rounded == 0 and value != 0 else rounded


# CCW-47 owner decision (2026-10-26): retain the original Refined v2,
# not the shorter Refined v2 Final (14/200 schema failures in the paid Luna replay).
# Frozen SHA-256:
# e30183660bffd977bc81a5a8f19093a07e9267a3da12aa12e9bbac913ed3f07c
_EVENT_SIGNIFICANCE_INSTRUCTIONS = (
    "JSON English.Decide whether the CURRENT market move is materially noteworthy AND m"
    "aterially new enough to interrupt the user now. Default=>no alert. No fixed numeri"
    "c cutoff.\n"
    "Q1 materiality: judge the CURRENT move itself from recent path,size,speed,and same"
    "-asset unusualness. Direction change or adjacent-window speed can support material"
    "ity only with materially noteworthy current-path evidence. Large c24/p24, news, pr"
    "evious alerts, and recent counts never increase materiality.\n"
    "Q2 novelty: only if Q1=material, judge whether this is materially new versus prev "
    "and cnt. Previous/recent events can only reduce novelty. If Q1 is not material, no"
    "velty should be unclear.\n"
    "Q3 should_alert: true only when Q1=material AND Q2=new. Otherwise false. Only afte"
    "r Q1/Q2/Q3 choose reason_code; it labels an established decision and cannot make m"
    "ateriality or novelty true.\n"
    "pw,p24=30d same-asset abs-move percentile: context, not threshold;null=unknown. If"
    " the move is ordinary for the asset and the observed trajectory shows no distincti"
    "ve continuation, turn, or pace, choose routine even if the timestamp or headline i"
    "s new. Percentile alone proves neither materiality nor novelty. For repeated simil"
    "ar recent moves, require distinct current-path evidence for new. Routine BTC and r"
    "epeated GRAM need distinct fresh path evidence. \n"
    "Calibration examples are not thresholds: ordinary moves without fresh material pat"
    "h evidence=>no alert, regardless of headlines.\n"
    "Input:sym;m={s,w,c30,c60,cw,c24,cl,pw,p24};s=[[min,USD],...],0=now,<0=older;c30=30"
    "m%;c60=1h%;cw=% over w;c24=24h%;cl=since last sent alert%;prev={min,f,cw};min=minu"
    "tes since prev;cnt={h6,h24}=recent alert-worthy market-event counts;n<=2 {t,r,mat,"
    "h},h=hours old;.042=.042%,not 4.2%.\n"
    "Output exactly symbol,materiality,novelty,should_alert,reason_code,confidence. mat"
    "eriality=material|routine|unclear;novelty=new|continuation|repeated|unclear;confid"
    "ence=low|medium|high.\n"
    "should_alert=true only when materiality=material AND novelty=new AND reason_code i"
    "s one of unusual_move|fast_move|reversal|trend_acceleration|market_news_alignment."
    " Otherwise should_alert=false with reason_code=routine_move|news_only|unclear. Sol"
    "e-news=>false+news_only.\n"
    "\n"
    "CCW-29 new balanced market-path decision policy:\n"
    "FIRST pass: independently judge whether the supplied CURRENT analysed-window movem"
    "ent itself is market-significant for this exact asset. Ground that in its magnitud"
    "e, actual time-ordered snapshots, supported short-window movements and same-asset "
    "history. An old price gap since last message, a sizable 24-hour move, a high perce"
    "ntile, news, another timestamp, or reversal wording CANNOT turn a small CURRENT mo"
    "ve into a material event.\n"
    "SECOND pass (only after material): check that there is a substantively fresh marke"
    "t leg against any previous alert. Compare the actual after-alert displacement cl w"
    "ith cw, observed recent path and previous alert age. An already-mentioned three-ho"
    "ur window overlapping an alert is not fresh by itself. A same-direction drop/rise "
    "may nevertheless be NEW if there is clearly material further displacement AFTER th"
    "at alert supported by current snapshots, even if the preceding alert was just minu"
    "tes ago or counts are high. A small fresh tick is not sufficient. High cnt or iden"
    "tical directional semantic family alone is not a veto.\n"
    "Use a fair negative check: if you would issue the same alert from a modest routine"
    " cw only because the prior message is old or because cl spans many hours, reject i"
    "t. Use a fair positive check: if a material cw contains a meaningful additional re"
    "cent fall/rise that the earlier notification could not have described, retain it. "
    "A partial rebound must not erase a confirmed major additional leg; a high c24 must"
    " not manufacture a new cw leg.\n"
    "Do not use rigid percentage thresholds. Keep materiality then novelty then decisio"
    "n in strict six-field schema. If uncertain on either, no alert. No unsupported cat"
    "alysts or headlines as triggers.\n"
    "CCW-29 refinement of balanced prompt after a blinded-holdout-independent diagnosis"
    " of mistakes ON THE OLDER TRAINING SET ONLY (never numerical rules):\n"
    "Avoid an over-eager positive. A reversal is not important merely because cw and c2"
    "4 have opposite signs; require a genuinely important price swing in the CURRENT sn"
    "apshots. A fast_move or acceleration requires observed substantial current-path di"
    "splacement, not merely a high percentile, a short speed comparison, or an isolated"
    " tiny bounce. New data and absence of previous event context do not automatically "
    "establish significance or novelty.\n"
    "For a recent similar alert with multiple previously alert-worthy events, distingui"
    "sh an overlapping three-hour window from genuinely additional price action since t"
    "he earlier message. A moderate recent post-alert difference that simply repeats th"
    "e notified trend should remain a continuation; do not call it new solely from an i"
    "mpressive current-window statistic or repeated related news. Yet a clearly substan"
    "tive new interval of continued loss/gain can warrant a fresh decision even when th"
    "ere were many prior alerts.\n"
    "Avoid over-suppression: evaluate an unusually substantial CURRENT market move on i"
    "ts own evidence before comparing with an earlier alert, even when the since-last-m"
    "essage value is oppositely signed due to partial retracement. A short rebound cann"
    "ot erase a large sustained current-window displacement. Judge moderate moves conte"
    "xtually with the asset's actual observed path; do not automatically classify all m"
    "oderate three-hour changes routine without inspecting available snapshots and hist"
    "orical context. A material fresh development can occur inside a broader trend. How"
    "ever a large old cl or c24 by itself NEVER creates materiality for a routine curre"
    "nt window.\n"
    "Make the final materiality/novelty decision independently of the reason_code label"
    "; default no alert for genuinely unsupported cases, and return EXACTLY the six spe"
    "cified JSON keys. No numerical cutoffs."
)


def _event_significance_prompt_payload(input_payload: dict) -> dict:
    """Return the small always-on model view used only for significance."""
    market = input_payload.get("market")
    market = market if isinstance(market, dict) else {}
    snapshots = market.get("snapshots")
    snapshots = snapshots if isinstance(snapshots, list) else []
    previous_alert = input_payload.get("previous_event_alert")
    previous_alert = previous_alert if isinstance(previous_alert, dict) else {}
    recent_counts = input_payload.get("recent_event_counts")
    recent_counts = recent_counts if isinstance(recent_counts, dict) else {}
    news_items = input_payload.get("news")
    news_items = news_items if isinstance(news_items, list) else []

    compact_news = []
    # Select the first two VALID headlines, matching the exact context.
    for item in [entry for entry in news_items if isinstance(entry, dict)][:2]:
        compact_item = {
            "t": item.get("title"),
            "r": item.get("relevance_label"),
            "mat": item.get("material"),
        }
        age_hours = _event_analysis_news_age_hours(input_payload, item)
        if age_hours is not None:
            compact_item["h"] = age_hours
        compact_news.append(compact_item)

    compact_snapshots = [
        [item.get("m"), item.get("p")]
        for item in snapshots[-6:]
        if isinstance(item, dict)
    ]
    payload = {
        "sym": input_payload.get("symbol"),
        "m": {
            "s": compact_snapshots,
            "w": market.get("analysed_window_minutes"),
            "c30": _event_analysis_percent(market.get("chg30m_percent")),
            "c60": _event_analysis_percent(market.get("chg1h_percent")),
            "cw": _event_analysis_percent(market.get("chg_window_percent")),
            "c24": _event_analysis_percent(market.get("chg24h_percent")),
            "cl": _event_analysis_percent(market.get("chg_since_msg_percent")),
            "pw": _event_analysis_percent(market.get("relative_window_percentile_30d")),
            "p24": _event_analysis_percent(market.get("relative_24h_percentile_30d")),
        },
        "n": compact_news,
    }
    if previous_alert:
        payload["prev"] = {
            "min": previous_alert.get("age_minutes"),
            "f": previous_alert.get("semantic_family"),
            "cw": _event_analysis_percent(previous_alert.get("analysed_window_move")),
        }
    if recent_counts:
        payload["cnt"] = {
            "h6": recent_counts.get("h6"),
            "h24": recent_counts.get("h24"),
        }
    return payload


def build_event_significance_prompt(input_payload: dict) -> str:
    payload = _json_dumps(_event_significance_prompt_payload(input_payload))
    return f"{_EVENT_SIGNIFICANCE_INSTRUCTIONS}\nInput JSON:\n{payload}"


async def ask_event_significance_raw(input_payload: dict, *, schema_check=None) -> tuple[str, dict]:
    symbol = str(input_payload.get("symbol") or "").strip() or None
    max_tokens = llm_config.max_tokens_for("event_analysis")
    response_format, response_format_overrides = _structured_response_formats(
        call_type="event_analysis",
        schema_name="event_significance",
        schema=_EVENT_SIGNIFICANCE_JSON_SCHEMA,
    )
    return await get_router().chat_completion(
        call_type="event_analysis",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_event_significance_prompt(input_payload)},
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


def _event_analysis_prompt_payload(input_payload: dict) -> dict:
    """Return the compact semantic model view without runtime or repeated static fields."""
    market = input_payload.get("market")
    market = market if isinstance(market, dict) else {}
    previous_alert = input_payload.get("previous_event_alert")
    previous_alert = previous_alert if isinstance(previous_alert, dict) else {}
    news_items = input_payload.get("news")
    news_items = news_items if isinstance(news_items, list) else []
    snapshots = market.get("snapshots")
    compact_snapshots = (
        [
            [item.get("m"), item.get("p")] if isinstance(item, dict) else item
            for item in snapshots
        ]
        if isinstance(snapshots, list)
        else snapshots
    )
    compact_news = []
    for item in news_items:
        if not isinstance(item, dict):
            continue
        compact_item = {
            "i": item.get("news_id"),
            "src": item.get("source"),
            "t": item.get("title"),
            "r": item.get("relevance_label"),
            "mat": item.get("material"),
        }
        summary = _event_analysis_news_summary(item.get("summary"))
        if summary:
            compact_item["x"] = summary
        age_hours = _event_analysis_news_age_hours(input_payload, item)
        if age_hours is not None:
            compact_item["h"] = age_hours
        compact_news.append(compact_item)

    payload = {
        "sym": input_payload.get("symbol"),
        "m": {
            "s": compact_snapshots,
            "w": market.get("analysed_window_minutes"),
            "cw": _event_analysis_percent(market.get("chg_window_percent")),
            "c24": _event_analysis_percent(market.get("chg24h_percent")),
            "cl": _event_analysis_percent(market.get("chg_since_msg_percent")),
        },
        "n": compact_news,
    }
    if previous_alert:
        payload["prev"] = {
            "k": previous_alert.get("canonical_event_key"),
            "f": previous_alert.get("semantic_family"),
            "cw": _event_analysis_percent(previous_alert.get("analysed_window_move")),
        }
    return payload


def build_event_analysis_prompt(input_payload: dict) -> str:
    payload = _json_dumps(_event_analysis_prompt_payload(input_payload))
    return f"{_EVENT_ANALYSIS_INSTRUCTIONS}\nInput JSON:\n{payload}"


_EVENT_ALERT_RENDER_INSTRUCTIONS = "\n".join(
    (
        "JSON English. Event Significance has ALREADY been accepted. Return exactly "
        "message_body, related_news_ids, possible_action. Do not re-decide whether to alert. "
        "Never infer news causality or give direct buy/sell instructions.",
        "Write to help a human understand WHY the observed market path matters and "
        "WHAT concrete observation would change the interpretation. Avoid robotic "
        "'watch next snapshots' text when verified price levels are available.",
        "Input sym; market_directions=verified signs for analysed window and 24h; "
        "evidence=verified backend observations; n=optional attributed news; "
        "sig=accepted classification. Do not invent missing metrics or catalysts.",
        "Situation: 1-2 fluent sentences, about 25-42 words. Connect the short-term "
        "path with the 24h direction and explain uncertainty. When "
        "evidence.observed_price_band.high_visits >= 2, you may explain that "
        "recent observations approached the same high more than once, but do not "
        "claim formal resistance, proven buyer/seller intent, volume, or a breakout. "
        "Do not repeat USD prices or percentages already stated by the backend. "
        "Distinguish a counter-move from a confirmed trend reversal.",
        "Possible action: 1-2 conditional sentences, about 25-55 words. "
        "When evidence.observed_price_band is present, quote ONLY its EXACT "
        "high and low USD strings. Describe both testable scenarios: a sustained "
        "move above the observed high versus a move below the observed low, and "
        "what each would mean for the short-term attempt. The observed high/low "
        "are reference prices from the last four supplied observations, NOT "
        "confirmed support/resistance or trading entry/exit targets. "
        "Do not invent other price levels, price forecasts or time deadlines. "
        "Use measured language ('would strengthen/undermine the rebound case', "
        "'would break the recent range'), not buy/sell orders. "
        "When band is missing, do not invent prices: explain a specific "
        "next-step continuation-versus-reversal observation instead.",
        "No fabricated causes, market sentiment, unusualness, acceleration or "
        "persistence. No predictive cross-period convergence/divergence claim. "
        "Never imply a positive move guarantees a profitable trade.",
    )
)


def _render_market_direction(value: object) -> str | None:
    """Return only a supported sign; no rounded or raw market numbers reach Render."""
    if value is None:
        return None
    try:
        change = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not change.is_finite():
        return None
    return "up" if change > 0 else "down" if change < 0 else "flat"


def _event_alert_render_prompt_payload(input_payload: dict) -> dict:
    # Render must not reinterpret numeric, snapshot, or previous-event evidence.
    # The backend separately renders verified prices, periods, and percentages.
    market = input_payload.get("market")
    market = market if isinstance(market, dict) else {}
    directions = {}
    if market.get("analysed_window_minutes") is not None:
        window = _render_market_direction(market.get("chg_window_percent"))
        if window is not None:
            directions["window"] = window
    day = _render_market_direction(market.get("chg24h_percent"))
    if day is not None:
        directions["24h"] = day
    last_msg = input_payload.get("last_msg")
    if isinstance(last_msg, dict) and last_msg.get("time") and last_msg.get("price") is not None:
        since = _render_market_direction(market.get("chg_since_msg_percent"))
        if since is not None:
            directions["since"] = since
    significance = input_payload.get("significance_decision")
    significance = significance if isinstance(significance, dict) else {}
    from bot.alerting.event_text import verified_event_alert_render_context

    return {
        "sym": input_payload.get("symbol"),
        "market_directions": directions,
        "evidence": verified_event_alert_render_context(
            market, input_payload.get("previous_event_alert")
        ),
        "n": _event_analysis_prompt_payload(input_payload)["n"],
        "sig": {"c": significance.get("confidence"), "r": significance.get("reason_code")},
    }


def build_event_alert_render_prompt(input_payload: dict) -> str:
    payload = _json_dumps(_event_alert_render_prompt_payload(input_payload))
    return f"{_EVENT_ALERT_RENDER_INSTRUCTIONS}\nInput JSON:\n{payload}"


async def ask_event_alert_render_raw(
    input_payload: dict, *, schema_check=None
) -> tuple[str, dict]:
    symbol = str(input_payload.get("symbol") or "").strip() or None
    max_tokens = llm_config.max_tokens_for("event_alert_render")
    response_format, response_format_overrides = _structured_response_formats(
        call_type="event_alert_render",
        schema_name="event_alert_render",
        schema=_EVENT_ALERT_RENDER_JSON_SCHEMA,
    )
    return await get_router().chat_completion(
        call_type="event_alert_render",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_event_alert_render_prompt(input_payload)},
        ],
        max_tokens=max_tokens,
        response_format=response_format,
        response_format_overrides=response_format_overrides,
        symbol=symbol,
        validate_response=_json_response_validator(
            call_type="event_alert_render",
            symbol=symbol,
            max_tokens=max_tokens,
            schema_check=schema_check,
        ),
    )


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
    response_format, response_format_overrides = _structured_response_formats(
        call_type=call_type,
        schema_name="market_report",
        schema=_MARKET_REPORT_JSON_SCHEMA,
    )
    return await get_router().chat_completion(
        call_type=call_type,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_market_report_prompt(input_payload)},
        ],
        max_tokens=max_tokens,
        response_format=response_format,
        response_format_overrides=response_format_overrides,
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
    model_overrides = {"groq": model} if model else None
    response_format, response_format_overrides = _structured_response_formats(
        call_type="news_intelligence",
        schema_name="news_intelligence",
        schema=_NEWS_INTELLIGENCE_JSON_SCHEMA,
        model_overrides=model_overrides,
    )
    return await get_router().chat_completion(
        call_type="news_intelligence",
        messages=messages,
        max_tokens=max_tokens,
        response_format=response_format,
        response_format_overrides=response_format_overrides,
        timeout=timeout,
        symbol=None,
        model_overrides=model_overrides,
        validate_response=_json_response_validator(
            call_type="news_intelligence",
            symbol=None,
            max_tokens=max_tokens,
            schema_check=schema_check,
        ),
    )
