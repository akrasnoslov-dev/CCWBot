from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from ops_agent.schemas import Period

PRIVACY_MODE = "no_raw_text_bundle_local_hashes"
SEVERE_QUALITY_ISSUES = {
    "contains_n_a",
    "contains_unknown",
    "contains_unavailable",
    "contains_null",
}
EVENT_REGRESSION_MATERIAL_MOVEMENT_DELTA_PERCENT = 2.5

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MONEY_RE = re.compile(r"[$€£]?\b\d+(?:[.,]\d+)*(?:\s?(?:usd|eur|gbp))?\b", re.IGNORECASE)
PERCENT_RE = re.compile(r"[-+]?\b\d+(?:[.,]\d+)?\s?%")
TIMESTAMP_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[tT ]\d{2}:\d{2}(?::\d{2})?)?\b")
WORD_RE = re.compile(r"[a-z][a-z0-9_]{2,}")
RANDOM_KEY_RE = re.compile(
    r"(^|[_:-])(?:[0-9a-f]{16,}|[0-9a-f]{8}(?:[_-]?[0-9a-f]{4}){3}"
    r"[_-]?[0-9a-f]{12})$",
    re.IGNORECASE,
)
NA_RE = re.compile(r"(?<![a-z0-9])n/a(?![a-z0-9])", re.IGNORECASE)

STOPWORDS = {
    "alert",
    "and",
    "are",
    "around",
    "because",
    "but",
    "can",
    "check",
    "coin",
    "continue",
    "current",
    "during",
    "event",
    "financial",
    "for",
    "from",
    "has",
    "have",
    "into",
    "its",
    "market",
    "may",
    "not",
    "now",
    "price",
    "risk",
    "should",
    "that",
    "the",
    "this",
    "users",
    "watch",
    "with",
}


class BundleHasher:
    def __init__(self, salt: bytes | None = None) -> None:
        self._salt = salt or os.urandom(32)

    def ref(self, namespace: str, value: Any) -> str:
        raw = "" if value is None else str(value)
        digest = hmac.new(
            self._salt,
            f"{namespace}:{raw}".encode(),
            hashlib.sha256,
        ).hexdigest()[:12]
        return f"{namespace}_ref:h_{digest}"


def normalize_alert_text(value: str | None) -> str:
    text = str(value or "").lower()
    text = URL_RE.sub(" ", text)
    text = PERCENT_RE.sub(" ", text)
    text = MONEY_RE.sub(" ", text)
    text = TIMESTAMP_RE.sub(" ", text)
    text = text.replace("not financial advice", " ")
    text = re.sub(r"[^a-z0-9_]+", " ", text)
    tokens = [token for token in WORD_RE.findall(text) if token not in STOPWORDS]
    return " ".join(tokens)


def safe_terms(value: str | None, *, limit: int = 5) -> list[str]:
    normalized = normalize_alert_text(value)
    counts = Counter(token for token in normalized.split() if token not in STOPWORDS)
    return [token for token, _ in counts.most_common(limit)]


def _terms_from_normalized(value: str) -> set[str]:
    return {token for token in value.split() if token not in STOPWORDS}


def _jaccard(first: set[str], second: set[str]) -> float:
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def _parse_json_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _parse_json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, str):
        return value
    return None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _minutes_between(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, int((end_dt - start_dt).total_seconds() // 60))


def _event_ref(hasher: BundleHasher, value: Any) -> str | None:
    return hasher.ref("event", value) if value is not None else None


def _analysis_ref(hasher: BundleHasher, value: Any) -> str | None:
    return hasher.ref("analysis", value) if value is not None else None


def _event_instance_ref(hasher: BundleHasher, value: Any) -> str | None:
    return hasher.ref("event_instance", value) if value else None


def _row_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in (
            "alert_message",
            "analysis_plain_text",
            "analysis_title",
            "analysis_message_body",
            "analysis_possible_action",
            "analysis_reason_for_no_alert",
        )
    )


def _analysis_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in (
            "analysis_plain_text",
            "analysis_title",
            "analysis_message_body",
            "analysis_possible_action",
            "analysis_reason_for_no_alert",
        )
    )


