"""Event identity, analysed-window, and stable-key helpers for alerts.

Belongs here: deterministic event keys, analysed-window labels, input hashes,
and pure market snapshot selection used by alert orchestration.
Does not belong here: LLM calls, Telegram delivery, recipient lookup, or DB writes.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from bot.alerting.alert_rules import calculate_price_change_percent
from bot.alerting.event_analysis import (
    EVENT_ANALYSIS_TYPE,
    EventAnalysisDecision,
    normalize_event_semantic_family,
)
from bot.alerting.market_heartbeat import MARKET_HEARTBEAT_ANALYSIS_TYPE
from bot.alerting.news_context import _news_driven_identity
from bot.db.database import make_news_key
from bot.domain.supported_coins import SUPPORTED_SYMBOLS, normalize_symbol

AUTOMATIC_MARKET_CHECK_JOB_NAME = "automatic_market_check"
EVENT_ANALYSIS_PAYLOAD_POINTS = 6
EVENT_SEMANTIC_MATERIAL_MOVEMENT_DELTA_PERCENT = 2.5
PRICE_ACTION_SEMANTIC_FAMILIES = frozenset(
    {
        "price_downtrend",
        "price_uptrend",
        "price_level_range",
        "volatility",
    }
)
_DIRECTIONAL_TRAIT_TERMS = frozenset(
    {
        "bearish", "breakout", "decline", "downside", "downtrend", "drop", "fall",
        "higher", "lower", "rally", "rebound", "selloff", "surge", "upside", "uptrend",
    }
)
_LEVEL_TRAIT_TERMS = frozenset(
    {
        "consolidation", "level", "range", "rangebound", "resistance", "sideways",
        "support",
    }
)
_VOLATILITY_TRAIT_TERMS = frozenset({"choppy", "volatile", "volatility", "whipsaw"})
_LEVEL_BREAK_PHRASES = (
    "break_above", "break_below", "break_through", "breakdown", "breaks_above",
    "breaks_below", "breaks_through",
)
_LEVEL_TEST_TERMS = frozenset({"approach", "approaches", "hold", "holds", "near", "test"})
_RANGE_STATE_TERMS = frozenset({"consolidation", "range", "rangebound", "sideways"})

def _stable_float(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)

def get_analysed_window_minutes(
    event_analysis_interval_seconds: int,
    payload_points: int = EVENT_ANALYSIS_PAYLOAD_POINTS,
) -> int:
    seconds = max(1, int(event_analysis_interval_seconds)) * max(1, int(payload_points))
    return max(1, (seconds + 59) // 60)

def _format_analysed_window_label(minutes: int | None) -> str:
    if minutes is None:
        return "n/a"
    minutes = max(1, int(minutes))
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes}m"

def _event_alert_change_label(analysed_window_label: str) -> str:
    if analysed_window_label == "n/a":
        return "Analysed-window market move"
    return f"{analysed_window_label} market move"

def _event_instance_key_for_decision(
    *,
    decision: EventAnalysisDecision,
    input_payload: dict,
) -> str | None:
    if not decision.event_key:
        return None
    return _build_event_instance_key(
        symbol=decision.symbol,
        event_key=decision.event_key,
        timestamp_value=input_payload.get("timestamp_utc"),
        related_news_ids=decision.related_news_ids,
        stable_news_ids=_stable_related_news_ids(input_payload, decision.related_news_ids),
        market_identity_details=_stable_market_identity_details(input_payload, decision),
    )

def _semantic_family_from_payload(input_payload: dict | None) -> str | None:
    if not input_payload:
        return None
    value = input_payload.get("semantic_family")
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
        if not item:
            stable_ids.append(str(news_id))
            continue
        stable_ids.append(make_news_key({"link": item.get("url"), **item}) or str(news_id))
    return sorted(stable_ids)

def _stable_market_identity_details(
    input_payload: dict,
    decision: EventAnalysisDecision,
) -> list[str]:
    if decision.related_news_ids:
        return []
    return [
        f"urgency:{decision.urgency or 'unknown'}",
        f"movement:{_stable_market_movement_bucket(input_payload)}",
    ]

def _stable_market_movement_bucket(input_payload: dict) -> str:
    movement = _event_movement_percent_from_payload(input_payload)
    if movement is None:
        return "unknown"
    bucket = int(abs(movement) // EVENT_SEMANTIC_MATERIAL_MOVEMENT_DELTA_PERCENT)
    bucket *= EVENT_SEMANTIC_MATERIAL_MOVEMENT_DELTA_PERCENT
    return f"{bucket:.1f}"

def _event_movement_percent_from_payload(input_payload: dict) -> float | None:
    market_data = input_payload.get("market", input_payload.get("market_data", {}))
    value = (
        market_data.get("chg_window")
        or market_data.get("chg_since_msg")
        or market_data.get("change_since_last_user_visible_message_percent")
        or market_data.get("chg24h")
        or market_data.get("change_24h_percent")
    )
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _urgency_rank(value: str | None) -> int:
    return {"low": 1, "normal": 2, "high": 3}.get(str(value or "").strip().lower(), 0)

def _event_semantic_cooldown_allows_escalation(
    previous_alert,
    *,
    current_urgency: str | None,
    current_movement_percent: float | None,
    current_stable_news_ids: list[str],
) -> tuple[bool, str | None]:
    details = _event_semantic_cooldown_escalation_details(
        previous_alert,
        current_urgency=current_urgency,
        current_movement_percent=current_movement_percent,
        current_stable_news_ids=current_stable_news_ids,
    )
    if details["urgency_increased"]:
        return True, "urgency_increased"
    if details["material_movement_increased"]:
        return True, "material_movement_increased"
    return False, None

def _event_semantic_cooldown_escalation_details(
    previous_alert,
    *,
    current_urgency: str | None,
    current_movement_percent: float | None,
    current_stable_news_ids: list[str],
) -> dict[str, object]:
    previous_context = _numeric_context_payload(getattr(previous_alert, "numeric_context", None))
    previous_urgency = str(previous_context.get("notification_severity") or "").strip().lower()
    previous_urgency_rank = _urgency_rank(previous_urgency)
    current_urgency_rank = _urgency_rank(current_urgency)

    previous_movement = _optional_float(previous_context.get("analysed_window_change_percent"))
    material_movement_increased = (
        previous_movement is not None
        and current_movement_percent is not None
        and abs(current_movement_percent)
        >= abs(previous_movement) + EVENT_SEMANTIC_MATERIAL_MOVEMENT_DELTA_PERCENT
    )

    previous_news_ids = {
        str(item)
        for item in previous_context.get("stable_related_news_ids") or []
        if str(item).strip()
    }
    current_news_ids = {str(item) for item in current_stable_news_ids if str(item).strip()}
    new_news_ids = current_news_ids - previous_news_ids
    return {
        "previous_urgency": previous_urgency or None,
        "current_urgency": str(current_urgency or "").strip().lower() or None,
        "urgency_increased": (
            previous_urgency_rank > 0 and current_urgency_rank > previous_urgency_rank
        ),
        "previous_movement_percent": previous_movement,
        "current_movement_percent": current_movement_percent,
        "material_movement_increased": material_movement_increased,
        "previous_news_count": len(previous_news_ids),
        "current_news_count": len(current_news_ids),
        "new_news_driver": bool(new_news_ids),
    }

def _event_cooldown_namespace(
    *,
    semantic_family: str | None,
    movement_percent: float | None,
) -> str | None:
    """Return a cooldown-only identity without changing market-event identity.

    Only explicit price-action families can share this namespace. Unknown and topical
    families stay distinct even when they reference the same article.
    """
    family = str(semantic_family or "").strip().lower() or None
    if family not in PRICE_ACTION_SEMANTIC_FAMILIES:
        return None
    direction = _movement_direction(movement_percent)
    if direction not in {"up", "down"}:
        return None
    return f"price_action:{direction}"

def _price_action_context_traits(
    *,
    semantic_family: str | None,
    raw_event_key: str | None,
    title: str | None = None,
    message_body: str | None = None,
) -> list[str]:
    """Return backend-owned price-action traits used only for cross-family cooldown.

    A family contributes its native trait, while the event wording may add other explicit
    traits. Cross-family alerts are equivalent only when both describe the same complete trait
    set; a trend, level interaction, and volatility regime therefore remain distinct by default.
    """
    family = str(semantic_family or "").strip().lower()
    traits: set[str] = set()
    if family in {"price_downtrend", "price_uptrend"}:
        traits.add("directional_move")
    elif family == "price_level_range":
        traits.add("level_interaction")
    elif family == "volatility":
        traits.add("volatility_regime")
    else:
        return []

    raw_tokens = re.findall(r"[a-z0-9]+", str(raw_event_key or "").lower())
    generic_family_tokens = {
        "btc", "event", "price", "downtrend", "uptrend", "level", "range", "volatility",
    }
    descriptive_raw_key = "_".join(
        token for token in raw_tokens if token not in generic_family_tokens
    )
    text = "_".join(
        str(value or "").strip().lower()
        for value in (descriptive_raw_key, title, message_body)
    )
    tokens = set(re.findall(r"[a-z0-9]+", text))
    if tokens.intersection(_DIRECTIONAL_TRAIT_TERMS):
        traits.add("directional_move")
    if tokens.intersection(_LEVEL_TRAIT_TERMS):
        traits.add("level_interaction")
    if tokens.intersection(_VOLATILITY_TRAIT_TERMS):
        traits.add("volatility_regime")
    normalized_text = "_".join(re.findall(r"[a-z0-9]+", text))
    if any(phrase in normalized_text for phrase in _LEVEL_BREAK_PHRASES):
        traits.add("level_break")
    if tokens.intersection(_LEVEL_TEST_TERMS):
        traits.add("level_test_or_hold")
    if tokens.intersection(_RANGE_STATE_TERMS):
        traits.add("range_state")
    if tokens.intersection({"reversal", "reversals", "whipsaw"}):
        traits.add("volatility_reversal")
    return sorted(traits)

def _event_cross_family_context_matches(
    *,
    symbol: str,
    previous_event_key: str | None,
    previous_semantic_family: str | None,
    previous_numeric_context: dict,
    current_semantic_family: str | None,
    current_movement_percent: float | None,
    current_analysed_window_minutes: int | None,
    current_price_action_traits: list[str] | None,
) -> bool:
    """Return whether two differently named price events share cooldown context.

    Both events must be explicit price-action events with the same backend-owned trait set,
    movement direction, and analysed window. News is supporting context and never decides
    equivalence; urgency and materially larger movement are evaluated by the caller.
    """
    if normalize_symbol(symbol) != "btc":
        return False
    previous_family = str(previous_semantic_family or "").strip().lower() or None
    if previous_family is None:
        context_family = str(previous_numeric_context.get("semantic_family") or "").strip()
        previous_family = context_family.lower() or normalize_event_semantic_family(
            symbol,
            previous_event_key,
        )
    current_family = str(current_semantic_family or "").strip().lower() or None
    if previous_family == current_family and previous_family is not None:
        return False

    previous_movement = _optional_float(
        previous_numeric_context.get("analysed_window_change_percent")
    )
    previous_namespace = _event_cooldown_namespace(
        semantic_family=previous_family,
        movement_percent=previous_movement,
    )
    current_namespace = _event_cooldown_namespace(
        semantic_family=current_family,
        movement_percent=current_movement_percent,
    )
    if previous_namespace is None or previous_namespace != current_namespace:
        return False

    previous_traits = {
        str(value).strip() for value in previous_numeric_context.get("price_action_traits") or []
        if str(value).strip()
    }
    current_traits = {
        str(value).strip() for value in current_price_action_traits or [] if str(value).strip()
    }
    if not previous_traits or previous_traits != current_traits:
        return False

    previous_window = previous_numeric_context.get("analysed_window_minutes")
    try:
        normalized_previous_window = int(previous_window)
        normalized_current_window = int(current_analysed_window_minutes)
    except (TypeError, ValueError):
        return False
    if normalized_previous_window != normalized_current_window:
        return False

    return True

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
    if value is None:
        return None
    return int(value)

def _raw_event_key_from_payload(
    input_payload: dict | None,
    decision: EventAnalysisDecision,
) -> str | None:
    if not input_payload:
        return decision.event_key
    return input_payload.get("raw_event_key") or decision.event_key

def _calculate_price_change(current_price: float, reference_price: float | None) -> float | None:
    if reference_price is None or reference_price == 0:
        return None
    return calculate_price_change_percent(reference_price, current_price)

def _utc_checked_at(snapshot) -> datetime:
    checked_at = snapshot.checked_at
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    return checked_at.astimezone(timezone.utc)

@dataclass(frozen=True)
class AnalysedWindowReference:
    reference_price: float | None
    reference_snapshot: object | None
    window_snapshots: list

def _select_analysed_window_reference(
    *,
    reference,
    snapshots: list,
    since: datetime,
    now: datetime,
    max_reference_age: timedelta,
) -> AnalysedWindowReference:
    since_utc = since.astimezone(timezone.utc)
    now_utc = now.astimezone(timezone.utc)
    earliest_reference_at = since_utc - max_reference_age
    window_snapshots = [
        snapshot
        for snapshot in snapshots
        if since_utc <= _utc_checked_at(snapshot) <= now_utc
    ]

    if reference is not None:
        reference_time = _utc_checked_at(reference)
        if earliest_reference_at <= reference_time <= since_utc:
            return AnalysedWindowReference(
                reference_price=float(reference.price),
                reference_snapshot=reference,
                window_snapshots=[
                    snapshot
                    for snapshot in window_snapshots
                    if _utc_checked_at(snapshot) > reference_time
                ],
            )

    if window_snapshots:
        return AnalysedWindowReference(
            reference_price=float(window_snapshots[0].price),
            reference_snapshot=None,
            window_snapshots=window_snapshots,
        )
    return AnalysedWindowReference(
        reference_price=None,
        reference_snapshot=None,
        window_snapshots=[],
    )

def _automatic_market_check_job_name(symbol: str) -> str:
    return f"{AUTOMATIC_MARKET_CHECK_JOB_NAME}:{normalize_symbol(symbol)}"

def _symbol_stagger_offsets_seconds(
    *,
    symbols: tuple[str, ...] | list[str],
    interval_seconds: int,
) -> dict[str, int]:
    interval = max(1, int(interval_seconds))
    normalized_symbols = list(dict.fromkeys(normalize_symbol(symbol) for symbol in symbols))
    if not normalized_symbols:
        return {}
    bucket_count = max(len(normalized_symbols), EVENT_ANALYSIS_PAYLOAD_POINTS)
    return {
        symbol: (index * interval) // bucket_count
        for index, symbol in enumerate(normalized_symbols)
    }

def _seconds_until_next_symbol_check(
    *,
    symbol: str,
    interval_seconds: int,
    now: datetime | None = None,
    symbols: tuple[str, ...] | list[str] = SUPPORTED_SYMBOLS,
) -> int:
    now = now or datetime.now(timezone.utc)
    interval = max(1, int(interval_seconds))
    offset = _symbol_stagger_offsets_seconds(
        symbols=symbols,
        interval_seconds=interval,
    ).get(normalize_symbol(symbol), 0)
    seconds_since_hour = now.minute * 60 + now.second
    if now.microsecond:
        seconds_since_hour += 1
    cycle_position = seconds_since_hour % interval
    return (offset - cycle_position) % interval

def _build_event_analysis_id(symbol: str) -> str:
    return f"{EVENT_ANALYSIS_TYPE}_{normalize_symbol(symbol)}_{uuid4().hex}"

def _build_market_heartbeat_id(symbol: str) -> str:
    return f"{MARKET_HEARTBEAT_ANALYSIS_TYPE}_{normalize_symbol(symbol)}_{uuid4().hex}"

def _json_dumps(payload: dict | list) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _event_input_hash(input_payload: dict) -> str:
    return sha256(_json_dumps(input_payload).encode("utf-8")).hexdigest()

def _build_event_similarity_fingerprint(input_payload: dict) -> str:
    """Return a safe stable hash for conservative pre-LLM context reuse."""
    market_data = input_payload.get("market", input_payload.get("market_data", {}))
    if not isinstance(market_data, dict):
        market_data = {}
    movement = _event_movement_percent_from_payload(input_payload)
    previous_context = input_payload.get("previous_event_alert")
    if not isinstance(previous_context, dict):
        previous_context = {}
    stable_news_ids = _stable_candidate_news_ids(input_payload)
    payload = {
        "symbol": normalize_symbol(str(input_payload.get("symbol") or "")),
        "analysed_window_minutes": market_data.get("analysed_window_minutes"),
        "movement_direction": _movement_direction(movement),
        "movement_bucket": _stable_market_movement_bucket(input_payload),
        "change_24h_bucket": _stable_numeric_bucket(market_data.get("chg24h")),
        "candidate_news_ids": stable_news_ids[:2],
        "previous_canonical_event_key": previous_context.get("canonical_event_key"),
        "previous_semantic_family": previous_context.get("semantic_family"),
        "previous_related_news_hash": previous_context.get("stable_related_news_ids_hash"),
    }
    return sha256(_json_dumps(payload).encode("utf-8")).hexdigest()

def _movement_direction(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"

def _stable_numeric_bucket(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown"
    bucket = int(abs(number) // EVENT_SEMANTIC_MATERIAL_MOVEMENT_DELTA_PERCENT)
    bucket *= EVENT_SEMANTIC_MATERIAL_MOVEMENT_DELTA_PERCENT
    return f"{_movement_direction(number)}:{bucket:.1f}"

def _stable_candidate_news_ids(input_payload: dict) -> list[str]:
    news_items = input_payload.get("news", input_payload.get("candidate_news", []))
    if not isinstance(news_items, list):
        return []
    stable_ids: set[str] = set()
    for item in news_items:
        if not isinstance(item, dict):
            continue
        stable_key = make_news_key({"link": item.get("url"), **item})
        if stable_key:
            stable_ids.add(stable_key)
    return sorted(stable_ids)

def _event_instance_bucket(timestamp_value: object, *, bucket_minutes: int = 60) -> str:
    if isinstance(timestamp_value, datetime):
        timestamp = timestamp_value
    else:
        try:
            timestamp = datetime.fromisoformat(str(timestamp_value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            timestamp = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    bucket_seconds = bucket_minutes * 60
    bucket_epoch = int(timestamp.timestamp()) // bucket_seconds * bucket_seconds
    return datetime.fromtimestamp(bucket_epoch, tz=timezone.utc).isoformat()

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
    stable_ids = stable_news_ids or []
    news_or_input = ",".join(sorted(str(news_id) for news_id in stable_ids or related_news_ids))
    if not news_or_input:
        details = ",".join(sorted(str(item) for item in market_identity_details or []))
        news_or_input = f"market_only:{details}" if details else "market_only"
    raw_key = "|".join(
        (
            normalize_symbol(symbol),
            event_key,
            _event_instance_bucket(timestamp_value),
            news_or_input,
        )
    )
    return sha256(raw_key.encode("utf-8")).hexdigest()

def _build_news_driven_event_key(*, symbol: str, news_item: dict) -> str:
    identity = _news_driven_identity(news_item)
    encoded = json.dumps(
        {"symbol": normalize_symbol(symbol), "identity": identity},
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"news:{normalize_symbol(symbol)}:{sha256(encoded.encode('utf-8')).hexdigest()[:24]}"

def _build_news_driven_event_instance_key(
    *,
    symbol: str,
    event_key: str,
    news_item: dict,
) -> str:
    identity = _news_driven_identity(news_item)
    dedup_group_id = str(news_item.get("dedup_group_id") or "").strip()
    bucket = (
        "dedup_group"
        if dedup_group_id
        else _event_instance_bucket(news_item.get("published_at"), bucket_minutes=60)
    )
    raw_key = "|".join(
        (
            normalize_symbol(symbol),
            event_key,
            bucket,
            identity,
        )
    )
    return sha256(raw_key.encode("utf-8")).hexdigest()

def _numeric_context_payload(numeric_context: str | None) -> dict:
    if not numeric_context:
        return {}
    try:
        payload = json.loads(numeric_context)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
