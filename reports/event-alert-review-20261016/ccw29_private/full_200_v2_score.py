"""CCW-29 new full-200 read-only collector, per-provider owner-label scoring; no predictions sent elsewhere."""
from __future__ import annotations
import collections,hashlib,io,json,pathlib,subprocess,sys,tarfile
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016"
HERE=BASE/"ccw29_private/full_200_v2"
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import load_frozen
from bot.services.ai_agent_groq import _event_significance_prompt_payload
from bot.alerting.event_identity import _json_dumps
source=load_frozen(BASE/"v2_private_sanitized.json")
assert len(source["cases"])==200 and source["dataset_sha256"]=="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
by_id={c["id"]:c for c in source["cases"]}
original_owner=json.loads((BASE/"ccw41_private/owner_reference_candidate_v1_20261022.json").read_text(encoding="utf-8"))
owner={r["id"]:r["final"] for r in original_owner["case_labels"]}
assert set(owner)==set(by_id)
manifest=json.loads((HERE/"manifest_private.json").read_text())
assert manifest["expected_calls"]==800 and manifest["case_count"]==200
instructions={}
for name,sha in manifest["prompt_instruction_sha256"].items():
 t=(HERE/f"candidate_{name}.txt").read_text(encoding="utf-8").rstrip("\n")
 assert hashlib.sha256(t.encode()).hexdigest()==sha
 instructions[name]=t
ledgers={}
cmd="cd /home/ccwbot_ops/ccw29_full200_v2; tar -cf - groq-0-ledger.json cloudflare-0-ledger.json cloudflare-1-ledger.json cloudflare-2-ledger.json cloudflare-3-ledger.json"
r=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops",cmd],capture_output=True,timeout=45)
assert r.stdout,"No isolated provider ledgers available"
with tarfile.open(fileobj=io.BytesIO(r.stdout),mode="r:") as tf:
 for member in tf:
  name=pathlib.Path(member.name).name
  if not name.endswith("-ledger.json"):continue
  raw=tf.extractfile(member).read()
  ledgers[name]=json.loads(raw)
  (HERE/(name[:-5]+"_PRIVATE.json")).write_bytes(raw)
assert len(ledgers)==5,"Missing one or more provider shard ledgers"
pred={}
status={}
for provider in ("groq","cloudflare"):
 attempts=[];observed={}
 for shard in range(1 if provider=="groq" else 4):
  name=f"{provider}-{shard}-ledger.json"
  doc=ledgers[name]
  assert doc["dataset_sha256"]==source["dataset_sha256"] and doc["provider"]==provider and doc["shard"]==shard
  for row in doc["attempts"]:
   id,key=row["id"],row["prompt"]
   assert id in by_id and key in instructions and row["input_sha256"]==by_id[id]["input_sha256"]
   user=instructions[key]+"\nInput JSON:\n"+_json_dumps(_event_significance_prompt_payload(by_id[id]["input"]))
   assert hashlib.sha256(user.encode()).hexdigest()==row["prompt_sha256"],"Model-visible prompt hash changed"
   if row["status"]=="valid":
    assert row["http_status"]==200 and row["decision"]["symbol"]==by_id[id]["symbol"]
    assert (id,key) not in observed,"Duplicate valid case"
    observed[(id,key)]=row
   attempts.append(row)
 pred[provider]=observed
 status[provider]={"valid":len(observed),"expected":400,
    "attempts":len(attempts),"status_counts":dict(collections.Counter(x["status"] for x in attempts))}
def stats(rows,truth):
 counts=collections.Counter()
 usage=0
 for id,c in by_id.items():
  if id not in rows:
   counts["missing"]+=1;continue
  value=rows[id]["decision"]["should_alert"] if "decision" in rows[id] else rows[id]["observed"]["should_alert"]
  label=truth[id]
  if label=="ambiguous":counts["ambiguous"]+=1;continue
  counts["TP" if label=="alert" and value else "FP" if label=="no_alert" and value else "FN" if label=="alert" else "TN"]+=1
 TP,FP,FN=counts["TP"],counts["FP"],counts["FN"]
 return {**{k:counts[k] for k in ("TP","FP","FN","TN","ambiguous","missing")},
  "scored":TP+FP+FN+counts["TN"],"precision":round(TP/(TP+FP),4) if TP+FP else None,
  "recall":round(TP/(TP+FN),4) if TP+FN else None}
baseline={id:{"observed":c["observed"]} for id,c in by_id.items()}
out={"dataset_sha256":source["dataset_sha256"],"source_case_count":200,"owner_labels":dict(collections.Counter(owner.values())),
 "dataset_status":"REUSED_TUNING_200_NOT_BLIND_HOLDOUT","baseline_historical_production":stats(baseline,owner),
 "providers":status,"new_candidates":{}}
for provider in ("groq","cloudflare"):
 out["new_candidates"][provider]={}
 for prompt in instructions:
  vals={id:row for (id,k),row in pred[provider].items() if k==prompt}
  metrics=stats(vals,owner)
  metrics["valid_case_count"]=len(vals)
  metrics["reported_total_tokens"]=sum(r.get("total_tokens",0) for r in vals.values())
  metrics["per_symbol"]={}
  for sym in ("BTC","ETH","GRAM","SOL"):
   relevant={id:row for id,row in vals.items() if by_id[id]["symbol"]==sym}
   reltruth={id:owner[id] for id in relevant}
   c=collections.Counter()
   for id,row in relevant.items():
    lbl=owner[id]
    if lbl=="ambiguous":c["ambiguous"]+=1;continue
    yes=row["decision"]["should_alert"]
    c["TP" if lbl=="alert" and yes else "FP" if lbl=="no_alert" and yes else "FN" if lbl=="alert" else "TN"]+=1
   metrics["per_symbol"][sym]={**{x:c[x] for x in ("TP","FP","FN","TN","ambiguous")},"valid":len(relevant)}
  out["new_candidates"][provider][prompt]=metrics
(HERE/"full200_interim_metrics_PRIVATE.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in out.items() if k!="new_candidates"},indent=2))
for provider,d in out["new_candidates"].items():
 for name,v in d.items():
  print("SCORE",provider,name,json.dumps({k:x for k,x in v.items() if k!="per_symbol"}))
