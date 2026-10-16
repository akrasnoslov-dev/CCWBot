"""Privacy-safe frozen real-market evaluation for the existing significance replay.

No production access, providers, recipient lookups, or Telegram operations.
Unlabelled scenarios and incomplete measurement denominators remain unknown.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

SYMBOLS = {"BTC", "ETH", "GRAM", "SOL"}
SCENARIO_TYPES = {
    "delivered", "no_alert", "significant", "routine", "borderline",
    "repeat", "continuation", "reversal", "news_present", "news_absent",
}
WARRANT = {"alert", "no_alert", "ambiguous"}
SENSITIVE_KEYS = {
    "user_id", "chat_id", "telegram_id", "telegram_chat_id", "telegram_user_id",
    "username", "email", "phone", "api_key", "secret", "token", "password",
    "session", "payment_id", "prompt", "raw_output", "raw_message",
}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _check_private_data(value: object, path: str = "case") -> None:
    if isinstance(value, dict):
        for key, part in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: non-string key")
            normalized = key.lower()
            if normalized in SENSITIVE_KEYS or normalized.endswith("_api_key"):
                raise ValueError(f"{path}: forbidden field {key}")
            _check_private_data(part, f"{path}.{key}")
    elif isinstance(value, list):
        for index, part in enumerate(value):
            _check_private_data(part, f"{path}[{index}]")
    elif isinstance(value, str):
        if EMAIL_PATTERN.search(value) or "t.me/" in value.lower():
            raise ValueError(f"{path}: possible private contact data")


def load_frozen(path: str | Path) -> dict:
    dataset = json.loads(Path(path).read_text(encoding="utf-8"))
    if dataset.get("schema_version") != 1:
        raise ValueError("Unsupported frozen benchmark schema")
    if dataset.get("provenance") != "real_market_sanitized":
        raise ValueError("Only verified real-market evidence may enter this benchmark")
    cases = dataset.get("cases")
    if not isinstance(cases, list) or dataset.get("dataset_sha256") != digest(cases):
        raise ValueError("Frozen dataset integrity mismatch")
    seen = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Invalid benchmark case")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not ID_PATTERN.fullmatch(case_id):
            raise ValueError("Case must have an opaque, privacy-safe ID")
        if case_id in seen:
            raise ValueError("Duplicate case ID")
        seen.add(case_id)
        if case.get("symbol") not in SYMBOLS:
            raise ValueError(f"{case_id}: unsupported symbol")
        if case.get("scenario_type") not in SCENARIO_TYPES:
            raise ValueError(f"{case_id}: unsupported scenario type")
        if case.get("source_type") not in {"approved_read_only", "public_market_archive"}:
            raise ValueError(f"{case_id}: missing real-market provenance")
        facts = case.get("input")
        if not isinstance(facts, dict) or facts.get("symbol") != case["symbol"]:
            raise ValueError(f"{case_id}: incomplete analysis input")
        market = facts.get("market")
        if not isinstance(market, dict) or any(
            market.get(field) is None
            for field in ("price", "chg_window_percent", "analysed_window_minutes")
        ):
            raise ValueError(f"{case_id}: missing real market facts")
        if not isinstance(market.get("snapshots"), list) or len(market["snapshots"]) < 2:
            raise ValueError(f"{case_id}: missing market snapshots")
        if case.get("input_sha256") != digest(facts):
            raise ValueError(f"{case_id}: changed canonical replay input")
        obs = case.get("observed", {})
        if not isinstance(obs, dict):
            raise ValueError(f"{case_id}: invalid observation")
        if obs.get("should_alert") is not None and type(obs["should_alert"]) is not bool:
            raise ValueError(f"{case_id}: invalid observed decision")
        for field in (
            "eligible_recipients", "delivered_count", "delivery_failures",
            "llm_calls", "provider_attempts", "total_tokens", "rate_limit_attempts",
            "same_event_duplicates", "same_family_duplicates",
        ):
            if field in obs and (type(obs[field]) is not int or obs[field] < 0):
                raise ValueError(f"{case_id}: invalid {field}")
        if (
            obs.get("eligible_recipients") is not None
            and obs.get("delivered_count", 0) > obs["eligible_recipients"]
        ):
            raise ValueError(f"{case_id}: deliveries exceed eligible recipients")
        if "operating_cost_usd" in obs and (
            type(obs["operating_cost_usd"]) not in (int, float)
            or obs["operating_cost_usd"] < 0
        ):
            raise ValueError(f"{case_id}: invalid cost")
        _check_private_data(case)
    return dataset


def blind_packet(dataset: dict, phase: str) -> dict:
    if phase not in {"significance", "message"}:
        raise ValueError("Unknown blind review phase")
    cards = []
    for case in dataset["cases"]:
        card = {
            "id": case["id"],
            "symbol": case["symbol"],
            "scenario_type": case["scenario_type"],
            "input": case["input"],
        }
        if phase == "message":
            # Message review follows locked significance review; only approved sanitized copy.
            card["final_message"] = case.get("observed", {}).get("final_message")
        cards.append(card)
    return {
        "schema_version": 1,
        "dataset_sha256": dataset["dataset_sha256"],
        "phase": phase,
        "cases": cards,
    }


def _read_evaluations(path: str | Path | None, dataset: dict) -> tuple[str | None, dict]:
    if path is None:
        return None, {}
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("dataset_sha256") != dataset["dataset_sha256"]:
        raise ValueError("Evaluator used a different frozen input")
    identity = record.get("evaluator_id")
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("Independent human evaluator ID required")
    allowed = {case["id"] for case in dataset["cases"]}
    labels = {}
    for row in record.get("labels", []):
        case_id = row.get("id")
        if case_id not in allowed or case_id in labels:
            raise ValueError("Unknown or duplicate evaluation case")
        if row.get("warrant") not in WARRANT:
            raise ValueError("Warrant must be alert, no_alert, or ambiguous")
        for quality in ("useful", "factual"):
            if row.get(quality) is not None and type(row[quality]) is not bool:
                raise ValueError(f"Invalid {quality} rating")
        labels[case_id] = row
    return identity, labels


def reconcile(
    dataset: dict, evaluator_one: str | Path | None = None,
    evaluator_two: str | Path | None = None,
    resolution: str | Path | None = None,
) -> tuple[dict, dict]:
    id1, first = _read_evaluations(evaluator_one, dataset)
    id2, second = _read_evaluations(evaluator_two, dataset)
    if bool(id1) != bool(id2):
        raise ValueError("Both independent evaluations required")
    if id1 and id1 == id2:
        raise ValueError("Two different independent human evaluators required")
    _, resolved = _read_evaluations(resolution, dataset)
    final = {}
    disagreements = []
    for case in dataset["cases"]:
        key = case["id"]
        if key not in first or key not in second:
            continue
        merged = {"id": key}
        for field in ("warrant", "useful", "factual"):
            a, b = first[key].get(field), second[key].get(field)
            if a == b:
                merged[field] = a
            else:
                disagreements.append({"id": key, "field": field})
                # Never auto-adjudicate a disagreement.
                merged[field] = resolved.get(key, {}).get(field)
                if field == "warrant" and merged[field] not in WARRANT:
                    merged[field] = None
        final[key] = merged
    return final, {
        "reviewed_by_both": len(final),
        "disagreements": disagreements,
        "unresolved_disagreements": sum(
            row["field"] not in resolved.get(row["id"], {})
            for row in disagreements
        ),
        "adjudicated": sum(
            row["field"] in resolved.get(row["id"], {})
            for row in disagreements
        ),
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _confusion(cases: list[dict], labels: dict, *, weight_field: str | None = None) -> dict:
    counts = Counter()
    eligible = 0
    omitted = 0
    ambiguous = 0
    for case in cases:
        label = labels.get(case["id"], {}).get("warrant")
        if label == "ambiguous":
            ambiguous += 1
            continue
        prediction = case.get("observed", {}).get("should_alert")
        if label not in {"alert", "no_alert"} or type(prediction) is not bool:
            omitted += 1
            continue
        weight = 1
        if weight_field:
            weight = case.get("observed", {}).get(weight_field)
            if weight is None:
                omitted += 1
                continue
        eligible += 1
        outcome = (
            "tp" if prediction and label == "alert" else
            "fp" if prediction else
            "fn" if label == "alert" else "tn"
        )
        counts[outcome] += weight
    return {
        "scored_cases": eligible,
        "unscored_cases": omitted,
        "ambiguous_cases": ambiguous,
        "tp": counts["tp"], "fp": counts["fp"],
        "fn": counts["fn"], "tn": counts["tn"],
        "precision": _ratio(counts["tp"], counts["tp"] + counts["fp"]),
        "recall": _ratio(counts["tp"], counts["tp"] + counts["fn"]),
    }


def _quality(cases: list[dict], labels: dict) -> dict:
    total = useful = factual = error = delivery_total = delivery_useful = 0
    for case in cases:
        observation = case.get("observed", {})
        if not observation.get("final_message"):
            continue
        label = labels.get(case["id"], {})
        if label.get("useful") is not None:
            total += 1
            useful += int(label["useful"])
            count = observation.get("delivered_count")
            if count is not None:
                delivery_total += count
                delivery_useful += count * int(label["useful"])
        if label.get("factual") is not None:
            factual += 1
            error += int(not label["factual"])
    return {
        "usefulness_reviewed_events": total,
        "usefulness_rate": _ratio(useful, total),
        "usefulness_reviewed_deliveries": delivery_total,
        "delivery_weighted_usefulness": _ratio(delivery_useful, delivery_total),
        "fact_checked_events": factual,
        "factual_errors": error,
        "factual_error_rate": _ratio(error, factual),
    }


def _technical(cases: list[dict]) -> dict:
    fields = (
        "delivered_count", "delivery_failures", "llm_calls", "provider_attempts",
        "total_tokens", "rate_limit_attempts", "operating_cost_usd",
        "same_event_duplicates", "same_family_duplicates",
    )
    output = {}
    for field in fields:
        measured = [c["observed"][field] for c in cases
                    if field in c.get("observed", {})]
        output[field] = {
            "measured_events": len(measured),
            "total": sum(measured) if measured else None,
        }
    return output


def report(dataset: dict, labels: dict | None = None, agreement: dict | None = None) -> dict:
    cases = dataset["cases"]
    labels = labels or {}
    def scope(rows: list[dict]) -> dict:
        return {
            "events": len(rows),
            "types": dict(sorted(Counter(c["scenario_type"] for c in rows).items())),
            "event_level": _confusion(rows, labels),
            "recipient_eligible_weighted": _confusion(
                rows, labels, weight_field="eligible_recipients"
            ),
            "final_text": _quality(rows, labels),
            "technical_observations": _technical(rows),
        }
    return {
        "provenance": "REAL_MARKET_FROZEN; no external calls; unlabelled != negative",
        "version": dataset.get("version"),
        "dataset_sha256": dataset["dataset_sha256"],
        "real_market_usable_cases": len(cases),
        "target_case_count": "150-200",
        "agreement": agreement or {"reviewed_by_both": 0, "disagreements": []},
        "overall": scope(cases),
        "by_symbol": {
            symbol: scope([case for case in cases if case["symbol"] == symbol])
            for symbol in sorted(SYMBOLS)
        },
    }


def compare_recorded_run(
    dataset: dict, run_path: str | Path, labels: dict | None = None,
    agreement: dict | None = None,
) -> dict:
    """Compare recorded, already-validated model results without an API call.

    A candidate never inherits baseline deliveries, messages or provider telemetry.
    A failed provider call is unknown, not an implicit negative prediction.
    """
    run = json.loads(Path(run_path).read_text(encoding="utf-8"))
    if run.get("dataset_sha256") != dataset["dataset_sha256"]:
        raise ValueError("Candidate run does not match frozen inputs")
    if not run.get("model") or not run.get("config_fingerprint"):
        raise ValueError("Candidate run must pin model and configuration")
    cases_by_id = {case["id"]: case for case in dataset["cases"]}
    candidate_results = {}
    for item in run.get("results", []):
        key = item.get("id")
        if key not in cases_by_id or key in candidate_results:
            raise ValueError("Unknown or repeated candidate case ID")
        if item.get("input_sha256") != cases_by_id[key]["input_sha256"]:
            raise ValueError("Candidate input changed from frozen benchmark")
        status = item.get("status")
        if status not in {"valid", "schema_error", "provider_error", "invalid_json"}:
            raise ValueError("Invalid replay status")
        decision = item.get("should_alert")
        if status == "valid" and type(decision) is not bool:
            raise ValueError("A valid replay needs a validated boolean decision")
        if status != "valid" and decision is not None:
            raise ValueError("A failed replay cannot be scored as a decision")
        obs = {"should_alert": decision}
        for key_name in (
            "llm_calls", "provider_attempts", "total_tokens",
            "rate_limit_attempts", "operating_cost_usd",
        ):
            if key_name in item:
                obs[key_name] = item[key_name]
        candidate_results[key] = obs
    candidates = [
        {**case, "observed": candidate_results.get(case["id"], {})}
        for case in dataset["cases"]
    ]
    baseline = report(dataset, labels, agreement)
    candidate = report({**dataset, "cases": candidates}, labels, agreement)
    paired = [
        (case["observed"]["should_alert"], candidate_results[case["id"]]["should_alert"])
        for case in dataset["cases"]
        if type(case.get("observed", {}).get("should_alert")) is bool
        and type(candidate_results.get(case["id"], {}).get("should_alert")) is bool
    ]
    return {
        "dataset_sha256": dataset["dataset_sha256"],
        "run_name": run.get("run_name"),
        "model": run["model"],
        "config_fingerprint": run["config_fingerprint"],
        "recorded_results": len(candidate_results),
        "paired_valid_decisions": len(paired),
        "paired_decision_changes": sum(left != right for left, right in paired),
        "baseline": baseline,
        "candidate": candidate,
    }
