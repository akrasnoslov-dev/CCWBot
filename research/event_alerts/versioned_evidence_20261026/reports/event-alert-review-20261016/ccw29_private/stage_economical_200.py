"""CCW-45: freeze ONE compact matched Luna candidate; no source-control or production changes.
Reads prior verified price history through isolated CCW-44 jobs. Never copies decisions into model input.
One-off paid execution is handled by a separate capped worker, not this staging script.
"""
from __future__ import annotations
import collections, datetime as dt, hashlib, io, json, math, pathlib, statistics, subprocess, sys, tarfile
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016/ccw29_private"
OUT=BASE/"economical_200";OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import digest
DATASET="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
REMOTE="/home/ccwbot_ops/ccw45_economical_200"
BUDGET=0.40
CAP=2048
PROMPT="""You decide whether a crypto MARKET movement merits a NEW, useful Event Alert. Prefer to avoid both meaningful misses and repetitive/noisy alerts. Use supplied observations only. Decide market materiality, then independent event novelty; delivery is a separate backend step.

Evidence: all returns are percent (0.5 means 0.5%, not 50%); path rows [minutes_before_now, % from first observed path price]. The source's reported window return sometimes uses a 210m reference despite a nominal 180m label; rely on explicitly aged observations. Historical 30m distributions are sampled observations, not guaranteed real-time volatility or proof of rarity.

1. MATERIALITY. Would an informed holder benefit NOW from being notified of the *current* price episode relative to normal noise for this specific asset? Weigh the observed move's size, duration, pace and multi-point consistency against asset-specific 7d/30d short-interval variation and the longer observed path. A meaningful completed move may remain significant during consolidation or a partial retrace. A pronounced, verified new counter-move may matter despite a modest net window return. Do not mistake isolated wiggles, merely fast-looking single intervals, minor trend changes, an old 24h move, high historical percentile or a headline for a fresh material market event. Historical statistics inform judgment, never fixed cutoffs. If the evidence is marginal or missing, choose routine/unclear, not material by speculation. Previous alerts cannot make the underlying movement less material.

2. NOVELTY (only if material). Compare what actually happened since the last verified relevant Event Alert against the movement and direction it already described. A new sizeable extension or significant opposite-direction price episode can be new; overlap, unchanged direction without material additional progress, repackaged 24h movement or small retracement is continuation/repeated. The last notification could be a heartbeat: never assume its price was the previous Event Alert's price. A high previous alert count is contextual, not an automatic veto; an old alert is not automatic novelty. If material but no evidence of a distinct new increment, novelty=unclear or continuation and no alert.

3. DECISION. Alert only if the current price episode is convincingly material AND genuinely new. Consider the strongest evidence AGAINST both before agreeing. Do not turn market materiality into routine just to suppress repeats. News may corroborate but never independently trigger. Never forecast, infer cause or invent volume, missing prices, trajectories, or intraminute volatility. A separate system enforces the existing 4h per-recipient same-family cooldown: do not apply a global 4h refusal here.

Return ONLY JSON, exactly: symbol, materiality, novelty, should_alert, reason_code, confidence.
materiality=material|routine|unclear; novelty=new|continuation|repeated|unclear; confidence=low|medium|high.
should_alert=true only when materiality=material AND novelty=new; then reason_code=unusual_move|fast_move|reversal|trend_acceleration|market_news_alignment.
Otherwise should_alert=false and reason_code=routine_move|news_only|unclear. No prose."""
def hv(data):return hashlib.sha256(data).hexdigest()
def pct(a,b):
 if not a or b is None:return None
 return round((float(b)/float(a)-1)*100,4)
def rounded(v,n=4):
 if v is None:return None
 x=float(v)
 if not math.isfinite(x):return None
 return round(x,n)
