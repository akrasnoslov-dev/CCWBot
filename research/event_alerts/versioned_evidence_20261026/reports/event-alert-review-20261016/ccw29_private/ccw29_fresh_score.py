"""CCW-29 new unseen 20-case holdout: verified sealed inputs, model replies, exploratory blind-label scoring."""
from __future__ import annotations
import collections,hashlib,json,pathlib,statistics,subprocess,sys
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016"
F=BASE/"ccw29_private/fresh_holdout"
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import digest,load_frozen
from bot.alerting.event_identity import _json_dumps
from bot.services.ai_agent_groq import _event_significance_prompt_payload
blind=json.loads((F/"holdout_20_blind_packet_PRIVATE.json").read_text(encoding="utf-8"))
manifest=json.loads((F/"holdout_manifest.json").read_text(encoding="utf-8"))
sealed=json.loads((F/"holdout_20_source_SEALED_PRIVATE.json").read_text(encoding="utf-8"))
labeldata=(F/"reviewer_gpt6_provisional_blind.json").read_bytes()
assert hashlib.sha256(labeldata).hexdigest()=="e90075842d5765cdeb5708b20515964f60c6e3f34a79638e4173dcbd3d0ccd2e"
review=json.loads(labeldata)
ds="cb087b1a52e32b48f96dabda9d9dbf72744fcdb37c273a906572567005fef873"
assert blind["dataset_sha256"]==manifest["dataset_sha256"]==sealed["dataset_sha256"]==review["dataset_sha256"]==ds
assert hashlib.sha256((F/"holdout_20_blind_packet_PRIVATE.json").read_bytes()).hexdigest()==manifest["blind_packet_sha256"]
assert len(blind["cases"])==len(review["labels"])==len(sealed["cases"])==20 and digest(sealed["cases"])==ds
assert {c["input_sha256"] for c in blind["cases"]}.isdisjoint({c["input_sha256"] for c in load_frozen(BASE/"v2_private_sanitized.json")["cases"]})
assert all("2026-10-17"<=c["source_utc"][:10]<"2026-10-23" for c in sealed["cases"])
labels={r["id"]:r["warrant"] for r in review["labels"]}
assert set(labels)=={c["id"] for c in blind["cases"]}
assert collections.Counter(labels.values())=={"alert":1,"no_alert":15,"ambiguous":4}
instr={}
for key,fn,sha in [
 ("e1","ccw43_incremental_market_leg_v1.txt","af47056653aa7257ffe0ab5e339f216b45f889cc6c18890472492a5622a77247"),
 ("e2","ccw43_two_sided_counterfactual_v1.txt","aab1596ee2cf8432a9bb7a427323d3a23a76e82e16f02b0b640a8cfd790f8228")]:
 t=(BASE/"ccw43_private"/fn).read_text(encoding="utf-8").rstrip("\n")
 assert hashlib.sha256(t.encode()).hexdigest()==sha
 instr[key]=t
def metric(predictions):
 n=collections.Counter();bad=0
 for id,w in labels.items():
  if id not in predictions:
   n["missing"]+=1;continue
  if w=="ambiguous":n["ambiguous"]+=1;continue
  yes=predictions[id]["decision"]["should_alert"]
  n["TP" if w=="alert" and yes else "FP" if w=="no_alert" and yes else "FN" if w=="alert" else "TN"]+=1
 tp,fp,fn=n["TP"],n["FP"],n["FN"]
 return {**{name:n[name] for name in ("TP","FP","FN","TN","ambiguous","missing")},
  "scored":tp+fp+fn+n["TN"],
  "precision":round(tp/(tp+fp),4) if tp+fp else None,
  "recall":round(tp/(tp+fn),4) if tp+fn else None}
scores={"artifact":"CCW29_NEW_UNSEEN_20","dataset_sha256":ds,
 "owner_review_status":"NOT_DONE","review_reference":"GPT6_PROVISIONAL_NOT_INDEPENDENT_OF_PROMPT_DESIGN",
 "provisional_label_counts":dict(collections.Counter(labels.values())),
 "blind_label_sha256":hashlib.sha256(labeldata).hexdigest(),"providers":{}}
case_by_id={c["id"]:c for c in blind["cases"]}
comp=[]
for provider in ("groq","cloudflare"):
 s=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops",
                   f"cat /home/ccwbot_ops/ccw29_fresh_holdout/{provider}-ledger.json"],
                  capture_output=True,timeout=25)
 if s.returncode:print("MISSING_PROVIDER_LEDGER",provider);continue
 filename=F/(provider+"-ledger_PRIVATE.json")
 filename.write_bytes(s.stdout)
 j=json.loads(s.stdout)
 assert j["dataset_sha256"]==ds and j["provider"]==provider
 pred={};stat=collections.Counter()
 for row in j["attempts"]:
  stat[row["status"]]+=1
  id,v=row["id"],row["prompt"]
  assert id in case_by_id and v in instr and row["input_sha256"]==case_by_id[id]["input_sha256"]
  prompt=instr[v]+"\nInput JSON:\n"+_json_dumps(_event_significance_prompt_payload(case_by_id[id]["input"]))
  assert hashlib.sha256(prompt.encode()).hexdigest()==row["prompt_sha256"],"model-visible input integrity failed"
  if row["status"]=="valid":
   assert row["http_status"]==200 and row["decision"]["symbol"]==case_by_id[id]["symbol"]
   assert (id,v) not in pred
   pred[(id,v)]=row
   comp.append({"case_id":id,"symbol":case_by_id[id]["symbol"],"reference_provisional":labels[id],
                "provider":provider,"prompt":v,"decision":row["decision"],"source_sha256":row["input_sha256"]})
 groups={v:{id:val for (id,k),val in pred.items() if k==v} for v in instr}
 scores["providers"][provider]={
  "attempts":len(j["attempts"]),"status_counts":dict(stat),
  "unique_valid":len(pred),"expected":40,
  "ledger_sha256":hashlib.sha256(s.stdout).hexdigest(),
  "by_prompt":{v:{"coverage":len(data),
                  "metrics_provisional_not_authoritative":metric(data),
                  "token_usage_total":sum(row.get("total_tokens",0) for row in data.values()),
                  "median_latency_ms":statistics.median(row["duration_ms"] for row in data.values()) if data else None,
                  "positive_decisions":sum(row["decision"]["should_alert"] for row in data.values())} for v,data in groups.items()}}
(F/"fresh_holdout_metrics_PRIVATE.json").write_text(json.dumps(scores,indent=2)+"\n",encoding="utf-8")
(F/"fresh_holdout_predictions_PRIVATE.json").write_text(json.dumps({"dataset_sha256":ds,"matches":comp},indent=2)+"\n",encoding="utf-8")
print(json.dumps(scores,indent=2))