def _base_payload(period: Period, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "period": period.as_dict(),
        "privacy_mode": PRIVACY_MODE,
        "warnings": warnings or [],
    }


def build_alert_evidence_payloads(
    rows: list[dict[str, Any]],
    *,
    period: Period,
    row_cap: int,
    semantic_cooldown_seconds: int,
) -> dict[str, dict[str, Any]]:
    hasher = BundleHasher()
    warnings = []
    if len(rows) >= row_cap:
        warnings.append("alert evidence reached row cap; repetition analysis may be incomplete")

    indexed = [_indexed_row(row, hasher) for row in rows]
    quality_payload = _alert_quality(indexed, period, warnings)
    suppression_payload = _suppression_effectiveness(
        indexed,
        period,
        semantic_cooldown_seconds=semantic_cooldown_seconds,
        warnings=warnings,
    )
    return {
        "evidence/db/alert_delivery_distribution.json": _delivery_distribution(
            indexed, period, warnings
        ),
        "evidence/db/alert_quality.json": quality_payload,
        "evidence/db/event_analysis_decision_timeline.json": _decision_timeline(
            indexed, period, warnings
        ),
        "evidence/db/alert_content_fingerprints.json": _content_fingerprints(
            indexed, period, warnings
        ),
        "evidence/db/alert_similarity_groups.json": _similarity_groups(
            indexed, period, warnings
        ),
        "evidence/db/backend_suppression_effectiveness.json": suppression_payload,
        "evidence/db/event_identity_quality.json": _event_identity_quality(
            indexed, period, warnings
        ),
        "evidence/db/event_alert_regression_checks.json": _event_alert_regression_checks(
            quality_payload,
            suppression_payload,
            period,
            warnings,
        ),
    }


def _indexed_row(row: dict[str, Any], hasher: BundleHasher) -> dict[str, Any]:
    full_text = _row_text(row)
    analysis_text = _analysis_text(row)
    normalized_text = normalize_alert_text(full_text)
    normalized_analysis = normalize_alert_text(analysis_text)
    content_basis = normalized_text or normalized_analysis or str(row.get("event_key") or "")
    analysis_basis = normalized_analysis or str(row.get("input_hash") or "")
    event_key = row.get("event_key") or row.get("analysis_event_key")
    related_news = _parse_json_list(row.get("related_news_ids"))
    numeric_context = _parse_json_dict(row.get("alert_numeric_context"))
    delivery_count = _int(row.get("delivery_count"))
    sent_delivery_count = _int(row.get("sent_delivery_count"))
    first_delivery_at = _iso(row.get("first_delivery_at"))
    last_delivery_at = _iso(row.get("last_delivery_at"))
    quality_issues = _quality_issues(
        row,
        full_text=full_text,
        related_news_count=len(related_news),
    )
    return {
        "symbol": str(row.get("symbol") or row.get("analysis_symbol") or "UNKNOWN").upper(),
        "alert_type": row.get("alert_type"),
        "trigger_source": row.get("trigger_source"),
        "status": row.get("status"),
        "should_alert": row.get("should_alert"),
        "analysis_status": row.get("analysis_status"),
        "event_key": event_key,
        "semantic_family": row.get("semantic_family")
        or numeric_context.get("semantic_family")
        or None,
        "analysis_event_key": row.get("analysis_event_key"),
        "urgency": row.get("urgency") or numeric_context.get("notification_severity"),
        "confidence": row.get("confidence"),
        "market_event_ref": _event_ref(hasher, row.get("market_event_id")),
        "analysis_ref": _analysis_ref(hasher, row.get("event_ai_analysis_id")),
        "event_instance_ref": _event_instance_ref(hasher, row.get("event_instance_key")),
        "content_hash": hasher.ref("content", content_basis),
        "analysis_hash": hasher.ref("analysis_content", analysis_basis),
        "input_hash_ref": hasher.ref("input", row.get("input_hash")),
        "normalized_text": normalized_text,
        "terms": _terms_from_normalized(normalized_text or normalized_analysis),
        "safe_terms": safe_terms(full_text or analysis_text),
        "delivery_count": delivery_count,
        "sent_delivery_count": sent_delivery_count,
        "failed_delivery_count": _int(row.get("failed_delivery_count")),
        "distinct_recipient_count": _int(row.get("distinct_recipient_count")),
        "first_delivery_at": first_delivery_at,
        "last_delivery_at": last_delivery_at,
        "analysis_created_at": _iso(row.get("analysis_created_at")),
        "detected_at": _iso(row.get("detected_at")),
        "price_change_percent": _float(row.get("price_change_percent")),
        "analysed_window_change_percent": _float(
            numeric_context.get("analysed_window_change_percent")
        ),
        "last_24h_change": _float(row.get("last_24h_change")),
        "last_7d_change": _float(row.get("last_7d_change")),
        "stable_related_news_ids": [
            str(item)
            for item in numeric_context.get("stable_related_news_ids") or []
            if str(item).strip()
        ],
        "related_news_count": len(related_news),
        "quality_issues": quality_issues,
    }


