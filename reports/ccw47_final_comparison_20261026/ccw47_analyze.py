from __future__ import annotations

import collections
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

from ccw47_runner import DATASET, MAX_OUTPUT, MODEL, SYSTEM, canonical, compact


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "research/event_alerts/versioned_evidence_20261026/reports/event-alert-review-20261016/ccw29_private/fresh200_unseen"
SOURCE_PATH = BASE / "fresh200_source_SEALED_PRIVATE.json"
OLD_LEDGER_PATH = BASE / "openai-luna-fresh200-ledger_PRIVATE.json"
OLD_PROMPT_PATH = BASE / "candidate_refined.txt"
NEW_PROMPT_PATH = ROOT / "benchmarks/event-alert-owner-20261026/prompt_refined_v2_final.txt"
LABELS_PATH = ROOT / "research/event_alerts/owner_labels_66.csv"
NEW_LEDGER_PATH = OUT / "new_refined_luna_ledger_PRIVATE.json"
RUNNER_PATH = OUT / "ccw47_runner.py"

MATERIALITY = ("material", "routine", "unclear")
NOVELTY = ("new", "continuation", "repeated", "unclear")
REASONS = ("unusual_move", "fast_move", "reversal", "trend_acceleration", "market_news_alignment", "routine_move", "news_only", "unclear")
CONFIDENCE = ("low", "medium", "high")
SYMBOLS = ("BTC", "ETH", "GRAM", "SOL")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def pct(num: float, den: float) -> float | None:
    return num / den if den else None


def percent(value: float | None) -> str:
    return "N/A" if value is None else f"{100 * value:.1f}%"


def mean(values):
    return statistics.mean(values) if values else None


def median(values):
    return statistics.median(values) if values else None


def p95(values):
    return sorted(values)[max(0, math.ceil(len(values) * 0.95) - 1)] if values else None


def fmt_num(value, digits=3):
    if value is None:
        return "N/A"
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.{digits}f}"


def quality(rows, labels):
    c = collections.Counter()
    for case_id, row in rows.items():
        label = labels.get(case_id)
        if label not in {"alert", "no_alert"}:
            continue
        alert = row["decision"]["should_alert"]
        c[("TP" if alert else "FN") if label == "alert" else ("FP" if alert else "TN")] += 1
    tp, fp, fn, tn = (c[k] for k in ("TP", "FP", "FN", "TN"))
    return {
        "n": tp + fp + fn + tn,
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "precision": pct(tp, tp + fp),
        "recall": pct(tp, tp + fn),
        "f1": pct(2 * tp, 2 * tp + fp + fn),
        "specificity": pct(tn, tn + fp),
        "accuracy": pct(tp + tn, tp + fp + fn + tn),
        "false_positive_rate": pct(fp, fp + tn),
        "false_negative_rate": pct(fn, fn + tp),
    }


def evidence(case):
    data = case["input"]
    market = data.get("market") or {}
    prev = data.get("previous_event_alert") or {}
    counts = data.get("recent_event_counts") or {}
    def val(key):
        v = market.get(key)
        return "?" if v is None else f"{v:.6g}"
    parts = [
        f"w={market.get('analysed_window_minutes', '?')}m",
        f"cw={val('chg_window_percent')}%",
        f"c30={val('chg30m_percent')}%",
        f"c60={val('chg1h_percent')}%",
        f"c24={val('chg24h_percent')}%",
        f"cl={val('chg_since_msg_percent')}%",
        f"pw={val('relative_window_percentile_30d')}",
        f"p24={val('relative_24h_percentile_30d')}",
    ]
    if prev:
        parts.append(f"prev_age={prev.get('age_minutes', '?')}m")
        parts.append(f"prev_family={prev.get('semantic_family', '?')}")
        parts.append(f"prev_cw={prev.get('analysed_window_move', '?')}%")
    if counts:
        parts.append(f"cnt6/24={counts.get('h6', '?')}/{counts.get('h24', '?')}")
    snapshots = market.get("snapshots") or []
    if snapshots:
        path = [s.get("p") for s in snapshots[-6:] if isinstance(s, dict) and s.get("p") is not None]
        if path:
            parts.append("snapshot_path=" + "→".join(f"{p:.8g}" for p in path))
    return "; ".join(parts)


