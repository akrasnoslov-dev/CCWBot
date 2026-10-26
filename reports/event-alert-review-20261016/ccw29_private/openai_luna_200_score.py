"""Verify and score OpenAI Luna CCW-29 200x2 private isolated evaluation."""
import collections,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016"
HERE=BASE/"ccw29_private/full_200_v2"
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import load_frozen
from bot.services.ai_agent_groq import _event_significance_prompt_payload
from bot.alerting.event_identity import _json_dumps
doc=load_frozen(BASE/"v2_private_sanitized.json")
assert doc["dataset_sha256"]=="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
inputs={c["id"]:c for c in doc["cases"]};assert len(inputs)==200
owner=json.loads((BASE/"ccw41_private/owner_reference_candidate_v1_20261022.json").read_text(encoding="utf-8"))
labels={r["id"]:r["final"] for r in owner["case_labels"]}
assert set(labels)==set(inputs)
manifest=json.loads((HERE/"manifest_private.json").read_text(encoding="utf-8"))
prompts={}
for name,h in manifest["prompt_instruction_sha256"].items():
 v=(HERE/("candidate_"+name+".txt")).read_text(encoding="utf-8").rstrip("\n")
 assert hashlib.sha256(v.encode()).hexdigest()==h
 prompts[name]=v
remote="cat /home/ccwbot_ops/ccw29_full200_v2/openai-luna-ledger.json"
r=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops",remote],capture_output=True,timeout=30)
assert r.returncode==0 and r.stdout
(HERE/"openai-luna-ledger_PRIVATE.json").write_bytes(r.stdout)
ledger=json.loads(r.stdout)
assert ledger["dataset_sha256"]==doc["dataset_sha256"] and ledger["model"]=="gpt-6-luna" and ledger["budget_usd"]==1.0
valid={};spent=0
for row in ledger["attempts"]:
 id,p=row["id"],row["prompt"]
 assert id in inputs and p in prompts and row["input_sha256"]==inputs[id]["input_sha256"]
 content=prompts[p]+"\nInput JSON:\n"+_json_dumps(_event_significance_prompt_payload(inputs[id]["input"]))
 assert hashlib.sha256(content.encode()).hexdigest()==row["prompt_sha256"]
 cost=row.get("estimated_charged_usd",row.get("reserved_usd",0))
 assert 0<=cost<=row["reserved_usd"]+0.0000001
 spent+=cost
 if row["status"]=="valid":
  assert row["http_status"]==200 and row["decision"]["symbol"]==inputs[id]["symbol"]
  assert (id,p) not in valid
  valid[(id,p)]=row
assert spent<=1.0000001
def score(prompt,symbol=None):
 cnt=collections.Counter()
 for id,c in inputs.items():
  if symbol is not None and c["symbol"]!=symbol:continue
  row=valid.get((id,prompt))
  if row is None:cnt["missing"]+=1;continue
  label=labels[id]
  if label=="ambiguous":cnt["ambiguous"]+=1;continue
  yes=row["decision"]["should_alert"]
  cnt["TP" if label=="alert" and yes else "FP" if label=="no_alert" and yes else "FN" if label=="alert" else "TN"]+=1
 TP,FP,FN=cnt["TP"],cnt["FP"],cnt["FN"]
 return {**{k:cnt[k] for k in ("TP","FP","FN","TN","ambiguous","missing")},
  "precision":round(TP/(TP+FP),4) if TP+FP else None,"recall":round(TP/(TP+FN),4) if TP+FN else None,
  "accuracy":round((TP+cnt["TN"])/(TP+FP+FN+cnt["TN"]),4) if TP+FP+FN+cnt["TN"] else None}
out={"model":"gpt-6-luna","source":"reused_200_not_blind","cases":200,"requests_expected":400,
 "attempts":len(ledger["attempts"]),"unique_valid":len(valid),"cost_usd_conservative":round(spent,6),
 "status_counts":dict(collections.Counter(x["status"] for x in ledger["attempts"])),
 "scores":{p:{"overall":score(p),"per_symbol":{s:score(p,s) for s in ("BTC","ETH","GRAM","SOL")}} for p in prompts}}
(HERE/"openai_luna_metrics_PRIVATE.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"model":out["model"],"unique_valid":out["unique_valid"],"requests_expected":400,
 "cost_usd_conservative":out["cost_usd_conservative"],"status_counts":out["status_counts"],
 "scores":{p:x["overall"] for p,x in out["scores"].items()}},indent=2))
