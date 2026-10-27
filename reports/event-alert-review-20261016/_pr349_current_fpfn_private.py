import json
from collections import Counter
from pathlib import Path
from scripts.event_alert_benchmark import load_frozen
from scripts.live_event_significance_benchmark import load_reviewer_a

root = Path("reports/event-alert-review-20261016")
data = load_frozen(root / "v2_private_sanitized.json")
labels = load_reviewer_a(root / "reviewer_A_significance_for_pr1.json", data)
by_id = {c["id"]: c for c in data["cases"]}
names = [
    ("cloudflare", "fallback_cloudflare_rebalanced_core", "rebalanced_core"),
    ("gemini", "fallback_gemini_rebalanced_core_gemini-3.5-flash-lite", "rebalanced_core"),
]
for provider, name, variant in names:
    state = json.loads((root / "merged_pilots_private" / name / "replay_state.json").read_text())
    counts = Counter()
    errors = []
    for row in state["runs"][variant]:
        if row["status"] != "valid" or labels[row["id"]] == "ambiguous":
            continue
        case = by_id[row["id"]]
        truth = labels[row["id"]] == "alert"
        pred = row["should_alert"]
        category = "TP" if truth and pred else "FN" if truth else "FP" if pred else "TN"
        counts[(case["symbol"], category)] += 1
        if truth != pred:
            m = case["input"].get("market", {})
            errors.append({"symbol": case["symbol"], "error": category,
                           "cw": m.get("cw"), "pw": m.get("pw"),
                           "w": m.get("w"), "c24": m.get("c24"),
                           "reason": row.get("reason_code")})
    print(provider, "matrix", sorted((f"{symbol}/{kind}", n) for (symbol, kind), n in counts.items()))
    print(provider, "errors", errors)
