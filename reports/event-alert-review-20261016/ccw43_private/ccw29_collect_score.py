"""Collect CCW-29 private result ledgers to workstation; validate source and score offline."""
from __future__ import annotations
import collections, hashlib, json, pathlib, subprocess, sys, statistics
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
HERE=ROOT/"reports"/"event-alert-review-20261016"/"ccw43_private"
DATA=HERE.parent
OUT=DATA/"ccw29_private"
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import load_frozen,_read_evaluations
from bot.services.ai_agent_groq import _EVENT_SIGNIFICANCE_INSTRUCTIONS,_event_significance_prompt_payload
from bot.alerting.event_identity import _json_dumps
doc=load_frozen(DATA/"v2_private_sanitized.json")
assert doc["dataset_sha256"]=="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
frozen={c["id"]:c for c in doc["cases"]}
manifest=json.loads((DATA/"ccw16_private/pilot-manifest.json").read_text())
pilot={c["id"]:c for c in manifest["cases"]}
assert len(pilot)==20
_,Ae=_read_evaluations(DATA/"reviewer_A_significance_for_pr1.json",doc)
OwnerDoc=json.loads((DATA/"ccw41_private/owner_reference_candidate_v1_20261022.json").read_text())
owner={x["id"]:x["final"] for x in OwnerDoc["case_labels"]}
A={id:x["warrant"] for id,x in Ae.items()}
instr={
 "production":_EVENT_SIGNIFICANCE_INSTRUCTIONS,
 "e1":(HERE/"ccw43_incremental_market_leg_v1.txt").read_text(encoding="utf-8").rstrip("\n"),
 "e2":(HERE/"ccw43_two_sided_counterfactual_v1.txt").read_text(encoding="utf-8").rstrip("\n")
}
assert hashlib.sha256(instr["e1"].encode()).hexdigest()=="af47056653aa7257ffe0ab5e339f216b45f889cc6c18890472492a5622a77247"
assert hashlib.sha256(instr["e2"].encode()).hexdigest()=="aab1596ee2cf8432a9bb7a427323d3a23a76e82e16f02b0b640a8cfd790f8228"
def score(group, ref):
 c=collections.Counter()
 for id,row in group.items():
  truth=ref[id]
  if truth=="ambiguous":c["ambiguous"]+=1;continue
  pred=row["decision"]["should_alert"]
  c["TP" if truth=="alert" and pred else "FP" if truth=="no_alert" and pred else "FN" if truth=="alert" else "TN"]+=1
 tp,fp,fn=c["TP"],c["FP"],c["FN"]
 return dict(**{k:c[k] for k in ("TP","FP","FN","TN","ambiguous")},scored=sum(c.values())-c["ambiguous"],precision=round(tp/(tp+fp),4) if tp+fp else None,recall=round(tp/(tp+fn),4) if tp+fn else None)
summary={"version":1,"dataset_sha256":doc["dataset_sha256"],"source":"ccw29_isolated_20261023","providers":{}}
for provider in ("cloudflare","groq"):
 ssh=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops",f"cat /home/ccwbot_ops/ccw29_replay/{provider}-ledger.json"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
 if ssh.returncode:raise RuntimeError("remote ledger unavailable: "+provider)
 raw=ssh.stdout
 (OUT/(provider+"-ledger_PRIVATE.json")).write_bytes(raw)
 led=json.loads(raw)
 assert led["dataset_sha256"]==doc["dataset_sha256"] and led["provider"]==provider
 valid={}
 for row in led["attempts"]:
  id,p=row["id"],row["prompt"]
  assert id in pilot and p in instr and row["input_sha256"]==frozen[id]["input_sha256"]
  orig=instr[p]+"\nInput JSON:\n"+_json_dumps(_event_significance_prompt_payload(frozen[id]["input"]))
  assert hashlib.sha256(orig.encode()).hexdigest()==row["prompt_sha256"],"staged prompt changed: "+id+"/"+p
  if row["status"]=="valid":
   assert row["http_status"]==200 and row["decision"]["symbol"]==frozen[id]["symbol"]
   assert (id,p) not in valid,"duplicate valid prediction"
   valid[(id,p)]=row
 groups={p:{id:valid[(id,p)] for id in pilot if (id,p) in valid} for p in instr}
 summary["providers"][provider]={
  "unique_valid":len(valid),"expected":60,
  "attempts":len(led["attempts"]),
  "status_counts":dict(collections.Counter(x["status"] for x in led["attempts"])),
  "ledger_sha256":hashlib.sha256(raw).hexdigest(),
  "comparisons":{p:{"count":len(g),"original_A":score(g,A),"owner_v1":score(g,owner),
       "reported_prompt_tokens":sum(r.get("prompt_tokens",0) for r in g.values()),
       "reported_completion_tokens":sum(r.get("completion_tokens",0) for r in g.values()),
       "reported_total_tokens":sum(r.get("total_tokens",0) for r in g.values()),
       "median_latency_ms":statistics.median(r["duration_ms"] for r in g.values()) if g else None} for p,g in groups.items()}
 }
(OUT/"interim_evidence_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,indent=2))
