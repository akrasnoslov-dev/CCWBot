"""CCW-29 source-hash-verified v3 Luna replay comparison; never use bot votes as truth."""
from __future__ import annotations
import collections,datetime,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016/ccw29_private/fresh200_unseen"
DS="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
V3="93860c81fff1d09e1ecf3de379e1b100fcef48b84efbec15416d65386cd7d02f"
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import digest
from bot.services.ai_agent_groq import _event_significance_prompt_payload
from bot.alerting.event_identity import _json_dumps
f=json.loads((BASE/"fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf8"))
assert f["dataset_sha256"]==DS and digest(f["cases"])==DS
cases={c["id"]:c for c in f["cases"]}
old=json.loads((BASE/"openai-luna-fresh200-ledger_PRIVATE.json").read_text(encoding="utf8"))
assert old["dataset_sha256"]==DS and old["model"]=="gpt-6-luna" and len(old["attempts"])==600
prompts={"production","balanced","refined","v3"}
oldvotes=collections.defaultdict(dict)
for row in old["attempts"]:
 assert row["status"]=="valid" and row["prompt"] in prompts and row["id"] in cases
 oldvotes[row["id"]][row["prompt"]]=row["decision"]["should_alert"]
res=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops",
 "cat /home/ccwbot_ops/ccw29_fresh200_luna_v3/openai-luna-ledger.json"],capture_output=True,timeout=35)
assert res.returncode==0 and res.stdout,"Luna v3 replay is not yet available"
(BASE/"openai-luna-v3-ledger_PRIVATE.json").write_bytes(res.stdout)
ledger=json.loads(res.stdout)
assert ledger["dataset_sha256"]==DS and ledger["model"]=="gpt-6-luna" and ledger["budget_usd"]==0.35 and ledger["expected"]==200
prompt=(BASE/"candidate_refined_v3_UNTESTED.txt").read_text(encoding="utf8").rstrip("\r\n")
assert hashlib.sha256(prompt.encode()).hexdigest()==V3
allvotes={id:dict(v) for id,v in oldvotes.items()}
counter=collections.Counter();cost=0
for row in ledger["attempts"]:
 assert row["id"] in cases and row["prompt"]=="v3" and row["input_sha256"]==cases[row["id"]]["input_sha256"]
 assert digest(cases[row["id"]]["input"])==row["input_sha256"]
 content=prompt+"\nInput JSON:\n"+_json_dumps(_event_significance_prompt_payload(cases[row["id"]]["input"]))
 assert hashlib.sha256(content.encode()).hexdigest()==row["prompt_sha256"]
 cc=row.get("estimated_charged_usd",row.get("reserved_usd",0))
 assert 0<=cc<=row["reserved_usd"]+1e-7
 cost+=cc
 counter[row["status"]]+=1
 if row["status"]=="valid":
  assert row["http_status"]==200 and row["decision"]["symbol"]==cases[row["id"]]["symbol"]
  assert "v3" not in allvotes[row["id"]]
  allvotes[row["id"]]["v3"]=row["decision"]["should_alert"]
assert cost<=0.3500001
disagreement=[]
for id,c in cases.items():
 if "v3" not in allvotes[id]:continue
 if allvotes[id]["v3"]!=allvotes[id]["refined"]:
  f=c["input"];m=f["market"];p=f.get("previous_event_alert") or {}
  disagreement.append({"id":id,"coin":c["symbol"],"source_utc":c["source_utc"],
   "from_refined":allvotes[id]["refined"],"to_v3":allvotes[id]["v3"],
   "window_pct":m.get("chg_window_percent"),"last_60m_pct":m.get("chg1h_percent"),
   "last_30m_pct":m.get("chg30m_percent"),"previous_alert_age_minutes":p.get("age_minutes")})
def repeat_pairs(name):
 findings=[]
 for sym in ("BTC","ETH","GRAM","SOL"):
  subset=sorted((c for c in cases.values() if c["symbol"]==sym and name in allvotes[c["id"]]),key=lambda c:c["source_utc"])
  accepted=[c for c in subset if allvotes[c["id"]][name]]
  for prev,now in zip(accepted,accepted[1:]):
   t1=datetime.datetime.fromisoformat(prev["source_utc"].replace("Z","+00:00"))
   t2=datetime.datetime.fromisoformat(now["source_utc"].replace("Z","+00:00"))
   minutes=(t2-t1).total_seconds()/60
   if 0<=minutes<=240:
    findings.append({"symbol":sym,"first_id":prev["id"],"next_id":now["id"],"minutes_between":round(minutes,1)})
 return findings
summary={"dataset_sha256":DS,"model":"gpt-6-luna","evaluation_kind":"static historical input replay; not an updated-state sequential simulation",
 "expected":200,"status_counts":dict(counter),"unique_valid":sum("v3" in v for v in allvotes.values()),
 "cost_conservative_usd":round(cost,6),"prior_two_luna_cost_usd":0.261808,
 "cost_total_usd":round(.261808+cost,6),
 "by_prompt":{p:{"suggested_alerts":sum(v[p] for v in allvotes.values() if p in v),
 "by_symbol":{sym:sum(allvotes[c["id"]].get(p,False) for c in cases.values() if c["symbol"]==sym) for sym in ("BTC","ETH","GRAM","SOL")},
 "potential_repeated_alert_pairs_within_4h":len(repeat_pairs(p))}
 for p in prompts},
 "v3_vs_refined":{"switched":len(disagreement),"now_alert":sum(x["to_v3"] for x in disagreement),
 "now_no_alert":sum(not x["to_v3"] for x in disagreement),"disagreement_details":disagreement},
 "classification_accuracy":{"available":False,"reason":"No independent adjudicated labels for these fresh 200 cases; old production/model outputs are not reference labels."},
 "sequence_simulation":{"available":False,"reason":"Frozen inputs retain original previous-alert state; a new decision would alter downstream states.","four_hour_proximity_is_diagnostic_not_confirmed_duplicate":True}}
(BASE/"v3_luna_comparison_PRIVATE.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print(json.dumps({k:v for k,v in summary.items() if k not in ("v3_vs_refined","sequence_simulation")},
 ensure_ascii=False,indent=2))
print("V3_CHANGES",json.dumps({k:v for k,v in summary["v3_vs_refined"].items() if k!="disagreement_details"}))
