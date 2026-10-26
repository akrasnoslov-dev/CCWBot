"""CCW29: audit fresh-200 Luna paired replay; require two blind human labels for quality claims."""
import collections,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016/ccw29_private/fresh200_unseen"
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import digest
from bot.services.ai_agent_groq import _event_significance_prompt_payload
from bot.alerting.event_identity import _json_dumps
src=json.loads((BASE/"fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf8"))
manifest=json.loads((BASE/"fresh200_luna_manifest_PRIVATE.json").read_text(encoding="utf8"))
assert src["dataset_sha256"]==manifest["dataset_sha256"]=="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
byid={c["id"]:c for c in src["cases"]};assert len(byid)==200 and digest(src["cases"])==src["dataset_sha256"]
original={c["id"]:c["observed"]["should_alert"] for c in src["cases"]}
prompts={}
for name,h in manifest["instructions_sha256"].items():
 p=(BASE/("candidate_"+name+".txt")).read_text(encoding="utf8").rstrip("\n")
 assert hashlib.sha256(p.encode()).hexdigest()==h
 prompts[name]=p
res=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops",
 "cat /home/ccwbot_ops/ccw29_fresh200_luna/openai-luna-ledger.json"],capture_output=True,timeout=30)
assert res.returncode==0 and res.stdout,"Luna ledger missing"
(BASE/"openai-luna-fresh200-ledger_PRIVATE.json").write_bytes(res.stdout)
led=json.loads(res.stdout)
assert led["provider"]=="openai" and led["model"]=="gpt-6-luna" and led["dataset_sha256"]==src["dataset_sha256"]
assert led["budget_usd"]==0.85 and led["expected"]==600
votes={};counts=collections.Counter()
total_cost=0
for row in led["attempts"]:
 id,p=row["id"],row["prompt"]
 assert id in byid and p in prompts and byid[id]["input_sha256"]==row["input_sha256"]
 assert digest(byid[id]["input"])==row["input_sha256"]
 tx=prompts[p]+"\nInput JSON:\n"+_json_dumps(_event_significance_prompt_payload(byid[id]["input"]))
 assert hashlib.sha256(tx.encode()).hexdigest()==row["prompt_sha256"],"LLM input not original"
 counts[row["status"]]+=1
 cost=row.get("estimated_charged_usd",row.get("reserved_usd",0))
 assert 0<=cost<=row["reserved_usd"]+1e-7
 total_cost+=cost
 if row["status"]=="valid":
  assert row["http_status"]==200 and row["decision"]["symbol"]==byid[id]["symbol"]
  assert (id,p) not in votes
  votes[(id,p)]=row["decision"]["should_alert"]
assert total_cost<=0.8500001,"Budget exceeded"
def read_reviewer(name):
 f=BASE/("ccw29_blind_review_"+name+"_200.json")
 if not f.exists():return None
 doc=json.loads(f.read_text(encoding="utf8"))
 assert doc["dataset_sha256"]==src["dataset_sha256"] and len(doc["labels"])==200
 out={}
 for r in doc["labels"]:
  id=r["id"]
  assert id in byid and r["input_sha256"]==byid[id]["input_sha256"] and r["warrant"] in ("alert","no_alert","ambiguous")
  assert r["rationale"].strip() and id not in out
  out[id]=r["warrant"]
 assert set(out)==set(byid)
 return out
a=read_reviewer("A");b=read_reviewer("B")
ref={}
if a is not None and b is not None:
 for id in byid:
  ref[id]=a[id] if a[id]==b[id] else "disagreement"
def score(name):
 c=collections.Counter()
 for id in byid:
  if (id,name) not in votes:c["missing"]+=1;continue
  if not ref:continue
  if ref[id] in ("ambiguous","disagreement"):c[ref[id]]+=1;continue
  truth=ref[id]=="alert";yes=votes[(id,name)]
  c["TP" if truth and yes else "FP" if yes and not truth else "FN" if truth else "TN"]+=1
 tp,fp,fn,tn=(c[k] for k in ("TP","FP","FN","TN"))
 return {"valid":sum((id,name) in votes for id in byid),"positive_predictions":sum(v for (id,k),v in votes.items() if k==name),
 "old_production_disagreements":sum(votes[(id,name)]!=original[id] for id in byid if (id,name) in votes),
 "by_symbol":{s:{"valid":sum((id,name) in votes for id,c in byid.items() if c["symbol"]==s),
   "positive":sum(votes[(id,name)] for id,c in byid.items() if c["symbol"]==s and (id,name) in votes)} for s in ("BTC","ETH","GRAM","SOL")},
 "if_two_human_labels":{**{k:c[k] for k in ("TP","FP","FN","TN","ambiguous","disagreement","missing")},
   "precision":round(tp/(tp+fp),4) if tp+fp else None,
   "recall":round(tp/(tp+fn),4) if tp+fn else None} if ref else None}
out={"benchmark":"CCW29 new 200, never in older tuning 200 or previous 20",
 "dataset_sha256":src["dataset_sha256"],"expected":600,"valid":len(votes),"statuses":dict(counts),
 "openai_cost_usd_conservative":round(total_cost,6),"budget_this_run_usd":0.85,
 "human_review_A_complete":a is not None,"human_review_B_complete":b is not None,
 "authoritative_human_labels_available":bool(ref),
 "scores":{p:score(p) for p in prompts}}
(BASE/"fresh200_luna_eval_PRIVATE.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8")
print(json.dumps({k:v for k,v in out.items() if k!="scores"},indent=2))
for k,v in out["scores"].items():print("PROMPT",k,json.dumps({n:x for n,x in v.items() if n!="by_symbol"}))