def _quality_issues(
    row: dict[str, Any], *, full_text: str, related_news_count: int
) -> list[str]:
    lowered = full_text.lower()
    issues: list[str] = []
    if NA_RE.search(lowered):
        issues.append("contains_n_a")
    for token, issue in (
        ("unknown", "contains_unknown"),
        ("unavailable", "contains_unavailable"),
        ("null", "contains_null"),
    ):
        if token in lowered:
            issues.append(issue)
    is_event_alert = str(row.get("alert_type") or "") == "event_alert" or row.get(
        "market_event_id"
    ) is not None
    if is_event_alert and "since last btc alert" in lowered:
        issues.append("old_since_last_btc_alert_label")
    if is_event_alert and "analysed-window change" in lowered:
        issues.append("old_analysed_window_change_label")
    if is_event_alert and "price change" in lowered:
        issues.append("old_generic_price_change_label")
    if is_event_alert and ("btc change" in lowered or "market change" in lowered):
        issues.append("old_generic_market_change_label")
    if is_event_alert and "24h change" in lowered:
        issues.append("old_24h_change_label")
    if is_event_alert and related_news_count == 0:
        issues.append("empty_related_context")
    alert_message = str(row.get("alert_message") or "")
    if not alert_message.strip() or alert_message.count("**") % 2:
        issues.append("malformed_formatting")
    return sorted(set(issues))


def _delivery_distribution(
    rows: list[dict[str, Any]], period: Period, warnings: list[str]
) -> dict[str, Any]:
    payload = _base_payload(period, warnings)
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = (row["symbol"], row.get("alert_type"), row.get("trigger_source"), row.get("status"))
        group = groups.setdefault(
            key,
            {
                "symbol": row["symbol"],
                "alert_type": row.get("alert_type"),
                "trigger_source": row.get("trigger_source"),
                "status": row.get("status"),
                "delivery_count": 0,
                "sent_deliveries": 0,
                "failed_deliveries": 0,
                "unique_market_events": set(),
                "unique_analyses": set(),
                "first_seen_at": None,
                "last_seen_at": None,
            },
        )
        group["delivery_count"] += row["delivery_count"]
        group["sent_deliveries"] += row["sent_delivery_count"]
        group["failed_deliveries"] += row["failed_delivery_count"]
        if row.get("market_event_ref"):
            group["unique_market_events"].add(row["market_event_ref"])
        if row.get("analysis_ref"):
            group["unique_analyses"].add(row["analysis_ref"])
        _extend_time_range(group, row.get("first_delivery_at") or row.get("analysis_created_at"))
        _extend_time_range(group, row.get("last_delivery_at") or row.get("analysis_created_at"))
    symbol_totals: dict[str, int] = defaultdict(int)
    output_rows = []
    for group in groups.values():
        group["unique_market_events"] = len(group["unique_market_events"])
        group["unique_analyses"] = len(group["unique_analyses"])
        symbol_totals[str(group["symbol"])] += int(group["sent_deliveries"])
        output_rows.append(group)
    payload["rows"] = sorted(
        output_rows,
        key=lambda item: (-item["delivery_count"], item["symbol"]),
    )
    payload["symbols"] = [
        {"symbol": symbol, "sent_deliveries": count}
        for symbol, count in sorted(symbol_totals.items(), key=lambda item: (-item[1], item[0]))
    ]
    return payload