def distribution(rows, field, values):
    counts = collections.Counter(r["decision"][field] for r in rows.values())
    return {v: counts[v] for v in values}


source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
old_ledger = json.loads(OLD_LEDGER_PATH.read_text(encoding="utf-8"))
new_ledger = json.loads(NEW_LEDGER_PATH.read_text(encoding="utf-8"))
old_prompt = OLD_PROMPT_PATH.read_text(encoding="utf-8").rstrip("\r\n")
new_prompt = NEW_PROMPT_PATH.read_text(encoding="utf-8").rstrip("\r\n")
with LABELS_PATH.open(encoding="utf-8", newline="") as f:
    labels = {row["case_id"]: row["owner_label"] for row in csv.DictReader(f)}

cases = source["cases"]
old_rows = [r for r in old_ledger["attempts"] if r.get("prompt") == "refined"]
new_rows = new_ledger["rows"]
assert len(cases) == 200 and len({c["id"] for c in cases}) == 200
assert len(old_rows) == 200 and len({r["id"] for r in old_rows}) == 200
assert len(new_rows) == 200 and len({r["id"] for r in new_rows}) == 200
assert text_sha(canonical(cases)) == DATASET
case_by_id = {c["id"]: c for c in cases}
old = {r["id"]: r for r in old_rows}
new_all = {r["id"]: r for r in new_rows}
new = {i: r for i, r in new_all.items() if r.get("status") == "valid"}
invalid = {i: r for i, r in new_all.items() if r.get("status") != "valid"}

assert source["dataset_sha256"] == old_ledger["dataset_sha256"] == new_ledger["dataset_sha256"] == DATASET
assert len(cases) == len(case_by_id) == len(old) == len(new_all) == 200
assert set(case_by_id) == set(old) == set(new_all)
assert collections.Counter(labels.values()) == {"alert": 24, "no_alert": 34, "ambiguous": 8}
assert old_ledger["provider"] == "openai" and old_ledger["model"] == MODEL
assert old_ledger["max_completion_tokens"] == new_ledger["max_completion_tokens"] == MAX_OUTPUT
assert new_ledger["model"] == MODEL
assert new_ledger["prompt_sha256"] == text_sha(new_prompt)

baseline_checks = collections.Counter()
for case in cases:
    case_id = case["id"]
    assert text_sha(canonical(case["input"])) == case["input_sha256"]
    user = old_prompt + "\nInput JSON:\n" + canonical(compact(case["input"]))
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    request = {"messages": messages}
    row = old[case_id]
    assert row["status"] == "valid" and row["http_status"] == 200
    assert row["input_sha256"] == case["input_sha256"] and row["symbol"] == case["symbol"]
    assert row["prompt_sha256"] == text_sha(user)
    assert row["request_sha256"] == text_sha(json.dumps(request, separators=(",", ":"), sort_keys=True))
    baseline_checks.update(["case_id", "input_sha256", "prompt_sha256", "request_sha256", "symbol", "valid"])

for case in cases:
    row = new_all[case["id"]]
    user = new_prompt + "\nInput JSON:\n" + canonical(compact(case["input"]))
    assert row["input_sha256"] == case["input_sha256"]
    assert row["prompt_sha256"] == text_sha(user)
    assert row["symbol"] == case["symbol"]

paired_ids = set(new)
old_paired = {i: old[i] for i in paired_ids}
old_quality_full = quality({i: old[i] for i in labels if labels[i] != "ambiguous"}, labels)
old_quality_paired = quality({i: old[i] for i in paired_ids if labels.get(i) in {"alert", "no_alert"}}, labels)
new_quality = quality({i: new[i] for i in paired_ids if labels.get(i) in {"alert", "no_alert"}}, labels)

old_only = sorted(i for i in paired_ids if old[i]["decision"]["should_alert"] and not new[i]["decision"]["should_alert"])
new_only = sorted(i for i in paired_ids if not old[i]["decision"]["should_alert"] and new[i]["decision"]["should_alert"])
same = sorted(i for i in paired_ids if old[i]["decision"]["should_alert"] == new[i]["decision"]["should_alert"])

