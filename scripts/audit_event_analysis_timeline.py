"""Read-only assessment of sanitized Event Analysis decisions; NOT an LLM replay.

Do not commit exported production evidence, raw prompts, report bundles, or user IDs.
Selection is for human adjudication only, never a live Event Alert gate.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

SYMBOLS = ("BTC", "ETH", "GRAM", "SOL")
REQUIRED = {
    "symbol",
    "analysis_created_at",
    "should_alert",
    "analysed_window_change_percent",
    "relative_window_percentile_30d",
}
MISSING_REPLAY_CONTEXT = (
    "snapshots",
    "previous_event_alert",
    "recent_event_counts",
    "news",
)


def _number(value):
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def audit(rows: list[dict], *, show_refs: bool = False) -> dict:
    if not isinstance(rows, list) or any(not isinstance(x, dict) for x in rows):
        raise ValueError("Expected a sanitized timeline rows array")
    if rows and not REQUIRED.issubset(set(rows[0])):
        raise ValueError("Timeline does not have the expected sanitized schema")
    result = {
        "provenance": "sanitized production decision timeline; not identical-context replay",
        "ground_truth": "unavailable",
        "false_positive_count": None,
        "false_negative_count": None,
        "missing_llm_input_fields": list(MISSING_REPLAY_CONTEXT),
        "by_symbol": {},
    }
    for symbol in SYMBOLS:
        coin = sorted(
            (
                r
                for r in rows
                if r.get("symbol") == symbol and isinstance(r.get("should_alert"), bool)
            ),
            key=lambda r: r["analysis_created_at"] or "",
        )
        positive = [r for r in coin if r["should_alert"] is True]
        negative = [r for r in coin if r["should_alert"] is False]

        def ranking(group, field, *, reverse=True):
            eligible = [r for r in group if _number(r.get(field)) is not None]
            return sorted(
                eligible,
                key=lambda r: (
                    abs(_number(r[field]))
                    if field == "analysed_window_change_percent"
                    else _number(r[field])
                ),
                reverse=reverse,
            )[:3]

        selection = []
        seen = set()
        buckets = (
            ("largest_negative", ranking(negative, "analysed_window_change_percent")),
            ("rarest_negative", ranking(negative, "relative_window_percentile_30d")),
            (
                "smallest_positive",
                ranking(positive, "analysed_window_change_percent", reverse=False),
            ),
            ("largest_positive", ranking(positive, "analysed_window_change_percent")),
        )
        for kind, candidates in buckets:
            for row in candidates:
                identity = row.get("analysis_ref") or row["analysis_created_at"]
                if identity in seen:
                    continue
                seen.add(identity)
                earlier = [
                    r for r in positive if r["analysis_created_at"] < row["analysis_created_at"]
                ]
                previous = earlier[-1] if earlier else None
                elapsed = (
                    (
                        _time(row["analysis_created_at"]) - _time(previous["analysis_created_at"])
                    ).total_seconds()
                    / 60
                    if previous
                    else None
                )
                chosen = {
                    "selection_reason": kind,
                    "recorded_should_alert": row["should_alert"],
                    "analysed_window_change_percent": _number(
                        row["analysed_window_change_percent"]
                    ),
                    "relative_window_percentile_30d": _number(
                        row["relative_window_percentile_30d"]
                    ),
                    "previous_positive_minutes_ago": round(elapsed, 1)
                    if elapsed is not None
                    else None,
                    "previous_positive_was_delivered": (
                        (previous.get("sent_delivery_count") or 0) > 0 if previous else None
                    ),
                    "needs_manual_adjudication": True,
                }
                if show_refs:
                    chosen["bundle_local_analysis_ref"] = row.get("analysis_ref")
                selection.append(chosen)
        result["by_symbol"][symbol] = {
            "total": len(coin),
            "positive": len(positive),
            "negative": len(negative),
            "selected_for_review": selection,
        }
    result["completed_decisions"] = sum(g["total"] for g in result["by_symbol"].values())
    result["positive"] = sum(g["positive"] for g in result["by_symbol"].values())
    result["negative"] = sum(g["negative"] for g in result["by_symbol"].values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "timeline", type=Path, help="Published sanitized event_analysis_decision_timeline.json"
    )
    parser.add_argument(
        "--show-local-refs", action="store_true", help="Include bundle-local pseudonymous refs"
    )
    args = parser.parse_args()
    data = json.loads(args.timeline.read_text(encoding="utf-8"))
    if "rows" not in data or "privacy_mode" not in data:
        parser.error("Expected sanitized ops-agent timeline, not a raw DB export")
    result = audit(data["rows"], show_refs=args.show_local_refs)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