def _alert_quality(
    rows: list[dict[str, Any]], period: Period, warnings: list[str]
) -> dict[str, Any]:
    payload = _base_payload(period, warnings)
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    total_event_alert_deliveries = 0
    affected_event_alert_deliveries = 0
    severe_affected_event_alert_deliveries = 0
    quality_issue_occurrences = 0
    for row in rows:
        issues = row.get("quality_issues") or []
        delivery_count = _int(row.get("delivery_count"))
        if str(row.get("alert_type") or "") == "event_alert":
            total_event_alert_deliveries += delivery_count
            if issues:
                affected_event_alert_deliveries += delivery_count
            if SEVERE_QUALITY_ISSUES.intersection(issues):
                severe_affected_event_alert_deliveries += delivery_count
        quality_issue_occurrences += delivery_count * len(issues)
        for issue in issues:
            key = (
                str(issue),
                row["symbol"],
                str(row.get("trigger_source") or "unknown"),
                str(row.get("alert_type") or "unknown"),
            )
            group = groups.setdefault(
                key,
                {
                    "issue": issue,
                    "symbol": row["symbol"],
                    "trigger_source": row.get("trigger_source") or "unknown",
                    "alert_type": row.get("alert_type") or "unknown",
                    "delivery_count": 0,
                    "sent_deliveries": 0,
                    "affected_users_estimate": 0,
                    "market_events": set(),
                    "analyses": set(),
                    "first_seen_at": None,
                    "last_seen_at": None,
                    "safe_terms": Counter(),
                    "sample_event_refs": [],
                },
            )
            group["delivery_count"] += _int(row.get("delivery_count"))
            group["sent_deliveries"] += _int(row.get("sent_delivery_count"))
            group["affected_users_estimate"] += _int(row.get("distinct_recipient_count"))
            if row.get("market_event_ref"):
                group["market_events"].add(row["market_event_ref"])
                if len(group["sample_event_refs"]) < 5:
                    group["sample_event_refs"].append(row["market_event_ref"])
            if row.get("analysis_ref"):
                group["analyses"].add(row["analysis_ref"])
            group["safe_terms"].update(row.get("safe_terms") or [])
            _extend_time_range(
                group,
                row.get("first_delivery_at") or row.get("analysis_created_at"),
            )
            _extend_time_range(group, row.get("last_delivery_at") or row.get("analysis_created_at"))

    issue_rows = []
    for group in groups.values():
        deliveries = _int(group["delivery_count"])
        issue_rows.append(
            {
                "issue": group["issue"],
                "symbol": group["symbol"],
                "trigger_source": group["trigger_source"],
                "alert_type": group["alert_type"],
                "delivery_count": deliveries,
                "sent_deliveries": group["sent_deliveries"],
                "affected_users_estimate": group["affected_users_estimate"],
                "market_events": len(group["market_events"]),
                "analyses": len(group["analyses"]),
                "share_of_event_alert_deliveries": (
                    round(deliveries / total_event_alert_deliveries, 4)
                    if total_event_alert_deliveries
                    else None
                ),
                "first_seen_at": group["first_seen_at"],
                "last_seen_at": group["last_seen_at"],
                "safe_terms": [term for term, _ in group["safe_terms"].most_common(5)],
                "sample_event_refs": group["sample_event_refs"],
            }
        )
    payload["total_event_alert_deliveries"] = total_event_alert_deliveries
    payload["affected_event_alert_deliveries"] = affected_event_alert_deliveries
    payload["severe_affected_event_alert_deliveries"] = severe_affected_event_alert_deliveries
    payload["quality_issue_occurrences"] = quality_issue_occurrences
    payload["issues"] = sorted(
        issue_rows,
        key=lambda item: (-item["delivery_count"], item["issue"], item["symbol"]),
    )
    payload["limitations"] = [
        "affected_users_estimate may count the same user more than once across grouped rows",
        "issue rows are issue occurrences; affected_event_alert_deliveries counts each "
        "affected Event Alert delivery once",
        "raw Telegram message text is not exported; issue labels are derived during collection",
    ]
    return payload


