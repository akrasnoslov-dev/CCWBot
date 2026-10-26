"""Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.
Frozen market inputs and both original evaluator exports remain unchanged.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.event_alert_benchmark import load_frozen, reconcile, report

here = Path(__file__).resolve().parent
frozen = here / "v2_private_sanitized.json"
a_file = here / "reviewer_A_significance_for_pr1.json"
b_file = here / "reviewer_B_significance_for_pr1.json"
data = load_frozen(frozen)
a = json.loads(a_file.read_text(encoding="utf-8"))
b = json.loads(b_file.read_text(encoding="utf-8"))
expected_sha = "ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
assert data["dataset_sha256"] == expected_sha
assert a["dataset_sha256"] == b["dataset_sha256"] == expected_sha
la = {x["id"]: x for x in a["labels"]}
lb = {x["id"]: x for x in b["labels"]}
case_ids = {c["id"] for c in data["cases"]}
assert len(case_ids) == len(la) == len(lb) == 200
disagreements = [
    {"id": c["id"], "warrant": la[c["id"]]["warrant"],
     "useful": la[c["id"]].get("useful"),
     "factual": la[c["id"]].get("factual")}
    for c in data["cases"]
    if la[c["id"]]["warrant"] != lb[c["id"]]["warrant"]
]
assert len(disagreements) == 99
resolution = {
    "dataset_sha256": expected_sha,
    "evaluator_id": "owner_decision_reviewer_A_reference_20261016",
    "labels": disagreements,
}
path = here / "owner_reviewer_A_resolution_private.json"
path.write_text(json.dumps(resolution, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
labels, agreement = reconcile(data, a_file, b_file, path)
assert agreement["unresolved_disagreements"] == 0
assert agreement["adjudicated"] == 99
assert all(labels[case_id]["warrant"] == la[case_id]["warrant"] for case_id in case_ids)
results = report(data, labels, agreement)
out = here / "baseline_reviewer_A_reference_private.json"
out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("dataset_sha256", expected_sha)
print("owner_choice: reviewer A is reference for 99 conflicting verdicts")
print("resolved_disagreements", agreement["adjudicated"], "unresolved", agreement["unresolved_disagreements"])
print("A_labels",dict(Counter(x["warrant"] for x in la.values())))
for sym, record in [("OVERALL",results["overall"]),*list(results["by_symbol"].items())]:
    event = record["event_level"]
    exposure = record["delivered_weighted_precision"]
    print(
        sym,"scored",event["scored_cases"],"ambiguous",event["ambiguous_cases"],
        "tp",event["tp"],"fp",event["fp"],"fn",event["fn"],"tn",event["tn"],
        "precision",round(100*event["precision"],2) if event["precision"] is not None else None,
        "recall",round(100*event["recall"],2) if event["recall"] is not None else None,
        "deliveries deserved",exposure["deserved_deliveries"],
        "unwanted",exposure["low_value_deliveries"],
        "ambiguous",exposure["ambiguous_deliveries"],
        "recipient-delivered precision",round(100*exposure["precision"],2)
           if exposure["precision"] is not None else None,
    )
print("saved_private",path.name,out.name)
