"""Freeze fresh 200 real CCWBot market cases, excluding both earlier sets; investigator SELECT-only."""
from __future__ import annotations
import collections,importlib.util,hashlib,json,pathlib,random,sys
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016"
OUT=BASE/"ccw29_private/fresh200_unseen"
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import digest,load_frozen,blind_packet
p=importlib.util.spec_from_file_location("original_approved_reader",BASE/"build_review.py")
reader=importlib.util.module_from_spec(p);p.loader.exec_module(reader)
reader.START="2026-10-17 00:00:00+00"
reader.END="2026-10-23 00:00:00+00"
assert reader.run_psql("SELECT current_user, current_setting('transaction_read_only'), current_setting('default_transaction_read_only')").strip()=="ccwbot_investigator|on|on"
orig=load_frozen(BASE/"v2_private_sanitized.json")
seen={c["input_sha256"] for c in orig["cases"]}
oldnew=json.loads((BASE/"ccw29_private/fresh_holdout/holdout_20_source_SEALED_PRIVATE.json").read_text(encoding="utf-8"))
seen|={c["input_sha256"] for c in oldnew["cases"]}
raw=reader.source_data()
valid=[];rejected=collections.Counter()
for row in raw:
 try:
  c,_=reader.candidate(row)
  assert reader.START[:10]<=c["source_utc"][:10]<reader.END[:10]
  if c["input_sha256"] in seen:
   rejected["old_200_or_holdout20"]+=1;continue
  seen.add(c["input_sha256"])
  valid.append(c)
 except Exception as err:rejected[type(err).__name__]+=1
counts=collections.Counter((c["symbol"],c["observed"]["should_alert"]) for c in valid)
print("SOURCE_AUDIT",json.dumps({"raw":len(raw),"unique_valid":len(valid),
 "strata":{f"{s}/{'old_yes' if yes else 'old_no'}":counts[(s,yes)] for s in ("BTC","ETH","GRAM","SOL") for yes in (True,False)},
 "excluded":dict(rejected)}),flush=True)
rng=random.Random(2026102307)
selection=[]
for sym in ("BTC","ETH","GRAM","SOL"):
 available=[c for c in valid if c["symbol"]==sym]
 assert len(available)>=50,"insufficient fresh data for "+sym
 # Deliberately enrich rare production-positive episodes WITHOUT using them as truth;
 # the result is NOT an unbiased production prevalence estimate.
 positive=[c for c in available if c["observed"]["should_alert"]]
 negative=[c for c in available if not c["observed"]["should_alert"]]
 n_pos=min(18,len(positive),49)
 n_neg=50-n_pos
 assert len(negative)>=n_neg
 def choose(pool,n):
  pool=list(pool);rng.shuffle(pool);done=[];days=set();signs=set();sizes=set();news=set()
  while len(done)<n:
   def score(c):
    m=c["input"]["market"];chg=m["chg_window_percent"]
    sign="+" if chg>=0 else "-";size=0 if abs(chg)<.75 else 1 if abs(chg)<2 else 2
    present=bool(c["input"].get("news"))
    return (c["source_utc"][:10] not in days,sign not in signs,size not in sizes,present not in news, rng.random())
   choice=max(pool,key=score);pool.remove(choice);done.append(choice)
   m=choice["input"]["market"];v=m["chg_window_percent"]
   days.add(choice["source_utc"][:10]);signs.add("+" if v>=0 else "-")
   sizes.add(0 if abs(v)<.75 else 1 if abs(v)<2 else 2);news.add(bool(choice["input"].get("news")))
  return done
 selection.extend(choose(positive,n_pos)+choose(negative,n_neg))
rng.shuffle(selection)
assert len(selection)==200 and len({c["id"] for c in selection})==200
assert not {c["input_sha256"] for c in selection}.intersection({c["input_sha256"] for c in orig["cases"]+oldnew["cases"]})
assert all(digest(c["input"])==c["input_sha256"] for c in selection)
h=digest(selection)
data={"schema_version":1,"dataset_sha256":h,"provenance":"real_market_sanitized",
 "extraction":{"source":"approved_postgresql_ccwbot_investigator_SELECT_only",
 "start":reader.START,"end_exclusive":reader.END,"old200_overlap":0,"prior_holdout20_overlap":0,
 "seed":2026102307,"selection":"50/symbol, up to 18 original-positive/symbol; original decision used only for stratification and NEVER as reviewer truth",
 "label_status":"NONE","population_estimate":False},
 "cases":selection}
source_path=OUT/"fresh200_source_SEALED_PRIVATE.json"
source_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
blind=blind_packet(data,"significance")
assert "cases" in blind and len(blind["cases"])==200
for c in blind["cases"]:
 assert "observed" not in c and "sampling_cohort" not in c
 c["input_sha256"]=next(x["input_sha256"] for x in selection if x["id"]==c["id"])
blind_path=OUT/"fresh200_blind_packet_PRIVATE.json"
blind_path.write_text(json.dumps(blind,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
m={"dataset_sha256":h,"total":len(selection),
 "by_symbol":dict(collections.Counter(c["symbol"] for c in selection)),
 "historical_positive_observed":sum(c["observed"]["should_alert"] for c in selection),
 "historical_positive_per_symbol":dict(collections.Counter(c["symbol"] for c in selection if c["observed"]["should_alert"])),
 "source_period":"2026-10-17 to 2026-10-22 UTC","blind_review_status":"NOT_REVIEWED",
 "authoritative_independent_human_ground_truth":False,
 "source_sha256":hashlib.sha256(source_path.read_bytes()).hexdigest(),
 "blind_packet_sha256":hashlib.sha256(blind_path.read_bytes()).hexdigest(),
 "overlap_old200":0,"overlap_holdout20":0}
(OUT/"fresh200_manifest.json").write_text(json.dumps(m,indent=2)+"\n",encoding="utf-8")
print("FROZEN200",json.dumps(m),flush=True)