def _decision_timeline(
    rows: list[dict[str, Any]], period: Period, warnings: list[str]
) -> dict[str, Any]:
    payload = _base_payload(period, warnings)
    seen: set[tuple[Any, Any, Any]] = set()
    timeline = []
    for row in sorted(
        rows,
        key=lambda item: str(item.get("analysis_created_at") or ""),
        reverse=True,
    ):
        key = (row.get("analysis_ref"), row.get("market_event_ref"), row.get("input_hash_ref"))
        if key in seen:
            continue
        seen.add(key)
        timeline.append(
            {
                "analysis_ref": row.get("analysis_ref"),
                "market_event_ref": row.get("market_event_ref"),
                "symbol": row["symbol"],
                "status": row.get("analysis_status"),
                "should_alert": row.get("should_alert"),
                "event_key": row.get("event_key"),
                "content_hash": row.get("content_hash"),
                "analysis_hash": row.get("analysis_hash"),
                "delivery_count": row.get("delivery_count"),
                "sent_delivery_count": row.get("sent_delivery_count"),
                "price_change_percent": row.get("price_change_percent"),
                "last_24h_change": row.get("last_24h_change"),
                "last_7d_change": row.get("last_7d_change"),
                "related_news_count": row.get("related_news_count"),
                "urgency": row.get("urgency"),
                "confidence": row.get("confidence"),
                "detected_at": row.get("detected_at"),
                "analysis_created_at": row.get("analysis_created_at"),
                "safe_terms": row.get("safe_terms"),
            }
        )
    payload["rows"] = timeline
    return payload


def _content_fingerprints(
    rows: list[dict[str, Any]], period: Period, warnings: list[str]
) -> dict[str, Any]:
    payload = _base_payload(period, warnings)
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["symbol"], row["content_hash"])
        group = groups.setdefault(
            key,
            {
                "symbol": row["symbol"],
                "content_hash": row["content_hash"],
                "analysis_hashes": set(),
                "event_keys": set(),
                "market_events": set(),
                "analysis_attempts": set(),
                "delivery_count": 0,
                "sent_deliveries": 0,
                "distinct_recipient_count": 0,
                "first_seen_at": None,
                "last_seen_at": None,
                "sample_event_refs": [],
                "event_instance_refs_sample": [],
                "safe_terms": Counter(),
            },
        )
        _add_group_row(group, row)
    payload["groups"] = _finalize_groups(groups.values(), min_events=1)
    payload["repeated_groups"] = [
        group
        for group in payload["groups"]
        if group["market_events"] > 1
        or group["sent_deliveries"] > group["distinct_recipient_count"]
    ]
    return payload


def _similarity_groups(
    rows: list[dict[str, Any]], period: Period, warnings: list[str]
) -> dict[str, Any]:
    payload = _base_payload(period, warnings)
    source_groups = [
        row
        for row in rows
        if row.get("terms") and (row.get("market_event_ref") or row.get("analysis_ref"))
    ]
    clusters: list[list[dict[str, Any]]] = []
    for row in source_groups:
        placed = False
        for cluster in clusters:
            if _jaccard(set(row["terms"]), set(cluster[0]["terms"])) >= 0.45:
                cluster.append(row)
                placed = True
                break
        if not placed:
            clusters.append([row])

    groups = []
    for cluster in clusters:
        if len(cluster) < 2:
            continue
        counter = Counter(term for row in cluster for term in row["terms"])
        group_id = BundleHasher().ref(
            "similarity",
            "|".join(sorted(str(row.get("content_hash")) for row in cluster)),
        )
        group = {
            "semantic_group_id": group_id,
            "symbols": sorted({row["symbol"] for row in cluster}),
            "event_keys": sorted(
                {str(row.get("event_key")) for row in cluster if row.get("event_key")}
            )[:10],
            "content_hashes": sorted({str(row.get("content_hash")) for row in cluster})[:10],
            "market_events": len(
                {row.get("market_event_ref") for row in cluster if row.get("market_event_ref")}
            ),
            "analysis_attempts": len(
                {row.get("analysis_ref") for row in cluster if row.get("analysis_ref")}
            ),
            "should_alert_true": sum(1 for row in cluster if row.get("should_alert") is True),
            "sent_deliveries": sum(_int(row.get("sent_delivery_count")) for row in cluster),
            "first_seen_at": None,
            "last_seen_at": None,
            "safe_terms": [term for term, _ in counter.most_common(5)],
            "sample_event_refs": [],
            "actionability": "similar alert content repeated; inspect event identity and cooldown",
        }
        for row in cluster:
            _extend_time_range(
                group,
                row.get("first_delivery_at") or row.get("analysis_created_at"),
            )
            _extend_time_range(group, row.get("last_delivery_at") or row.get("analysis_created_at"))
            if row.get("market_event_ref") and len(group["sample_event_refs"]) < 5:
                group["sample_event_refs"].append(row["market_event_ref"])
        groups.append(group)
    payload["groups"] = sorted(
        groups,
        key=lambda item: (-item["sent_deliveries"], -item["market_events"], item["symbols"]),
    )
    return payload


