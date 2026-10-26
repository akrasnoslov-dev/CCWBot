"""CCW-45 offline matched scorer. Does not generate, rerun or request any model responses.
GPT-6 post-hoc review is diagnostics ONLY; independence/production release not established.
"""
from __future__ import annotations
import collections, datetime, hashlib, json, pathlib, subprocess, sys
ROOT=pathlib.Path(r"D:\Projects\CCWBot");sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import digest
BASE=ROOT/"reports/event-alert-review-20261016/ccw29_private"
OUT=BASE/"economical_200";F=BASE/"fresh200_unseen"
DS="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
manifest=json.loads((OUT/"economical_manifest.json").read_text(encoding="utf8"))
src=json.loads((F/"fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf8"))
jobdoc=json.loads((OUT/"economical_jobs_PRIVATE.json").read_text(encoding="utf8"))
assert DS==manifest["dataset_sha256"]==src["dataset_sha256"]==jobdoc["manifest"]["dataset_sha256"]
assert digest(src["cases"])==DS and len(src["cases"])==200
byid={c["id"]:c for c in src["cases"]}
jobs={j["id"]:j for j in jobdoc["jobs"]}
assert len(byid)==len(jobs)==200 and set(byid)==set(jobs)
prompt=(OUT/"economical_prompt.txt").read_text(encoding="utf8").rstrip("\r\n")
assert hashlib.sha256(prompt.encode()).hexdigest()==manifest["prompt_instruction_sha256"]["economical"]
for ident,j in jobs.items():
 c=byid[ident]
 assert digest(c["input"])==c["input_sha256"]==j["input_sha256"]
 txt=j["body"]["messages"][1]["content"]
 assert txt.startswith(prompt+"\n\nEVIDENCE JSON:\n")
 assert hashlib.sha256(txt.encode()).hexdigest()==j["prompt_sha256"]
 data=json.loads(txt.split("\n\nEVIDENCE JSON:\n",1)[1])
 assert data["symbol"]==c["symbol"] and "should_alert" not in data and "observed" not in data
 assert hashlib.sha256(json.dumps(j["body"],sort_keys=True,separators=(",",":")).encode()).hexdigest()==j["request_sha256"]
remote=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops",
 "cat /home/ccwbot_ops/ccw45_economical_200/openai-luna-ledger.json"],capture_output=True,timeout=50)
if remote.returncode!=0 or not remote.stdout:raise SystemExit("NO_PAID_LEDGER: 0 results; blocked until safe temporary test credential delegation")
ledger=json.loads(remote.stdout)
assert ledger["task"]=="CCW-45" and ledger["dataset_sha256"]==DS
assert ledger["model"]=="gpt-6-luna" and ledger["expected"]==200
assert ledger["budget_usd"]==manifest["one_off_budget_usd"]==0.40
assert ledger["max_completion_tokens"]==2048
(OUT/"economical_luna_ledger_PRIVATE.json").write_bytes(remote.stdout)
attempts=ledger["attempts"];assert len(attempts)<=200
assert len({a["id"] for a in attempts})==len(attempts)
valid={};states=collections.Counter();cost=0;tin=tout=0;missing_usage=0
persym={x:{"cases":50,"valid":0,"positive":0,"input_tokens":0,"output_tokens":0} for x in ("BTC","ETH","GRAM","SOL")}
for a in attempts:
 j=jobs[a["id"]];sym=byid[a["id"]]["symbol"]
 assert (a["input_sha256"],a["prompt_sha256"],a["request_sha256"],a["symbol"],a["prompt"])==(j["input_sha256"],j["prompt_sha256"],j["request_sha256"],sym,"economical")
 states[a["status"]]+=1
 charged=a.get("estimated_charged_usd",a["reserved_usd"])
 assert 0<=charged<=a["reserved_usd"]+1e-7;cost+=charged
 if a["status"]!="valid":continue
 d=a["decision"]
 assert a["http_status"]==200 and type(d["should_alert"])==bool and d["symbol"]==sym
 assert set(d)=={"symbol","materiality","novelty","should_alert","reason_code","confidence"}
 assert d["should_alert"]==(d["materiality"]=="material" and d["novelty"]=="new"),"CONTRADICTORY_MODEL_DECISION"
 valid[a["id"]]=bool(d["should_alert"])
 persym[sym]["valid"]+=1;persym[sym]["positive"]+=int(d["should_alert"])
 if type(a.get("prompt_tokens"))==int and type(a.get("completion_tokens"))==int:
  inn=a["prompt_tokens"];out=a["completion_tokens"]
  tin+=inn;tout+=out
  persym[sym]["input_tokens"]+=inn;persym[sym]["output_tokens"]+=out
 else:missing_usage+=1