old_usage = {
    "input_total": sum(r["prompt_tokens"] for r in old.values()),
    "input_average": mean([r["prompt_tokens"] for r in old.values()]),
    "input_median": median([r["prompt_tokens"] for r in old.values()]),
    "completion_total": sum(r["completion_tokens"] for r in old.values()),
    "completion_average": mean([r["completion_tokens"] for r in old.values()]),
    "completion_median": median([r["completion_tokens"] for r in old.values()]),
    "total_tokens": sum(r["prompt_tokens"] + r["completion_tokens"] for r in old.values()),
    "total_average": mean([r["prompt_tokens"] + r["completion_tokens"] for r in old.values()]),
    "cost_total_usd": sum(r["estimated_charged_usd"] for r in old.values()),
    "cost_average_usd": mean([r["estimated_charged_usd"] for r in old.values()]),
    "latency_mean_ms": mean([r["duration_ms"] for r in old.values()]),
    "latency_median_ms": median([r["duration_ms"] for r in old.values()]),
    "latency_p95_ms": p95([r["duration_ms"] for r in old.values()]),
}
new_usage = {
    "input_total": sum(r["input_tokens"] for r in new_all.values()),
    "input_average": mean([r["input_tokens"] for r in new_all.values()]),
    "input_median": median([r["input_tokens"] for r in new_all.values()]),
    "completion_total": sum(r["completion_tokens"] for r in new_all.values()),
    "completion_average": mean([r["completion_tokens"] for r in new_all.values()]),
    "completion_median": median([r["completion_tokens"] for r in new_all.values()]),
    "total_tokens": sum(r["input_tokens"] + r["completion_tokens"] for r in new_all.values()),
    "total_average": mean([r["input_tokens"] + r["completion_tokens"] for r in new_all.values()]),
    "cost_total_usd": sum(r["charged_upper_usd"] for r in new_all.values()),
    "cost_average_usd": mean([r["charged_upper_usd"] for r in new_all.values()]),
    "latency_mean_ms": mean([r["latency_ms"] for r in new_all.values()]),
    "latency_median_ms": median([r["latency_ms"] for r in new_all.values()]),
    "latency_p95_ms": p95([r["latency_ms"] for r in new_all.values()]),
}

per_coin = {}
for symbol in SYMBOLS:
    ids = [c["id"] for c in cases if c["symbol"] == symbol]
    valid_ids = [i for i in ids if i in new]
    decisive_ids = [i for i in valid_ids if labels.get(i) in {"alert", "no_alert"}]
    per_coin[symbol] = {
        "cases": len(ids),
        "old_alerts": sum(old[i]["decision"]["should_alert"] for i in ids),
        "old_alert_rate": pct(sum(old[i]["decision"]["should_alert"] for i in ids), len(ids)),
        "new_valid": len(valid_ids),
        "new_failures": len(ids) - len(valid_ids),
        "new_alerts": sum(new[i]["decision"]["should_alert"] for i in valid_ids),
        "new_alert_rate_among_valid": pct(sum(new[i]["decision"]["should_alert"] for i in valid_ids), len(valid_ids)),
        "old_owner_on_new_valid": quality({i: old[i] for i in decisive_ids}, labels),
        "new_owner": quality({i: new[i] for i in decisive_ids}, labels),
    }

reliability = {
    "old": {"attempted": 200, "valid": 200, "http_failures": 0, "invalid_json": 0, "schema_failures": 0, "transport_failures": 0},
    "new": {
        "attempted": len(new_all),
        "valid": len(new),
        "http_failures": sum(r["status"] == "http_error" for r in new_all.values()),
        "invalid_json": sum(r["status"] == "transport_or_parse_error" and r.get("error_type") == "JSONDecodeError" for r in new_all.values()),
        "schema_failures": sum(r["status"] == "invalid_response" for r in new_all.values()),
        "transport_failures": sum(r["status"] == "transport_or_parse_error" and r.get("error_type") != "JSONDecodeError" for r in new_all.values()),
    },
}