def _suppression_effectiveness(
    rows: list[dict[str, Any]],
    period: Period,
    *,
    semantic_cooldown_seconds: int,
    warnings: list[str],
) -> dict[str, Any]:
    payload = _base_payload(period, warnings)
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("should_alert") is not True or not row.get("event_key"):
            continue
        family_key = str(row.get("semantic_family") or row.get("event_key"))
        key = (row["symbol"], family_key)
        group = groups.setdefault(
            key,
            {
                "symbol": row["symbol"],
                "event_key": row["event_key"],
                "semantic_family": row.get("semantic_family"),
                "cooldown_type": "semantic_event_key",
                "configured_seconds": semantic_cooldown_seconds,
                "llm_should_alert_events": 0,
                "delivered_events": 0,
                "likely_suppressed_events": 0,
                "delivered_inside_cooldown_candidates": 0,
                "delivered_inside_cooldown_allowed_escalations": 0,
                "allowed_escalation_reasons": Counter(),
                "first_seen_at": None,
                "last_seen_at": None,
                "confidence": "medium",
                "note": "suppression inferred from DB; no durable suppression row exists",
                "_delivered_rows": [],
            },
        )
        group["llm_should_alert_events"] += 1
        if _int(row.get("sent_delivery_count")) > 0:
            group["delivered_events"] += 1
            group["_delivered_rows"].append(row)
        else:
            group["likely_suppressed_events"] += 1
        _extend_time_range(group, row.get("first_delivery_at") or row.get("analysis_created_at"))
        _extend_time_range(group, row.get("last_delivery_at") or row.get("analysis_created_at"))

    for group in groups.values():
        if semantic_cooldown_seconds <= 0:
            continue
        delivered_rows = sorted(
            group.pop("_delivered_rows", []),
            key=lambda item: str(
                item.get("first_delivery_at") or item.get("analysis_created_at") or ""
            ),
        )
        previous = None
        for row in delivered_rows:
            if previous is not None and _rows_inside_cooldown(
                previous,
                row,
                semantic_cooldown_seconds=semantic_cooldown_seconds,
            ):
                allowed, reason = _delivery_escalation_allowed(previous, row)
                if allowed:
                    group["delivered_inside_cooldown_allowed_escalations"] += 1
                    group["allowed_escalation_reasons"][str(reason)] += 1
                else:
                    group["delivered_inside_cooldown_candidates"] += 1
            previous = row
        group["allowed_escalation_reasons"] = dict(group["allowed_escalation_reasons"])
    payload["suppression_groups"] = sorted(
        groups.values(),
        key=lambda item: (
            -item["delivered_inside_cooldown_candidates"],
            -item["likely_suppressed_events"],
            -item["llm_should_alert_events"],
        ),
    )
    return payload


