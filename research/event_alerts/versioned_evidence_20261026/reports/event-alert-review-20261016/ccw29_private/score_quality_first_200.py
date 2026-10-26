"""CCW-44 final Quality-first scorer; no API calls, explicit provisional human-label caveat."""
import collections,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016/ccw29_private"
F=BASE/"fresh200_unseen";OUT=BASE/"quality_first_200";OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import digest
DS="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
manifest=json.loads((OUT/"quality_first_manifest.json").read_text(encoding="utf8"))
src=json.loads((F/"fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf8"))
assert manifest["dataset_sha256"]==DS==src["dataset_sha256"] and digest(src["cases"])==DS
byid={c["id"]:c for c in src["cases"]};assert len(byid)==200
s=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops","cat /home/ccwbot_ops/ccw44_quality_first_200/jobs.json"],capture_output=True,timeout=40)
assert s.returncode==0 and s.stdout,"JOBS_NOT_AVAILABLE"
jobdoc=json.loads(s.stdout);jobs={j["id"]:j for j in jobdoc["jobs"]}
assert jobdoc["manifest"]["dataset_sha256"]==DS and len(jobs)==200
txt=(OUT/"quality_first_prompt.txt").read_text(encoding="utf8").rstrip("\r\n")
assert hashlib.sha256(txt.encode()).hexdigest()==manifest["prompt_instruction_sha256"]["quality_first"]
for id,j in jobs.items():
 assert id in byid and j["input_sha256"]==byid[id]["input_sha256"]
 assert digest(byid[id]["input"])==j["input_sha256"]
 full=j["body"]["messages"][1]["content"]
 assert full.startswith(txt+"\n\nEVIDENCE JSON:\n")
 assert hashlib.sha256(full.encode()).hexdigest()==j["prompt_sha256"]
 assert "observed" not in json.loads(full.split("\n\nEVIDENCE JSON:\n",1)[1])
 assert hashlib.sha256(json.dumps(j["body"],sort_keys=True,separators=(",",":")).encode()).hexdigest()==j["request_sha256"]
raw=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops","cat /home/ccwbot_ops/ccw44_quality_first_200/openai-luna-ledger.json"],capture_output=True,timeout=40)
assert raw.returncode==0 and raw.stdout,"NO_LUNA_RESULTS_YET"
(OUT/"quality_first_luna_ledger_PRIVATE.json").write_bytes(raw.stdout)
led=json.loads(raw.stdout)
assert led["model"]=="gpt-6-luna" and led["dataset_sha256"]==DS and led["budget_usd"]==0.5
assert led["expected"]==200 and led["max_completion_tokens"]==4096
states=collections.Counter();by_sym=collections.Counter();per_sym={}
for s in ("BTC","ETH","GRAM","SOL"):per_sym[s]={"cases":0,"valid":0,"positive":0,"input":0,"completion":0}
valid={};spent=0;tin=0;tout=0;usage_missing=0
for x in led["attempts"]:
 id=x["id"];j=jobs[id];sym=byid[id]["symbol"]
 assert x["input_sha256"]==j["input_sha256"] and x["prompt_sha256"]==j["prompt_sha256"]
 assert x["request_sha256"]==j["request_sha256"] and x["prompt"]=="quality_first"
 states[x["status"]]+=1
 cost=x.get("estimated_charged_usd",x.get("reserved_usd",0))
 assert 0<=cost<=x["reserved_usd"]+1e-7;spent+=cost
 if x["status"]!="valid":continue
 assert x["http_status"]==200 and id not in valid and x["decision"]["symbol"]==sym
 assert x["decision"]["should_alert"] is True or x["decision"]["should_alert"] is False
 valid[id]=x["decision"];per_sym[sym]["valid"]+=1
 if x["decision"]["should_alert"]:per_sym[sym]["positive"]+=1
 inp,out=x.get("prompt_tokens"),x.get("completion_tokens")
 if type(inp)==int and type(out)==int:
  tin+=inp;tout+=out;per_sym[sym]["input"]+=inp;per_sym[sym]["completion"]+=out
 else:usage_missing+=1
assert spent<=0.5000001
for c in byid.values():per_sym[c["symbol"]]["cases"]+=1
# Paired comparisons are exact matched snapshots but no independent truth.
prior={}
for name,path in (("production",F/"openai-luna-fresh200-ledger_PRIVATE.json"),
 ("balanced",F/"openai-luna-fresh200-ledger_PRIVATE.json"),
 ("refined",F/"openai-luna-fresh200-ledger_PRIVATE.json"),
 ("v3",F/"openai-luna-v3-ledger_PRIVATE.json")):
 srcledger=json.loads(path.read_text(encoding="utf8"))
 tmp={r["id"]:r["decision"]["should_alert"] for r in srcledger["attempts"] if r["prompt"]==name and r["status"]=="valid"}
 assert set(tmp)==set(byid)
 prior[name]=tmp
differences={k:{"changed":sum(v[id]!=valid[id]["should_alert"] for id in valid),
 "newly_alerts":sum(not v[id] and valid[id]["should_alert"] for id in valid),
 "suppressed_alerts":sum(v[id] and not valid[id]["should_alert"] for id in valid)} for k,v in prior.items()}
provisional=json.loads((F/"gpt6_direct_review_200_PROVISIONAL_PRIVATE.json").read_text(encoding="utf8"))
assert provisional["dataset_sha256"]==DS
labels={r["id"]:r["warrant"] for r in provisional["case_labels"]}
assert set(labels)==set(byid)
def metric(v):
 c=collections.Counter()
 for id,dec in v.items():
  lab=labels[id]
  if lab=="ambiguous":c["ambiguous"]+=1;continue
  if lab not in ("alert","no_alert"):raise ValueError("unknown label")
  yes=dec if type(dec)==bool else dec["should_alert"]
  c["TP" if lab=="alert" and yes else "FP" if lab=="no_alert" and yes else "FN" if lab=="alert" else "TN"]+=1
 tp,fp,fn,tn=(c[k] for k in ("TP","FP","FN","TN"))
 return {"TP":tp,"FP":fp,"FN":fn,"TN":tn,"ambiguous":c["ambiguous"],
 "precision_provisional":round(tp/(tp+fp),4) if tp+fp else None,
 "recall_provisional":round(tp/(tp+fn),4) if tp+fn else None,
 "accuracy_provisional":round((tp+tn)/(tp+fp+fn+tn),4) if tp+fp+fn+tn else None}
results={"task":"CCW-44","dataset_sha256":DS,
 "status":dict(states),"complete":len(valid)==200,"valid":len(valid),"required":200,
 "input_tokens":tin,"completion_tokens_including_reasoning":tout,
 "avg_input_tokens":round(tin/len(valid),2) if valid else None,
 "avg_completion_tokens_including_reasoning":round(tout/len(valid),2) if valid else None,
 "missing_usage":usage_missing,"cost_upper_usd":round(spent,6),"cap_usd":0.5,
 "quality_first_positive":sum(d["should_alert"] for d in valid.values()),"per_symbol":per_sym,
 "matched_changes":differences,
 "quality_reference":"AI POSTHOC SELF-REVIEW ONLY, not human, not independent",
 "provisional_diagnostic_scores":{"quality_first":metric(valid),**{k:metric(v) for k,v in prior.items()}},
 "human_verified_quality_percent":None,
 "dataset_is_fresh_holdout":False,
 "source_warning":"new enriched input constructed from previously examined 200 source rows; no new 24-hour time series or realized volatility was invented"}
(OUT/"quality_first_results_PRIVATE.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print(json.dumps(results,ensure_ascii=False,indent=2))