def as_utc(s):return dt.datetime.fromisoformat(str(s).replace("Z","+00:00")).astimezone(dt.timezone.utc)
def compact(case,enriched):
 f=case["input"];m=f["market"];sym=case["symbol"]
 assert enriched["symbol"]==sym and enriched["observation_utc"]==f["timestamp_utc"]
 me=enriched["market_evidence"];hist=enriched["verified_price_history"]
 assert hist["source"]=="read_only_event_ai_analyses_market_price"
 points=sorted(hist["actual_24h_event_ai_analyses_market_price_30m_buckets"],key=lambda x:x["minutes_before_now"],reverse=True)
 assert 29<=len(points)<=48
 now=as_utc(f["timestamp_utc"])
 for point in points:
  t=as_utc(point["ts_utc"])
  assert 0 <= (now-t).total_seconds() <= 24*3600+30
  assert abs((now-t).total_seconds()/60-float(point["minutes_before_now"]))<0.05
 assert abs(points[-1]["price_usd"]/m["price"]-1)<0.0000001
 # 24h anchors at actual observed timestamps. No interpolation or invented ticks.
 targets=[1440,1080,720,480,360,240,120,60,0]
 anchors=[]
 for a in targets:
  p=min(points,key=lambda x:abs(x["minutes_before_now"]-a))
  if abs(p["minutes_before_now"]-a)<=22 and (not anchors or p["minutes_before_now"]!=anchors[-1][0]):
   anchors.append([round(p["minutes_before_now"]),pct(points[0]["price_usd"],p["price_usd"])])
 oldest=points[0]["price_usd"]; h=max(points,key=lambda x:x["price_usd"]);l=min(points,key=lambda x:x["price_usd"])
 # Last 24h observed regular contiguous 30m intervals; no returns across missing intervals.
 valid=[pct(a["price_usd"],b["price_usd"]) for a,b in zip(points,points[1:]) if 25<=(a["minutes_before_now"]-b["minutes_before_now"])<=35]
 assert all(v is not None for v in valid)
 sample_stdev=round(statistics.stdev(valid),4) if len(valid)>=10 else None
 short=sorted(m.get("snapshots") or [],key=lambda x:x["m"])
 assert len(short)>=2 and short[-1]["m"]==0
 brief_path=[[int(x["m"]*-1),pct(short[0]["p"],x["p"])] for x in short]
 brief_path.reverse()
 # Convert latest-first to oldest-first with explicitly positive minutes before now.
 brief_path=list(reversed(brief_path))
 # Validate source-window mismatch; never substitute 210m for 180m.
 actual180=next((x for x in short if x["m"]==-180),None)
 source_delta=rounded(m.get("chg_window_percent"))
 oldest_age=-int(short[0]["m"])
 actual_source_age=me.get("source_reported_move_implied_reference_age_minutes")
 if actual_source_age is not None:actual_source_age=int(actual_source_age)
 window={"source_reported_return_pct":source_delta,
         "source_reported_reference_age_m":actual_source_age,
         "nominal_window_m":m.get("analysed_window_minutes"),
         "actual_180m_return_pct":pct(actual180["p"],m["price"]) if actual180 else None,
         "path_age_and_pct_from_oldest":brief_path}
 prev=f.get("previous_event_alert") or {}
 last=f.get("last_msg") or {}
 prior_price=me.get("matched_previous_event_alert_price_usd")
 if prior_price is not None:
  assert last.get("type")=="event_alert"
  assert abs(prior_price/last["price"]-1)<0.000001
 prevsec={
 "prior_event_age_m":rounded(prev.get("age_minutes"),1),
 "prior_event_family":prev.get("semantic_family") or prev.get("canonical_event_key"),
 "prior_event_window_return_pct":rounded(prev.get("analysed_window_move")),
 "last_message_type":last.get("type"),
 "prior_event_price_usd_if_verified":rounded(prior_price,6) if prior_price is not None else None,
 "new_price_change_since_verified_prior_event_pct":pct(prior_price,m["price"]),
 "events_6h":(f.get("recent_event_counts") or {}).get("h6"),
 "events_24h":(f.get("recent_event_counts") or {}).get("h24")}
 # News is optional corroboration, not a substitute for market materiality.
 news=[str(x.get("title"))[:135] for x in f.get("news") or [] if x.get("relevance_label") in ("direct_symbol","broad_market")][:1]
 # Keep simple comparable same-asset interval history.
 distributions={}
 for d in (7,30):
  z=hist.get(f"rolling_{d}d_observed_return_distribution") or {}
  distributions[str(d)+"d"]={"median_abs_30m_pct":z.get("abs_30m_pct_median"),
    "p90_abs_30m_pct":z.get("abs_30m_pct_p90"),
    "stdev_30m_return_pct":z.get("return_30m_pct_stdev"),
    "observed_intervals":z.get("usable_intervals")}
 out={
 "symbol":sym,"time_utc":f["timestamp_utc"],
 "market":{"now_usd":rounded(m["price"],6),"last30m_pct":rounded(m.get("chg30m_percent")),
   "last60m_pct":rounded(m.get("chg1h_percent")),
   "source_24h_pct":rounded(m.get("chg24h_percent")),
   "path_window":window,
   "observed_24h":{"n_observations":len(points),"oldest_age_m":rounded(points[0]["minutes_before_now"],1),
     "change_from_oldest_pct":pct(oldest,m["price"]),
     "high_pct_from_oldest":pct(oldest,h["price_usd"]),"high_age_m":round(h["minutes_before_now"]),
     "low_pct_from_oldest":pct(oldest,l["price_usd"]),"low_age_m":round(l["minutes_before_now"]),
     "anchors_age_m_pct_from_oldest":anchors,
     "observed_contiguous_30m_stdev_pct":sample_stdev,"valid_30m_intervals":len(valid)},
   "historical_asset_30m_return_distributions":distributions,
   "historical_30d_window_abs_percentile":rounded(m.get("relative_window_percentile_30d"),1)},
 "previous":prevsec,"related_news_title_optional":news}
 assert "observed" not in out and "should_alert" not in json.dumps(out)
 return json.dumps(out,ensure_ascii=True,separators=(",",":"),sort_keys=True)