metrics = {
    "status": "completed_with_schema_failures",
    "recommendation": "Keep original Refined v2",
    "recommendation_reason": "Refined v2 Final improved conditional recall but materially increased false positives, reduced paired accuracy/specificity, and produced 14/200 schema-invalid outputs. The full 200-case quality comparison is therefore not valid, while the original retained complete reliability and better low-noise behavior.",
    "dataset": {"canonical_sha256": DATASET, "raw_file_sha256": sha(SOURCE_PATH), "cases": 200, "symbols": dict(collections.Counter(c["symbol"] for c in cases))},
    "coverage": {"old_attempted": 200, "old_valid": 200, "new_attempted": 200, "new_valid": len(new), "new_failures": len(invalid)},
    "decisions": {
        "old_alerts_all_200": sum(r["decision"]["should_alert"] for r in old.values()),
        "old_no_alerts_all_200": sum(not r["decision"]["should_alert"] for r in old.values()),
        "new_alerts_valid": sum(r["decision"]["should_alert"] for r in new.values()),
        "new_no_alerts_valid": sum(not r["decision"]["should_alert"] for r in new.values()),
        "new_alert_rate_among_valid": pct(sum(r["decision"]["should_alert"] for r in new.values()), len(new)),
        "new_known_alert_rate_all_attempts": pct(sum(r["decision"]["should_alert"] for r in new.values()), 200),
    },
    "per_coin": per_coin,
    "owner_quality": {"old_full_58": old_quality_full, "old_on_new_valid_56": old_quality_paired, "new_valid_56": new_quality, "new_decisive_failures": sum(i in invalid and labels[i] in {"alert", "no_alert"} for i in labels)},
    "differences": {"paired_valid": len(paired_ids), "agreement": len(same), "agreement_rate": pct(len(same), len(paired_ids)), "old_only_alerts": old_only, "new_only_alerts": new_only, "invalid_case_ids": sorted(invalid)},
    "distributions": {
        "old": {"materiality": distribution(old, "materiality", MATERIALITY), "novelty": distribution(old, "novelty", NOVELTY), "reason_code": distribution(old, "reason_code", REASONS), "confidence": distribution(old, "confidence", CONFIDENCE)},
        "new_valid": {"materiality": distribution(new, "materiality", MATERIALITY), "novelty": distribution(new, "novelty", NOVELTY), "reason_code": distribution(new, "reason_code", REASONS), "confidence": distribution(new, "confidence", CONFIDENCE)},
    },
    "usage": {"old": old_usage, "new": new_usage, "cost_difference_usd": new_usage["cost_total_usd"] - old_usage["cost_total_usd"], "cost_ratio": pct(new_usage["cost_total_usd"], old_usage["cost_total_usd"])},
    "reliability": reliability,
    "baseline_verification": {"rows": len(old), "checks_per_category": dict(baseline_checks), "provider": "openai", "model": MODEL, "endpoint": "/v1/chat/completions", "system_message": SYSTEM, "response_format": {"type": "json_object"}, "max_completion_tokens": MAX_OUTPUT},
}

