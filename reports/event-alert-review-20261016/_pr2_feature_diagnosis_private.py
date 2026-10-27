"""Private local compact feature comparison of benchmark model errors."""
import json
from pathlib import Path
from scripts.event_alert_benchmark import load_frozen
from scripts.live_event_significance_benchmark import load_reviewer_a
from bot.services.ai_agent_groq import _event_significance_prompt_payload
p=Path("reports/event-alert-review-20261016")
d=load_frozen(p/"v2_private_sanitized.json")
labels=load_reviewer_a(p/"reviewer_A_significance_for_pr1.json",d)
byid={x["id"]:x for x in d["cases"]}
for folder,v in [
("fallback_cloudflare_path_facts","path_facts"),
("fallback_cloudflare_balanced_novelty","balanced_novelty"),
("fallback_gemini_production_gemini-3.5-flash-lite","production")]:
 f=p/"merged_pilots_private"/folder/"replay_state.json"
 if not f.exists(): continue
 state=json.loads(f.read_text())
 print("====",folder)
 for row in state["runs"][v]:
  if row["status"]!="valid":continue
  true=labels[row["id"]]=="alert"
  if row["should_alert"]==true:continue
  market=_event_significance_prompt_payload(byid[row["id"]]["input"])
  m=market["m"]
  print(byid[row["id"]]["symbol"],"label",true,"pred",row["should_alert"],
        "cw",m.get("cw"),"pw",m.get("pw"),"p24",m.get("p24"),"c24",m.get("c24"),
        "w",m.get("w"),"c30",m.get("c30"),"c60",m.get("c60"),
        "prev",market.get("prev"),"cnt",market.get("cnt"))