assert cost<=0.4000001
prior={}
for name,p in (("production",F/"openai-luna-fresh200-ledger_PRIVATE.json"),
 ("balanced",F/"openai-luna-fresh200-ledger_PRIVATE.json"),
 ("refined_v2",F/"openai-luna-fresh200-ledger_PRIVATE.json"),
 ("refined_v3",F/"openai-luna-v3-ledger_PRIVATE.json"),
 ("quality_first",BASE/"quality_first_200/quality_first_luna_ledger_PRIVATE.json")):
 name_in_ledger={"refined_v2":"refined","refined_v3":"v3"}.get(name,name)
 entries=json.loads(p.read_text(encoding="utf8"))["attempts"]
 v={r["id"]:r["decision"]["should_alert"] for r in entries if r["prompt"]==name_in_ledger and r["status"]=="valid"}
 assert set(v)==set(byid),(name,len(v))
 prior[name]=v
pair={}
for name,old in prior.items():
 pair[name]={"old_alerts":sum(old.values()),
 "new_alerts":sum(valid.values()),"same_decisions":sum(old[i]==valid[i] for i in valid),
 "new_positive":sum(valid[i] and not old[i] for i in valid),
 "withdrawn_positive":sum(not valid[i] and old[i] for i in valid),
 "both_positive":sum(valid[i] and old[i] for i in valid)}
reference=json.loads((F/"gpt6_direct_review_200_PROVISIONAL_PRIVATE.json").read_text(encoding="utf8"))
assert reference["dataset_sha256"]==DS
labels={x["id"]:x["warrant"] for x in reference["case_labels"]}
assert set(labels)==set(byid)
def exploratory(v):
 c=collections.Counter()
 for ident,positive in v.items():
  mark=labels[ident]
  if mark=="ambiguous":c["ambiguous_pred_alert" if positive else "ambiguous_pred_no_alert"]+=1
  elif mark=="alert":c["TP" if positive else "FN"]+=1
  elif mark=="no_alert":c["FP" if positive else "TN"]+=1
  else:raise AssertionError(mark)
 tp,fp,fn=(c[k] for k in ("TP","FP","FN"))
 return {"counts":dict(c),
  "precision_against_nonindependent_GPT6":round(tp/(tp+fp),4) if tp+fp else None,
  "recall_against_nonindependent_GPT6":round(tp/(tp+fn),4) if tp+fn else None}
def when(ident):
 return datetime.datetime.fromisoformat(byid[ident]["input"]["timestamp_utc"].replace("Z","+00:00"))
def direction(ident):
 z=json.loads(jobs[ident]["body"]["messages"][1]["content"].split("\n\nEVIDENCE JSON:\n",1)[1])["market"]["path_window"]
 n=z["actual_180m_return_pct"]
 return 1 if n is not None and n>0 else -1 if n is not None and n<0 else 0
# Potential repeat pressure only: this does NOT simulate actual per-recipient cooldown.
positive=sorted([ident for ident,p in valid.items() if p],key=when)
nearby=[]
for index,ident in enumerate(positive):
 for old in positive[:index]:
  gap=(when(ident)-when(old)).total_seconds()/60
  if byid[ident]["symbol"]==byid[old]["symbol"] and 0<=gap<240 and direction(ident)==direction(old)!=0:
   nearby.append({"older":old,"newer":ident,"gap_minutes":round(gap,1)})
result={
 "task":"CCW-45","dataset_sha256":DS,"prompt_sha256":manifest["prompt_instruction_sha256"]["economical"],
 "state_counts":dict(states),"valid":len(valid),"expected":200,"complete":len(valid)==200 and len(attempts)==200,
 "proposed_alerts":sum(valid.values()),"per_symbol":persym,
 "input_tokens":tin,"completion_tokens_including_reasoning":tout,
 "avg_input_tokens":round(tin/len(valid),1) if valid and missing_usage==0 else None,
 "avg_completion_tokens_including_reasoning":round(tout/len(valid),1) if valid and missing_usage==0 else None,
 "missing_usage":missing_usage,"cost_upper_usd":round(cost,7),"spend_cap_usd":0.40,
 "paired_matching":pair,
 "exploratory_GPT6_posthoc_reference_NOT_independent":exploratory(valid),
 "independent_human_precision":None,"independent_human_recall":None,
 "possible_same_direction_four_hour_pairs_NOT_confirmed_duplicates":len(nearby),
 "possible_repeat_pairs_PRIVATE":nearby,
 "month_estimate_at_historical_200_terminal_Event_Analyses_per_25h_UNVALIDATED":round((cost/len(attempts))*192*30,3) if len(attempts)==200 else None,
 "monthly_estimate_excludes_render_retries_provider_price_changes":True,
 "note":"Historical 200 Event Analyses in ~25h are not verified current production workload. No independently labelled humans; static replay cannot assert delivery-level cooldown or final-message quality. No production deployed."
 }
(OUT/"economical_results_PRIVATE.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print(json.dumps({k:v for k,v in result.items() if k not in ("possible_repeat_pairs_PRIVATE",)},ensure_ascii=False,indent=2))
