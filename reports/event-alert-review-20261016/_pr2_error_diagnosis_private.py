"""Local error diagnosis on frozen benchmark, no API or repo modifications."""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict, Counter
from scripts.event_alert_benchmark import load_frozen
from scripts.live_event_significance_benchmark import load_reviewer_a
root = Path("reports/event-alert-review-20261016")
dataset=load_frozen(root/"v2_private_sanitized.json")
labels=load_reviewer_a(root/"reviewer_A_significance_for_pr1.json",dataset)
byid={x["id"]:x for x in dataset["cases"]}
for folder, variant in (
 ("fallback_cloudflare_path_facts","path_facts"),
 ("fallback_cloudflare_materiality_first","materiality_first"),
 ("fallback_cloudflare_balanced_novelty","balanced_novelty"),
 ("fallback_gemini_production_gemini-3.5-flash-lite","production"),
):
 f=root/"merged_pilots_private"/folder/"replay_state.json"
 if not f.exists():continue
 data=json.loads(f.read_text(encoding="utf8"))
 print("\n===",folder,"===",len(data["runs"][variant]))
 for row in data["runs"][variant]:
  if row["status"]!="valid":continue
  true=labels[row["id"]]=="alert"
  actual=row["should_alert"]
  if actual==true:continue
  case=byid[row["id"]]
  x=case["input"]
  market=x.get("market",{})
  print("  ",case["symbol"],"truth",true,"pred",actual,"reason",row.get("reason_code"),
        "m", {k:v for k,v in market.items() if k in ("chg_window_percent","window_minutes","chg_24h_percent","chg_30m_percent","chg_60m_percent","percentile_window","percentile_24h","sampled_path","path")},
        "other", {k:v for k,v in x.items() if k not in ("market","news") and k in ("previous_alert","recent_alert_counts")})
