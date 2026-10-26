"""CCW-29 fresh private holdout: collect real POST-200 market cases via investigator read-only session."""
from __future__ import annotations
import hashlib,importlib.util,json,pathlib,collections,random,sys,datetime
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
SOURCE=ROOT/"reports/event-alert-review-20261016"
DEST=SOURCE/"ccw29_private/fresh_holdout"
DEST.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import digest,load_frozen,blind_packet
spec=importlib.util.spec_from_file_location("build_review_local",SOURCE/"build_review.py")
x=importlib.util.module_from_spec(spec);spec.loader.exec_module(x)
x.START="2026-10-17 00:00:00+00"
x.END="2026-10-23 00:00:00+00"
old=load_frozen(SOURCE/"v2_private_sanitized.json")
assert len(old["cases"])==200
prev={c["input_sha256"] for c in old["cases"]}
original_id=x.run_psql("SELECT current_user, current_setting('transaction_read_only'), current_setting('default_transaction_read_only')").strip()
assert original_id=="ccwbot_investigator|on|on",original_id
rows=x.source_data()
good=[];reject=collections.Counter();seen=set()
for row in rows:
 try:
  c,_=x.candidate(row)
  assert c["source_utc"] >= "2026-10-17" and c["source_utc"] < "2026-10-23"
  if c["input_sha256"] in prev:reject["overlap_200"]+=1;continue
  if c["input_sha256"] in seen:reject["duplicate_new"]+=1;continue
  seen.add(c["input_sha256"]);good.append(c)
 except Exception as e:reject[type(e).__name__+":"+str(e)[:60]]+=1
groups=collections.defaultdict(list)
for c in good:
 positive=c["sampling_cohort"]!="no_alert"
 groups[(c["symbol"],positive)].append(c)
counts={f"{s}/{'positive' if pos else 'negative'}":len(groups[(s,pos)]) for s in ("BTC","ETH","GRAM","SOL") for pos in (True,False)}
print("INPUT_COVERAGE",json.dumps({"raw":len(rows),"valid":len(good),"strata":counts,"rejections":dict(reject)},sort_keys=True),flush=True)
rng=random.Random(2026102301)
choice=[]
# First take at most two historic bot positives plus three negatives per coin.
for sym in ("BTC","ETH","GRAM","SOL"):
 for positive,count in ((True,2),(False,3)):
  pool=groups[(sym,positive)]
  if len(pool)<count:
   raise RuntimeError("not enough new independent evidence for "+sym+"/"+str(positive)+": "+str(len(pool)))
  rng.shuffle(pool)
  selected=[];dates=set();seen_sign=set()
  while len(selected)<count:
   pick=max(pool,key=lambda c:(
    int(c["source_utc"][:10] not in dates),
    int(((c["input"]["market"]["chg_window_percent"] or 0)>0) not in seen_sign),
    rng.random()))
   selected.append(pick);pool.remove(pick);dates.add(pick["source_utc"][:10]);seen_sign.add((pick["input"]["market"]["chg_window_percent"] or 0)>0)
  choice.extend(selected)
rng.shuffle(choice)
assert len(choice)==20 and len({c["input_sha256"] for c in choice})==20
data={"schema_version":1,"provenance":"real_market_sanitized","dataset_sha256":digest(choice),"cases":choice,
 "extraction":{"source":"postgresql_ccwbot_investigator_read_only","utc_start":x.START,"utc_end_exclusive":x.END,
 "frozen_seed":2026102301,"stratification":"2 observed positive / 3 observed no-alert per symbol; outcome hidden from reviewers and models",
 "status":"SEALED_UNLABELED_NEW_20","old_dataset_sha256":old["dataset_sha256"],"old_overlap_count":0}}
(DESC:=DEST/"holdout_20_source_SEALED_PRIVATE.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
packet=blind_packet(data,"significance")
for p in packet["cases"]:
 p["input_sha256"]=next(c["input_sha256"] for c in choice if c["id"]==p["id"])
(DICT:=DEST/"holdout_20_blind_packet_PRIVATE.json").write_text(json.dumps(packet,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"holdout_version":"ccw29-fresh-20261023-v1","case_count":20,"dataset_sha256":data["dataset_sha256"],
 "source_sha256":hashlib.sha256(DESC.read_bytes()).hexdigest(),
 "blind_packet_sha256":hashlib.sha256(DICT.read_bytes()).hexdigest(),
 "period":"2026-10-17T00Z..2026-10-23T00Z",
 "symbol_counts":dict(collections.Counter(c["symbol"] for c in choice)),
 "observed_production_positive_count":sum(c["observed"]["should_alert"] for c in choice),
 "original_200_overlap":0,
 "source_status":"real_market_frozen_private","label_status":"NOT_YET_BLIND_REVIEWED",
 "independence":"new timestamps and distinct canonical SHA from original 200; production labels are NOT independent reviewer truth"}
(DEST/"holdout_manifest.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
print("FROZEN",json.dumps(summary,sort_keys=True),flush=True)