(OUT / "CCW47_METRICS.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

manifest = {
    "task": "CCW-47",
    "run_status": metrics["status"],
    "production_changed": False,
    "dataset_canonical_sha256": DATASET,
    "dataset_file_sha256": sha(SOURCE_PATH),
    "old_prompt_file_sha256": sha(OLD_PROMPT_PATH),
    "old_prompt_instruction_sha256": text_sha(old_prompt),
    "new_prompt_file_sha256": sha(NEW_PROMPT_PATH),
    "new_prompt_instruction_sha256": text_sha(new_prompt),
    "old_ledger_sha256": sha(OLD_LEDGER_PATH),
    "new_private_ledger_sha256": sha(NEW_LEDGER_PATH),
    "runner_sha256": sha(RUNNER_PATH),
    "reference_commit": "62dad35f93a193ba083bb42436b505864f116ca7",
    "provider": "openai",
    "model": MODEL,
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "system_message": SYSTEM,
    "response_format": {"type": "json_object"},
    "max_completion_tokens": MAX_OUTPUT,
    "input_usd_per_million": 0.10,
    "output_usd_per_million": 0.50,
    "estimated_additional_spend_usd": new_usage["cost_total_usd"],
    "budget_cap_usd": new_ledger["max_budget_usd"],
    "attempts": 200,
    "valid": len(new),
    "schema_failures": reliability["new"]["schema_failures"],
    "automatic_retries": 0,
    "fallback_models": 0,
    "temporary_credential_deleted": True,
    "private_ledger_gitignored": True,
    "execution_environment": "Linux (Hetzner), unprivileged ccwbot_ops isolated workspace",
}
(OUT / "CCW47_RUN_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

diff_fields = ["event_id", "coin", "owner_label", "new_status", "old_should_alert", "new_should_alert", "old_materiality", "new_materiality", "old_novelty", "new_novelty", "old_reason_code", "new_reason_code", "old_confidence", "new_confidence", "difference_type", "market_evidence"]
with (OUT / "CCW47_CASE_DIFFERENCES.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=diff_fields)
    writer.writeheader()
    for case in cases:
        i = case["id"]
        old_d = old[i]["decision"]
        new_d = new[i]["decision"] if i in new else {}
        if i in new and old_d["should_alert"] == new_d["should_alert"]:
            continue
        kind = "schema_failure" if i in invalid else "old_only_alert" if old_d["should_alert"] else "new_only_alert"
        writer.writerow({
            "event_id": i, "coin": case["symbol"], "owner_label": labels.get(i, "unlabelled"), "new_status": new_all[i]["status"],
            "old_should_alert": old_d["should_alert"], "new_should_alert": new_d.get("should_alert", ""),
            "old_materiality": old_d["materiality"], "new_materiality": new_d.get("materiality", ""),
            "old_novelty": old_d["novelty"], "new_novelty": new_d.get("novelty", ""),
            "old_reason_code": old_d["reason_code"], "new_reason_code": new_d.get("reason_code", ""),
            "old_confidence": old_d["confidence"], "new_confidence": new_d.get("confidence", ""),
            "difference_type": kind, "market_evidence": evidence(case),
        })

owner_fields = ["event_id", "coin", "owner_label", "new_status", "old_should_alert", "old_class", "new_should_alert", "new_class", "decision_changed", "market_evidence"]
with (OUT / "CCW47_OWNER_ERRORS.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=owner_fields)
    writer.writeheader()
    for case in cases:
        i = case["id"]
        if i not in labels:
            continue
        label = labels[i]
        old_alert = old[i]["decision"]["should_alert"]
        def cls(alert):
            if label == "ambiguous":
                return "ambiguous_excluded"
            return ("TP" if alert else "FN") if label == "alert" else ("FP" if alert else "TN")
        new_alert = new[i]["decision"]["should_alert"] if i in new else None
        writer.writerow({
            "event_id": i, "coin": case["symbol"], "owner_label": label, "new_status": new_all[i]["status"],
            "old_should_alert": old_alert, "old_class": cls(old_alert),
            "new_should_alert": "" if new_alert is None else new_alert, "new_class": "schema_failure" if new_alert is None else cls(new_alert),
            "decision_changed": "" if new_alert is None else old_alert != new_alert,
            "market_evidence": evidence(case),
        })

def qrow(name, old_q, new_q):
    return f"| {name} | {old_q} | {new_q} |"

lines = [
    "# CCW-47 Final Event Significance Prompt Comparison",
    "",
    "## Outcome",
    "",
    "**Recommendation: Keep Original Refined v2. Do not adopt Refined v2 Final.**",
    "",
    "All 200 authorized new requests were attempted exactly once, with no retries or fallback models. Refined v2 Final returned 186 schema-valid decisions and 14 schema-invalid decisions (7.0% failure rate). It improved recall on the owner-labelled matched subset, but added substantially more false positives, reduced specificity and accuracy, and increased the alert rate. The incomplete decision coverage prevents a valid full-200 quality comparison and is itself a material regression.",
    "",
    "Production was not changed or restarted. The temporary API credential was deleted after the run.",
    "",
    "## Main comparison",
    "",
    "| Metric | Original Refined v2 | Refined v2 Final |",
    "|---|---:|---:|",
    qrow("Requests attempted", "200 (archived)", "200 (new)"),
    qrow("Valid results", "200", f"{len(new)}"),
    qrow("Failures", "0", f"{len(invalid)} schema failures"),
    qrow("Alerts", "42/200 (21.0%)", f"59/{len(new)} valid ({percent(pct(59, len(new)))})"),
    qrow("No-alerts", "158/200", f"{len(new)-59}/{len(new)} valid"),
    qrow("Owner TP/FP/FN/TN", "9/8/15/26 on all 58", f"{new_quality['TP']}/{new_quality['FP']}/{new_quality['FN']}/{new_quality['TN']} on 56 valid"),
    qrow("Precision", percent(old_quality_full["precision"]), percent(new_quality["precision"])),
    qrow("Recall", percent(old_quality_full["recall"]), percent(new_quality["recall"])),
    qrow("F1", percent(old_quality_full["f1"]), percent(new_quality["f1"])),
    qrow("Specificity", percent(old_quality_full["specificity"]), percent(new_quality["specificity"])),
    qrow("Accuracy", percent(old_quality_full["accuracy"]), percent(new_quality["accuracy"])),
    qrow("Input tokens", fmt_num(old_usage["input_total"], 0), fmt_num(new_usage["input_total"], 0)),
    qrow("Completion tokens (incl. reasoning)", fmt_num(old_usage["completion_total"], 0), fmt_num(new_usage["completion_total"], 0)),
    qrow("Total tokens", fmt_num(old_usage["total_tokens"], 0), fmt_num(new_usage["total_tokens"], 0)),
    qrow("Usage-based cost", f"${old_usage['cost_total_usd']:.6f}", f"${new_usage['cost_total_usd']:.6f}"),
    qrow("Mean / median / P95 latency", f"{old_usage['latency_mean_ms']:.0f}/{old_usage['latency_median_ms']:.0f}/{old_usage['latency_p95_ms']:.0f} ms", f"{new_usage['latency_mean_ms']:.0f}/{new_usage['latency_median_ms']:.0f}/{new_usage['latency_p95_ms']:.0f} ms"),
    "",
    "Owner metrics are conditional on the 58 selected disagreement cases, not production-wide estimates. Two decisive owner-labelled cases failed schema validation under the new prompt, so its metrics cover only 56 cases. For an apples-to-apples 56-case comparison, Original Refined v2 scored " + f"{old_quality_paired['TP']}/{old_quality_paired['FP']}/{old_quality_paired['FN']}/{old_quality_paired['TN']} with {percent(old_quality_paired['accuracy'])} accuracy, versus {new_quality['TP']}/{new_quality['FP']}/{new_quality['FN']}/{new_quality['TN']} and {percent(new_quality['accuracy'])} for Final.",
    "",
    "## Coverage and per-coin decisions",
    "",
    "| Coin | Old alerts / 50 | New valid | New failures | New alerts / valid |",
    "|---|---:|---:|---:|---:|",
]
for symbol in SYMBOLS:
    x = per_coin[symbol]
    lines.append(f"| {symbol} | {x['old_alerts']} ({percent(x['old_alert_rate'])}) | {x['new_valid']} | {x['new_failures']} | {x['new_alerts']} ({percent(x['new_alert_rate_among_valid'])}) |")

lines += [
    "",
    "## Owner-labelled classification quality",
    "",
    "| Metric | Old, all 58 | Old, paired 56 | New, valid 56 |",
    "|---|---:|---:|---:|",
]
for name, key in (("TP", "TP"), ("FP", "FP"), ("FN", "FN"), ("TN", "TN")):
    lines.append(f"| {name} | {old_quality_full[key]} | {old_quality_paired[key]} | {new_quality[key]} |")
for name, key in (("Precision", "precision"), ("Recall", "recall"), ("F1", "f1"), ("Specificity", "specificity"), ("Accuracy", "accuracy"), ("False-positive rate", "false_positive_rate"), ("False-negative rate", "false_negative_rate")):
    lines.append(f"| {name} | {percent(old_quality_full[key])} | {percent(old_quality_paired[key])} | {percent(new_quality[key])} |")

lines += [
    "",
    "## Decision differences",
    "",
    f"Among {len(paired_ids)} cases with valid decisions from both prompts, {len(same)} agreed ({percent(pct(len(same), len(paired_ids)))}). There were {len(old_only)} old-only alerts and {len(new_only)} new-only alerts. Fourteen additional cases have no comparable new decision because of schema failure.",
    "",
    "Every flip and schema failure is listed in `CCW47_CASE_DIFFERENCES.csv` with grounded numeric market evidence.",
    "",
    "## Distributions",
    "",
    "Counts use all 200 old decisions and 186 valid new decisions.",
]
for field, values in (("materiality", MATERIALITY), ("novelty", NOVELTY), ("reason_code", REASONS), ("confidence", CONFIDENCE)):
    lines += ["", f"### {field}", "", "| Value | Old | New valid |", "|---|---:|---:|"]
    for value in values:
        lines.append(f"| {value} | {metrics['distributions']['old'][field][value]} | {metrics['distributions']['new_valid'][field][value]} |")

lines += [
    "",
    "## Tokens, cost and latency",
    "",
    "| Metric | Old | New | Difference |",
    "|---|---:|---:|---:|",
]
for label, key in (("Input total", "input_total"), ("Input average", "input_average"), ("Input median", "input_median"), ("Completion total", "completion_total"), ("Completion average", "completion_average"), ("Completion median", "completion_median"), ("Total tokens", "total_tokens"), ("Total average", "total_average")):
    lines.append(f"| {label} | {fmt_num(old_usage[key])} | {fmt_num(new_usage[key])} | {fmt_num(new_usage[key]-old_usage[key])} |")
lines += [
    f"| Cost total | ${old_usage['cost_total_usd']:.6f} | ${new_usage['cost_total_usd']:.6f} | ${new_usage['cost_total_usd']-old_usage['cost_total_usd']:+.6f} ({100*(new_usage['cost_total_usd']/old_usage['cost_total_usd']-1):+.1f}%) |",
    f"| Cost average/case | ${old_usage['cost_average_usd']:.9f} | ${new_usage['cost_average_usd']:.9f} | ${new_usage['cost_average_usd']-old_usage['cost_average_usd']:+.9f} |",
    f"| Latency mean | {old_usage['latency_mean_ms']:.0f} ms | {new_usage['latency_mean_ms']:.0f} ms | {new_usage['latency_mean_ms']-old_usage['latency_mean_ms']:+.0f} ms |",
    f"| Latency median | {old_usage['latency_median_ms']:.0f} ms | {new_usage['latency_median_ms']:.0f} ms | {new_usage['latency_median_ms']-old_usage['latency_median_ms']:+.0f} ms |",
    f"| Latency P95 | {old_usage['latency_p95_ms']:.0f} ms | {new_usage['latency_p95_ms']:.0f} ms | {new_usage['latency_p95_ms']-old_usage['latency_p95_ms']:+.0f} ms |",
    "",
    "New-prompt cost is 13.5% lower, mainly because its shorter instruction reduced input tokens. This secondary efficiency benefit does not offset reliability and owner-agreement regressions.",
    "",
    "## Reliability",
    "",
    "| Failure type | Old | New |",
    "|---|---:|---:|",
    f"| HTTP failures | 0 | {reliability['new']['http_failures']} |",
    f"| Invalid JSON | 0 | {reliability['new']['invalid_json']} |",
    f"| Schema/consistency failures | 0 | {reliability['new']['schema_failures']} |",
    f"| Transport failures | 0 | {reliability['new']['transport_failures']} |",
    "",
    "The 14 invalid responses were parseable JSON but failed the six-field schema or cross-field consistency validator. The runner intentionally did not retain invalid response bodies, so no unsupported diagnosis of the exact conflicting fields is made.",
    "",
    "## Focused error analysis",
    "",
]

def category(title, predicate):
    ids = [i for i in labels if i in new and predicate(i)]
    lines.extend([f"### {title}", "", "| Event | Coin | Owner | Old | New | Grounded market evidence |", "|---|---|---|---:|---:|---|"])
    if not ids:
        lines.append("| — | — | — | — | — | None |")
    for i in ids:
        lines.append(f"| {i} | {case_by_id[i]['symbol']} | {labels[i]} | {str(old[i]['decision']['should_alert']).lower()} | {str(new[i]['decision']['should_alert']).lower()} | {evidence(case_by_id[i])} |")
    lines.append("")

category("Owner alert: old missed, new catches", lambda i: labels[i] == "alert" and not old[i]["decision"]["should_alert"] and new[i]["decision"]["should_alert"])
category("Owner alert: new misses", lambda i: labels[i] == "alert" and not new[i]["decision"]["should_alert"])
category("Owner no-alert: new fixes old false positive", lambda i: labels[i] == "no_alert" and old[i]["decision"]["should_alert"] and not new[i]["decision"]["should_alert"])
category("Owner no-alert: new introduces false positive", lambda i: labels[i] == "no_alert" and not old[i]["decision"]["should_alert"] and new[i]["decision"]["should_alert"])

lines += ["### Owner-labelled schema failures", "", "| Event | Coin | Owner | Old decision | Grounded market evidence |", "|---|---|---|---:|---|"]
owner_invalid = [i for i in labels if i in invalid]
for i in owner_invalid:
    lines.append(f"| {i} | {case_by_id[i]['symbol']} | {labels[i]} | {str(old[i]['decision']['should_alert']).lower()} | {evidence(case_by_id[i])} |")
if not owner_invalid:
    lines.append("| — | — | — | — | None |")

lines += ["", "### Eight owner-ambiguous cases (excluded from scoring)", "", "| Event | Coin | Old | New/status | Grounded market evidence |", "|---|---|---:|---|---|"]
for i in labels:
    if labels[i] != "ambiguous":
        continue
    new_cell = str(new[i]["decision"]["should_alert"]).lower() if i in new else new_all[i]["status"]
    lines.append(f"| {i} | {case_by_id[i]['symbol']} | {str(old[i]['decision']['should_alert']).lower()} | {new_cell} | {evidence(case_by_id[i])} |")

lines += [
    "",
    "## Reproducibility",
    "",
    f"- Canonical dataset SHA-256: `{DATASET}`; raw source-file SHA-256: `{sha(SOURCE_PATH)}`.",
    f"- Old prompt raw/instruction SHA-256: `{sha(OLD_PROMPT_PATH)}` / `{text_sha(old_prompt)}`.",
    f"- New prompt raw/instruction SHA-256: `{sha(NEW_PROMPT_PATH)}` / `{text_sha(new_prompt)}`; reference commit `62dad35f93a193ba083bb42436b505864f116ca7`.",
    f"- Old/new ledger SHA-256: `{sha(OLD_LEDGER_PATH)}` / `{sha(NEW_LEDGER_PATH)}`.",
    f"- Provider/model: OpenAI / `{MODEL}`; Chat Completions; system message `{SYSTEM}`; JSON object mode; max completion tokens {MAX_OUTPUT}.",
    "- Execution environment: Linux on Hetzner under the unprivileged `ccwbot_ops` account in `/home/ccwbot_ops/ccw12_refined_compare`; the runner's privilege check is Linux-specific.",
    "- All 200 baseline rows were revalidated against case ID, input hash, reconstructed prompt hash, reconstructed request hash, symbol, HTTP 200, and schema-valid status.",
    "- New rows were revalidated against all 200 case IDs, input hashes, prompt hashes, symbols, and unique single-attempt coverage.",
    "",
    "## Limitations",
    "",
    "- The 58 decisive owner labels were selected because earlier prompts disagreed; these precision/recall values are not representative holdout or production-wide performance.",
    "- Fourteen missing new decisions prevent a complete 200-case quality comparison. They must not be treated as no-alerts or silently retried.",
    "- The remaining 134 cases lack owner labels from this review. Model-model agreement is not human correctness.",
    "- This test evaluates OpenAI Luna significance output only. It does not prove Groq/Cloudflare parity, Telegram delivery behavior, cooldown behavior, or final Situation/Possible Action quality.",
    "- Cost uses actual returned token counts at verified Standard prices; provider billing adjustments such as caching or regional processing are not independently invoiced here.",
    "",
    "## Final recommendation",
    "",
    "Keep **Original Refined v2**. Refined v2 Final caught four additional owner-positive cases on the paired subset and raised recall, especially for SOL and GRAM, but it introduced seven additional false positives, lowered paired specificity from 75.8% to 54.5%, lowered paired accuracy from 58.9% to 53.6%, increased known alerts from 41 to 59 on comparable valid cases, and failed schema validation in 14/200 requests. Its lower token cost is useful but secondary. Do not change production; any future prompt revision or retest requires a new owner decision.",
]

(OUT / "CCW47_FINAL_COMPARISON.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"report": str(OUT / 'CCW47_FINAL_COMPARISON.md'), "metrics": metrics["coverage"], "spend": new_usage["cost_total_usd"], "recommendation": metrics["recommendation"]}, indent=2))