def _event_alert_regression_checks(
    quality_payload: dict[str, Any],
    suppression_payload: dict[str, Any],
    period: Period,
    warnings: list[str],
) -> dict[str, Any]:
    payload = _base_payload(period, warnings)
    issue_counts = {
        str(row.get("issue")): _int(row.get("delivery_count"))
        for row in quality_payload.get("issues") or []
    }
    placeholder_issues = {
        issue: count
        for issue, count in issue_counts.items()
        if issue in {"contains_n_a", "contains_unknown", "contains_unavailable", "contains_null"}
    }
    old_label_issues = {
        issue: count for issue, count in issue_counts.items() if issue.startswith("old_")
    }
    noisy_repeat_groups = [
        row
        for row in suppression_payload.get("suppression_groups") or []
        if _int(row.get("delivered_inside_cooldown_candidates")) > 0
    ]
    allowed_repeat_groups = [
        row
        for row in suppression_payload.get("suppression_groups") or []
        if _int(row.get("delivered_inside_cooldown_allowed_escalations")) > 0
    ]
    critical = bool(placeholder_issues or old_label_issues)
    warning = bool(noisy_repeat_groups)
    payload.update(
        {
            "status": "critical" if critical else "warning" if warning else "ok",
            "placeholder_issue_counts": placeholder_issues,
            "old_label_issue_counts": old_label_issues,
            "same_family_repeat_noise_groups": len(noisy_repeat_groups),
            "same_family_allowed_escalation_groups": len(allowed_repeat_groups),
            "sample_repeat_groups": noisy_repeat_groups[:5],
            "sample_allowed_escalation_groups": allowed_repeat_groups[:5],
        }
    )
    return payload


def _rows_inside_cooldown(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    semantic_cooldown_seconds: int,
) -> bool:
    previous_at = previous.get("first_delivery_at") or previous.get("analysis_created_at")
    current_at = current.get("first_delivery_at") or current.get("analysis_created_at")
    minutes = _minutes_between(previous_at, current_at)
    if minutes is None:
        return False
    return minutes * 60 < semantic_cooldown_seconds


def _delivery_escalation_allowed(
    previous: dict[str, Any], current: dict[str, Any]
) -> tuple[bool, str | None]:
    if _urgency_rank(current.get("urgency")) > _urgency_rank(previous.get("urgency")):
        return True, "urgency_increased"
    previous_movement = _float(previous.get("analysed_window_change_percent"))
    current_movement = _float(current.get("analysed_window_change_percent"))
    if (
        previous_movement is not None
        and current_movement is not None
        and abs(current_movement)
        >= abs(previous_movement) + EVENT_REGRESSION_MATERIAL_MOVEMENT_DELTA_PERCENT
    ):
        return True, "material_movement_increased"
    previous_news = {str(item) for item in previous.get("stable_related_news_ids") or []}
    current_news = {str(item) for item in current.get("stable_related_news_ids") or []}
    if current_news - previous_news:
        return True, "new_news_driver"
    return False, None


def _urgency_rank(value: Any) -> int:
    return {"low": 1, "normal": 2, "high": 3}.get(str(value or "").strip().lower(), 0)


def _event_identity_quality(
    rows: list[dict[str, Any]], period: Period, warnings: list[str]
) -> dict[str, Any]:
    payload = _base_payload(period, warnings)
    by_symbol: dict[str, dict[str, Any]] = {}
    by_content: dict[tuple[str, str], set[str]] = defaultdict(set)
    key_counts: dict[tuple[str, str], int] = defaultdict(int)
    suspicious_keys: list[dict[str, Any]] = []
    for row in rows:
        symbol = row["symbol"]
        event_key = str(row.get("event_key") or "")
        if not event_key:
            continue
        stats = by_symbol.setdefault(
            symbol,
            {
                "symbol": symbol,
                "market_events": set(),
                "event_keys": set(),
                "one_off_event_keys": 0,
                "suspicious_key_count": 0,
                "same_content_split_key_groups": 0,
            },
        )
        if row.get("market_event_ref"):
            stats["market_events"].add(row["market_event_ref"])
        stats["event_keys"].add(event_key)
        key_counts[(symbol, event_key)] += 1
        by_content[(symbol, row["content_hash"])].add(event_key)
        if RANDOM_KEY_RE.search(event_key):
            stats["suspicious_key_count"] += 1
            if len(suspicious_keys) < 10:
                suspicious_keys.append({"symbol": symbol, "event_key": event_key})
    split_groups = []
    for (symbol, content_hash), event_keys in by_content.items():
        if len(event_keys) <= 1:
            continue
        by_symbol[symbol]["same_content_split_key_groups"] += 1
        split_groups.append(
            {
                "symbol": symbol,
                "content_hash": content_hash,
                "event_key_count": len(event_keys),
                "event_keys_sample": sorted(event_keys)[:5],
            }
        )
    rows_out = []
    for symbol, stats in by_symbol.items():
        keys = stats["event_keys"]
        market_events = len(stats["market_events"])
        stats["one_off_event_keys"] = sum(
            1 for event_key in keys if key_counts[(symbol, event_key)] == 1
        )
        rows_out.append(
            {
                "symbol": symbol,
                "market_events": market_events,
                "event_keys": len(keys),
                "event_key_churn_ratio": (
                    round(len(keys) / market_events, 4) if market_events else None
                ),
                "one_off_event_keys": stats["one_off_event_keys"],
                "suspicious_key_count": stats["suspicious_key_count"],
                "same_content_split_key_groups": stats["same_content_split_key_groups"],
            }
        )
    payload["rows"] = sorted(
        rows_out,
        key=lambda item: (-(item["event_key_churn_ratio"] or 0), item["symbol"]),
    )
    payload["same_content_split_key_groups"] = sorted(
        split_groups, key=lambda item: (-item["event_key_count"], item["symbol"])
    )[:50]
    payload["suspicious_event_keys"] = suspicious_keys
    return payload


