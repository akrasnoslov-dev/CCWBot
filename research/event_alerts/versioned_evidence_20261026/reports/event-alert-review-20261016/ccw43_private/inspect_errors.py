import json
from pathlib import Path
h=Path(__file__).resolve().parent
rows=json.loads((h/"pilot_case_audit_PRIVATE.json").read_text())["cases"]
for a in rows:
    sig=a["signals"];g=a["decisions"]["groq"];c=a["decisions"]["cloudflare"]
    verdict=lambda d: ("ALERT" if d["should_alert"] else d["materiality"]+"/"+d["novelty"])
    decisions=lambda p: " G:"+verdict(g[p])+" C:"+verdict(c[p])
    if a["owner"]=="alert" or any(v["should_alert"] for v in (g["production"],c["production"],g["ccw15_novelty_independent_v1"],c["ccw15_novelty_independent_v1"])):
      print("CASE",a["id"],"SYMBOL",sig["symbol"],"A",a["original_A"],"OWNER",a["owner"],"C",a["reviewer_C"],"SCEN",sig["scenario_type"],"TAGS",sig["tags"])
      print("  Market: window",round(sig["window_pct"] or 0,3),"1h",sig["pct_1h"],"30m",sig["pct_30m"],"24h",sig["pct_24h"],"pctl",sig["relative_window_percentile"],"since_last",sig["since_last_pct"],"prior_age",sig["prior_alert_age_mins"],"prior_move",sig["prior_alert_move_pct"],"counts",sig["recent_counts"])
      for p in ["production","ccw15_materiality_evidence_v1","ccw15_novelty_independent_v1"]:
        print(" ",p,decisions(p))
      print(" C rationale:",(a["C_rationale"] or "")[:650])