source=json.loads((BASE/"fresh200_unseen/fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf8"))
assert source["dataset_sha256"]==DATASET and digest(source["cases"])==DATASET and len(source["cases"])==200
assert len({x["id"] for x in source["cases"]})==200
assert collections.Counter(x["symbol"] for x in source["cases"])=={"BTC":50,"ETH":50,"GRAM":50,"SOL":50}
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops"]
r=subprocess.run(ssh+["cat /home/ccwbot_ops/ccw44_quality_first_200/jobs.json"],capture_output=True,timeout=60)
assert r.returncode==0 and r.stdout,"Cannot access previously verified read-only enriched history"
prior=json.loads(r.stdout);assert prior["manifest"]["verified_long_price_history"] is True
oldjobs={j["id"]:j for j in prior["jobs"]}
assert set(oldjobs)=={c["id"] for c in source["cases"]}
prompt_sha=hv(PROMPT.encode("utf8"))
jobs=[]
for case in source["cases"]:
 assert digest(case["input"])==case["input_sha256"]
 oldj=oldjobs[case["id"]]
 assert oldj["input_sha256"]==case["input_sha256"]
 oldtext=oldj["body"]["messages"][1]["content"]
 assert hv(oldtext.encode())==oldj["prompt_sha256"]
 parsed=json.loads(oldtext.split("\n\nEVIDENCE JSON:\n",1)[1])
 payload=compact(case,parsed)
 full=PROMPT+"\n\nEVIDENCE JSON:\n"+payload
 body={"messages":[{"role":"system","content":"You are a careful crypto monitoring assistant."},{"role":"user","content":full}]}
 jobs.append({"id":case["id"],"input_sha256":case["input_sha256"],"symbol":case["symbol"],"prompt":"economical",
  "prompt_sha256":hv(full.encode("utf8")),
  "request_sha256":hv(json.dumps(body,separators=(",",":"),sort_keys=True).encode("utf8")),
  "body":body})
assert len(jobs)==200
assert len({(j["id"],j["prompt"]) for j in jobs})==200
sizes=[len(j["body"]["messages"][1]["content"].encode("utf8")) for j in jobs]
# The worker reserves worst-case UTF-8 bytes as prompt tokens, plus a safety margin.
reserve=sum((s+len("You are a careful crypto monitoring assistant.")+1024)*0.10/1e6+CAP*0.50/1e6 for s in sizes)
assert reserve<=BUDGET, f"Strict up-front worst-case reserve exceeds $0.40: {reserve}"
manifest={"task":"CCW-45","dataset_sha256":DATASET,"prompt_instruction_sha256":{"economical":prompt_sha},
 "expected":200,"labels_in_model_input":False,"reused_development_set":True,
 "origin":"source snapshots + CCW-44 independently stored read-only event_ai_analyses price history",
 "model":"gpt-6-luna","api":"/v1/chat/completions","response_format":"json_object",
 "max_completion_tokens":CAP,"one_off_budget_usd":BUDGET,"candidate_count":1,
 "retry_policy":"never retry submitted paid request","production_modified":False}
