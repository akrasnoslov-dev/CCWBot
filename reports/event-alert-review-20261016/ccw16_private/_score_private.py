"""Private CCW16 summary: downloads only restricted experiment ledger, never keys or prompts."""
from pathlib import Path
import subprocess
import sys
from collections import Counter
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.event_alert_benchmark import load_frozen, _read_evaluations
from scripts.ccw16_dual_provider_pilot import score
import json

root=Path(r"D:\Projects\CCWBot")
dir=root/"reports"/"event-alert-review-20261016"
out=dir/"ccw16_private"/"pilot-ledger.json"
run=subprocess.run([
    "scp","-B","-o","BatchMode=yes",
    "ccwbot-prod-ops:/home/ccwbot_ops/ccw16_replay/pilot-ledger.json",
    str(out)
],capture_output=True,text=True,timeout=30)
if run.returncode: raise RuntimeError("Experiment ledger retrieval failed")
data=json.loads(out.read_text())
ds=load_frozen(dir/"v2_private_sanitized.json")
_,labels=_read_evaluations(dir/"reviewer_A_significance_for_pr1.json",ds)
rows=data["attempts"]
groups={}
for x in rows:
    if x.get("status")!="valid": continue
    dec=x.get("decision",{})
    if "should_alert" not in dec: continue
    gt=labels[x["id"]]["warrant"]
    groups.setdefault(x["provider"],[]).append({"warrant":gt,"decision":dec["should_alert"],
        "reserved":x["reserved_units"],"tokens":x.get("total_tokens")})
result={"total_attempts":len(rows),"errors":dict(Counter(x["status"] for x in rows))}
for prov,r in groups.items():
    result[prov]={"n":len(r),"matched_A":sum((a["decision"]==(a["warrant"]=="alert"))
        for a in r if a["warrant"]!="ambiguous"),
        "scored_A":sum(a["warrant"]!="ambiguous" for a in r),
        "ambiguous_A":sum(a["warrant"]=="ambiguous" for a in r),
        "reserved_units":sum(a["reserved"] for a in r),
        "actual_tokens":sum(a["tokens"] or 0 for a in r),
        "decisions":[a["decision"] for a in r]}
print(json.dumps(result,sort_keys=True))
