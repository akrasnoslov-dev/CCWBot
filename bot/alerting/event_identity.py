"""Pure Event Alert identity, precision, and scheduling helpers."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

from bot.alerting.alert_rules import calculate_price_change_percent
from bot.alerting.event_analysis import EVENT_ANALYSIS_TYPE, EventAnalysisDecision
from bot.alerting.market_heartbeat import MARKET_HEARTBEAT_ANALYSIS_TYPE
from bot.alerting.news_context import _news_driven_identity
from bot.db.database import make_news_key
from bot.domain.supported_coins import SUPPORTED_SYMBOLS, normalize_symbol

AUTOMATIC_MARKET_CHECK_JOB_NAME = "automatic_market_check"
EVENT_ANALYSIS_PAYLOAD_POINTS = 6


def _stable_float(value: float | None, digits: int) -> float | None:
    return None if value is None else round(float(value), digits)


def get_analysed_window_minutes(
    event_analysis_interval_seconds: int, payload_points: int = EVENT_ANALYSIS_PAYLOAD_POINTS
) -> int:
    return max(
        1, (max(1, int(event_analysis_interval_seconds)) * max(1, int(payload_points)) + 59) // 60
    )


def _format_analysed_window_label(minutes: int | None) -> str:
    if minutes is None:
        return "n/a"
    minutes = max(1, int(minutes))
    return f"{minutes // 60}h" if minutes % 60 == 0 else f"{minutes}m"


def _event_alert_change_label(analysed_window_label: str) -> str:
    return (
        "Analysed-window market move"
        if analysed_window_label == "n/a"
        else f"{analysed_window_label} market move"
    )


def _semantic_family_from_payload(input_payload: dict | None) -> str | None:
    value = input_payload.get("semantic_family") if input_payload else None
    return str(value).strip() if value else None


def _stable_related_news_ids(input_payload: dict, related_news_ids: list[str]) -> list[str]:
    if not related_news_ids:
        return []
    news_items = input_payload.get("news", input_payload.get("candidate_news", []))
    if not isinstance(news_items, list):
        return sorted(str(news_id) for news_id in related_news_ids)
    by_id = {str(item.get("news_id") or ""): item for item in news_items if isinstance(item, dict)}
    stable_ids = []
    for news_id in related_news_ids:
        item = by_id.get(str(news_id))
        stable_ids.append(
            make_news_key({"link": item.get("url"), **item}) if item else str(news_id)
        )
    return sorted(stable_id for stable_id in stable_ids if stable_id)


def _event_instance_key_for_decision(
    *, decision: EventAnalysisDecision, input_payload: dict
) -> str | None:
    if not decision.event_key:
        return None
    stable_news_ids = _stable_related_news_ids(input_payload, decision.related_news_ids)
    return _build_event_instance_key(
        symbol=decision.symbol,
        event_key=decision.event_key,
        timestamp_value=input_payload.get("timestamp_utc"),
        related_news_ids=decision.related_news_ids,
        stable_news_ids=stable_news_ids,
        # No movement bucket: numbers are LLM evidence, never backend policy.
        market_identity_details=[f"urgency:{decision.urgency or 'unknown'}"]
        if not stable_news_ids
        else [],
    )


def _optional_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _analysed_window_minutes_from_payload(input_payload: dict | None) -> int | None:
    if not input_payload:
        return None
    market_data = input_payload.get("market", input_payload.get("market_data", {}))
    value = market_data.get("analysed_window_minutes")
    return int(value) if value is not None else None


def _raw_event_key_from_payload(
    input_payload: dict | None, decision: EventAnalysisDecision
) -> str | None:
    return (
        decision.event_key
        if not input_payload
        else input_payload.get("raw_event_key") or decision.event_key
    )


def _calculate_price_change(
    current_price: Decimal, reference_price: Decimal | None
) -> float | None:
    if reference_price is None:
        return None
    reference = Decimal(str(reference_price))
    if reference == 0:
        return None
    current = Decimal(str(current_price))
    return float(calculate_price_change_percent(reference, current))


def _utc_checked_at(snapshot) -> datetime:
    checked_at = snapshot.checked_at
    return (
        checked_at.replace(tzinfo=timezone.utc)
        if checked_at.tzinfo is None
        else checked_at.astimezone(timezone.utc)
    )


@dataclass(frozen=True)
class AnalysedWindowReference:
    reference_price: Decimal | None
    reference_snapshot: object | None
    window_snapshots: list


def _select_analysed_window_reference(
    *, reference, snapshots: list, since: datetime, now: datetime, max_reference_age: timedelta
) -> AnalysedWindowReference:
    since_utc, now_utc = since.astimezone(timezone.utc), now.astimezone(timezone.utc)
    window = [
        snapshot for snapshot in snapshots if since_utc <= _utc_checked_at(snapshot) <= now_utc
    ]
    if reference is not None:
        reference_time = _utc_checked_at(reference)
        if since_utc - max_reference_age <= reference_time <= since_utc:
            return AnalysedWindowReference(
                Decimal(str(reference.price)),
                reference,
                [snapshot for snapshot in window if _utc_checked_at(snapshot) > reference_time],
            )
    return (
        AnalysedWindowReference(Decimal(str(window[0].price)), None, window)
        if window
        else AnalysedWindowReference(None, None, [])
    )


def _automatic_market_check_job_name(symbol: str) -> str:
    return f"{AUTOMATIC_MARKET_CHECK_JOB_NAME}:{normalize_symbol(symbol)}"


def _symbol_stagger_offsets_seconds(
    *, symbols: tuple[str, ...] | list[str], interval_seconds: int
) -> dict[str, int]:
    interval = max(1, int(interval_seconds))
    normalized = list(dict.fromkeys(normalize_symbol(symbol) for symbol in symbols))
    bucket_count = max(len(normalized), EVENT_ANALYSIS_PAYLOAD_POINTS)
    return {symbol: index * interval // bucket_count for index, symbol in enumerate(normalized)}


def _seconds_until_next_symbol_check(
    *,
    symbol: str,
    interval_seconds: int,
    now: datetime | None = None,
    symbols: tuple[str, ...] | list[str] = SUPPORTED_SYMBOLS,
) -> int:
    now = now or datetime.now(timezone.utc)
    interval = max(1, int(interval_seconds))
    offset = _symbol_stagger_offsets_seconds(symbols=symbols, interval_seconds=interval).get(
        normalize_symbol(symbol), 0
    )
    seconds = now.minute * 60 + now.second + bool(now.microsecond)
    return (offset - seconds % interval) % interval


def _build_event_analysis_id(symbol: str) -> str:
    return f"{EVENT_ANALYSIS_TYPE}_{normalize_symbol(symbol)}_{uuid4().hex}"


def _build_market_heartbeat_id(symbol: str) -> str:
    return f"{MARKET_HEARTBEAT_ANALYSIS_TYPE}_{normalize_symbol(symbol)}_{uuid4().hex}"


def _canonical_decimal_string(value: Decimal) -> str:
    normalized = value.normalize()
    return "0" if normalized == 0 else format(normalized, "f")


def _json_dumps(payload: object) -> str:
    """Canonical JSON that writes Decimal market values without binary-float loss."""
    if payload is None:
        return "null"
    if payload is True:
        return "true"
    if payload is False:
        return "false"
    if isinstance(payload, Decimal):
        return _canonical_decimal_string(payload)
    if isinstance(payload, (int, float, str)):
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)
    if isinstance(payload, (list, tuple)):
        return "[" + ",".join(_json_dumps(item) for item in payload) + "]"
    if isinstance(payload, dict):
        return (
            "{"
            + ",".join(
                f"{json.dumps(str(key), ensure_ascii=False)}:{_json_dumps(value)}"
                for key, value in sorted(payload.items(), key=lambda item: str(item[0]))
            )
            + "}"
        )
    raise TypeError(f"Unsupported JSON value: {type(payload).__name__}")


def _event_input_hash(input_payload: dict) -> str:
    return sha256(_json_dumps(input_payload).encode("utf-8")).hexdigest()


def _canonical_event_analysis_context(input_payload: dict) -> dict:
    """All semantic LLM input, excluding only runtime IDs and wall-clock metadata."""
    market = input_payload.get("market", input_payload.get("market_data", {}))
    market = market if isinstance(market, dict) else {}
    news_items = input_payload.get("news", input_payload.get("candidate_news", []))
    news = []
    for item in news_items if isinstance(news_items, list) else []:
        if isinstance(item, dict):
            news.append(
                {
                    # Keep this structurally identical to _compact_event_analysis_news().
                    # Every field here is sent to the LLM and can change its decision.
                    "news_id": item.get("news_id"),
                    "title": item.get("title"),
                    "source": item.get("source"),
                    "time": item.get("time"),
                    "summary": item.get("summary"),
                    "relevance_label": item.get("relevance_label"),
                    "material": item.get("material"),
                }
            )
    news.sort(key=_json_dumps)
    last_msg = input_payload.get("last_msg")
    last_msg = last_msg if isinstance(last_msg, dict) else {}
    previous_event_alert = input_payload.get("previous_event_alert")
    previous_event_alert = previous_event_alert if isinstance(previous_event_alert, dict) else {}
    return {
        # Version the semantic input contract.  Existing analyses with the former
        # ambiguous change-field names must not be reused under the clarified prompt.
        "schema_version": 2,
        "symbol": normalize_symbol(str(input_payload.get("symbol") or "")),
        "display_symbol": input_payload.get("display_symbol"),
        "coin_name": input_payload.get("coin_name"),
        "market": {
            key: market.get(key)
            for key in (
                "price",
                "snapshots",
                "payload_points",
                "analysed_window_minutes",
                "chg_window_percent",
                "chg24h_percent",
                "chg_since_msg_percent",
            )
        },
        # Delivery and wall-clock metadata do not alter the market-analysis question.
        "last_msg": {
            "type": last_msg.get("type"),
            "price": last_msg.get("price"),
        },
        "previous_event_alert": {
            "title": previous_event_alert.get("title"),
            "canonical_event_key": previous_event_alert.get("canonical_event_key"),
            "semantic_family": previous_event_alert.get("semantic_family"),
            "analysed_window_move": previous_event_alert.get("analysed_window_move"),
            "stable_related_news_ids_hash": previous_event_alert.get(
                "stable_related_news_ids_hash"
            ),
            "possible_action": previous_event_alert.get("possible_action"),
        },
        "news": news,
        "policy": input_payload.get("policy")
        if isinstance(input_payload.get("policy"), dict)
        else None,
    }


def _build_exact_event_context_fingerprint(input_payload: dict) -> str:
    return sha256(
        _json_dumps(_canonical_event_analysis_context(input_payload)).encode("utf-8")
    ).hexdigest()


def _event_instance_bucket(timestamp_value: object, *, bucket_minutes: int = 60) -> str:
    try:
        timestamp = (
            timestamp_value
            if isinstance(timestamp_value, datetime)
            else datetime.fromisoformat(str(timestamp_value).replace("Z", "+00:00"))
        )
    except (TypeError, ValueError):
        timestamp = datetime.now(timezone.utc)
    timestamp = (
        timestamp.replace(tzinfo=timezone.utc)
        if timestamp.tzinfo is None
        else timestamp.astimezone(timezone.utc)
    )
    seconds = bucket_minutes * 60
    return datetime.fromtimestamp(
        int(timestamp.timestamp()) // seconds * seconds, tz=timezone.utc
    ).isoformat()


def _build_event_instance_key(
    *,
    symbol: str,
    event_key: str,
    timestamp_value: object,
    related_news_ids: list[str],
    input_hash: str | None = None,
    stable_news_ids: list[str] | None = None,
    market_identity_details: list[str] | None = None,
) -> str:
    identity = ",".join(sorted(str(item) for item in (stable_news_ids or related_news_ids)))
    if not identity:
        details = ",".join(sorted(str(item) for item in market_identity_details or []))
        identity = f"market_only:{details}" if details else "market_only"
    return sha256(
        "|".join(
            (normalize_symbol(symbol), event_key, _event_instance_bucket(timestamp_value), identity)
        ).encode("utf-8")
    ).hexdigest()


def _build_news_driven_event_key(*, symbol: str, news_item: dict) -> str:
    encoded = json.dumps(
        {"symbol": normalize_symbol(symbol), "identity": _news_driven_identity(news_item)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"news:{normalize_symbol(symbol)}:{sha256(encoded.encode('utf-8')).hexdigest()[:24]}"


def _build_news_driven_event_instance_key(*, symbol: str, event_key: str, news_item: dict) -> str:
    bucket = (
        "dedup_group"
        if str(news_item.get("dedup_group_id") or "").strip()
        else _event_instance_bucket(news_item.get("published_at"), bucket_minutes=60)
    )
    return sha256(
        "|".join(
            (normalize_symbol(symbol), event_key, bucket, _news_driven_identity(news_item))
        ).encode("utf-8")
    ).hexdigest()


def _numeric_context_payload(numeric_context: str | None) -> dict:
    if not numeric_context:
        return {}
    try:
        payload = json.loads(numeric_context)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