runner=(BASE/"fresh200_unseen/fresh200_luna_runner_PRIVATE.py").read_text(encoding="utf8")
for a,b in (("/home/ccwbot_ops/ccw29_fresh200_luna",REMOTE),
 ("BUDGET=0.85",f"BUDGET={BUDGET}"),("MAX_COMPLETION_TOKENS=4096",f"MAX_COMPLETION_TOKENS={CAP}"),
 ("==600","==200"),("expected\":600","expected\":200"),
 ("CCW-29","CCW-45"),("CCW29","CCW45"),
 ("\\nInput JSON:\\n","\\nEVIDENCE JSON:\\n"),
 ("for retry in range(6):","for retry in range(1):"),
 ("if status==429 and retry<5:","if False and status==429 and retry<5:")):
 assert a in runner,(a,"missing runner template token")
 runner=runner.replace(a,b)
# No hidden second Luna pass, no retry even after 429, no provider calls per recipient.
assert 'len(originals)==200' in runner and 'range(1)' in runner
assert 'KEY_PATH.unlink(missing_ok=True)' in runner
runner=runner.replace('assert len(jobs)==200 and all(j["reserved_usd"]<0.01 for j in jobs)',
 'assert len(jobs)==200 and all(j["reserved_usd"]<0.01 for j in jobs)\n assert sum(j["reserved_usd"] for j in jobs)<=BUDGET,"200 calls cannot fit hard budget; zero calls allowed"')
compile(runner,"economical_luna_runner.py","exec")
assets={"manifest.json":json.dumps(manifest,separators=(",",":")).encode(),
 "jobs.json":json.dumps({"manifest":manifest,"jobs":jobs},separators=(",",":")).encode(),
 "candidate_economical.txt":(PROMPT+"\n").encode(),
 "openai_luna_200_runner.py":runner.encode()}
(OUT/"economical_prompt.txt").write_text(PROMPT+"\n",encoding="utf8")
(OUT/"economical_manifest.json").write_text(json.dumps({**manifest,"request_upper_bound_usd":round(reserve,8),"request_bytes_average":round(statistics.mean(sizes),1)},indent=2)+"\n",encoding="utf8")
(OUT/"economical_jobs_PRIVATE.json").write_text(json.dumps({"manifest":manifest,"jobs":jobs},separators=(",",":")),encoding="utf8")
(OUT/"economical_luna_runner_PRIVATE.py").write_text(runner,encoding="utf8")
# Deliberately no long-lived remote watcher; this does not launch any paid or asynchronous work.
pre=subprocess.run(ssh+[f'test "$(id -un)" = ccwbot_ops && test ! -e {REMOTE} && echo SAFE'],capture_output=True,timeout=25)
assert pre.returncode==0 and b"SAFE" in pre.stdout,repr(pre.stderr[:200])
stream=io.BytesIO()
with tarfile.open(fileobj=stream,mode="w") as tar:
 for name,body in assets.items():
  item=tarfile.TarInfo(name);item.size=len(body);item.mode=0o600;tar.addfile(item,io.BytesIO(body))
stage=subprocess.run(ssh+[f"set -eu; umask 077; mkdir -m 700 {REMOTE}; tar -xf - -C {REMOTE}; python3 -m py_compile {REMOTE}/openai_luna_200_runner.py; test ! -e {REMOTE}/openai-luna-ledger.json; echo STAGED"],input=stream.getvalue(),capture_output=True,timeout=70)
assert stage.returncode==0 and b"STAGED" in stage.stdout,(stage.returncode,stage.stderr[:250])
print(json.dumps({"status":"STAGED_NO_PAID_CALLS","count":len(jobs),"symbol_counts":dict(collections.Counter(j["symbol"] for j in jobs)),
 "dataset_sha256":DATASET,"prompt_sha256":prompt_sha,
 "request_bytes_min_avg_max":[min(sizes),round(statistics.mean(sizes)),max(sizes)],
 "precomputed_all_calls_max_usd":round(reserve,8),"spend_cap_usd":BUDGET,"completion_tokens_cap":CAP,
 "remote_dir":REMOTE,"no_key_access_or_copy":True,"production_modified":False},ensure_ascii=True))