def _add_group_row(group: dict[str, Any], row: dict[str, Any]) -> None:
    if row.get("analysis_hash"):
        group["analysis_hashes"].add(row["analysis_hash"])
    if row.get("event_key"):
        group["event_keys"].add(row["event_key"])
    if row.get("market_event_ref"):
        group["market_events"].add(row["market_event_ref"])
        if len(group["sample_event_refs"]) < 5:
            group["sample_event_refs"].append(row["market_event_ref"])
    if row.get("analysis_ref"):
        group["analysis_attempts"].add(row["analysis_ref"])
    if row.get("event_instance_ref") and len(group["event_instance_refs_sample"]) < 5:
        group["event_instance_refs_sample"].append(row["event_instance_ref"])
    group["delivery_count"] += _int(row.get("delivery_count"))
    group["sent_deliveries"] += _int(row.get("sent_delivery_count"))
    group["distinct_recipient_count"] += _int(row.get("distinct_recipient_count"))
    group["safe_terms"].update(row.get("safe_terms") or [])
    _extend_time_range(group, row.get("first_delivery_at") or row.get("analysis_created_at"))
    _extend_time_range(group, row.get("last_delivery_at") or row.get("analysis_created_at"))


def _finalize_groups(groups: Any, *, min_events: int) -> list[dict[str, Any]]:
    output = []
    for group in groups:
        market_events = len(group["market_events"])
        if market_events < min_events:
            continue
        output.append(
            {
                "symbol": group["symbol"],
                "content_hash": group["content_hash"],
                "analysis_hashes": sorted(group["analysis_hashes"])[:10],
                "event_keys": sorted(group["event_keys"])[:10],
                "market_events": market_events,
                "analysis_attempts": len(group["analysis_attempts"]),
                "delivery_count": group["delivery_count"],
                "sent_deliveries": group["sent_deliveries"],
                "distinct_recipient_count": group["distinct_recipient_count"],
                "first_seen_at": group["first_seen_at"],
                "last_seen_at": group["last_seen_at"],
                "delivery_window_minutes": _minutes_between(
                    group["first_seen_at"], group["last_seen_at"]
                ),
                "sample_event_refs": group["sample_event_refs"],
                "event_instance_refs_sample": group["event_instance_refs_sample"],
                "safe_terms": [term for term, _ in group["safe_terms"].most_common(5)],
                "actionability": "same content hash repeated; inspect cooldown/event identity",
            }
        )
    return sorted(
        output,
        key=lambda item: (-item["sent_deliveries"], -item["market_events"], item["symbol"]),
    )


def _extend_time_range(group: dict[str, Any], value: str | None) -> None:
    if not value:
        return
    if group.get("first_seen_at") is None or value < group["first_seen_at"]:
        group["first_seen_at"] = value
    if group.get("last_seen_at") is None or value > group["last_seen_at"]:
        group["last_seen_at"] = value


def _window_seconds(group: dict[str, Any]) -> int:
    minutes = _minutes_between(group.get("first_seen_at"), group.get("last_seen_at"))
    return int(minutes or 0) * 60
