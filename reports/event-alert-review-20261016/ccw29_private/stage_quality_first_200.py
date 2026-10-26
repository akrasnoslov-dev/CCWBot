"""CCW-44: isolate one quality-first Luna replay on exactly 200 existing frozen real events.
No production writes; no external data fetches beyond uploading isolated private jobs.
The source is a previously examined development set, NOT a blind/untouched holdout.
"""
from __future__ import annotations
import collections,datetime,hashlib,io,json,math,pathlib,subprocess,sys,tarfile
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016/ccw29_private/fresh200_unseen"
OUT=ROOT/"reports/event-alert-review-20261016/ccw29_private/quality_first_200"
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import digest
from bot.alerting.event_identity import _json_dumps
DATASET="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
REMOTE="/home/ccwbot_ops/ccw44_quality_first_200"
PROMPT="""ROLE
You are the market-event significance reviewer for a low-noise crypto monitoring service. Your job is to detect IMPORTANT observable price movements that users have not already been told about. Treat missed genuinely important movement and repeated low-value notices as distinct failures. Use only the supplied factual evidence. This is a research replay: do not guess future prices or recommend a trade.

DATA FORMAT
Evidence JSON contains symbol, time, source observed market metrics, chronological explicitly timestamp-offset price samples, derived returns between the actual observed points, exact-window return where a matching reference sample exists, and previous delivered message / previous market event context where available. All percentages are percentage points, e.g. 0.7 means +0.7%, not 70%. A negative time offset means minutes before current sample. Source nominal analysed_window_minutes may differ from the oldest usable snapshot; trust actual observation offsets for time statements and flag a discrepancy rather than silently attributing an older return to a shorter window. Historical percentiles measure relative movement but are not statistical proof of rarity. News is supporting context only and cannot trigger on its own.

MARKET MATERIALITY — FIRST
Judge the current observable episode without allowing event-history or frequency of earlier notifications to redefine whether the price episode itself is significant.
Examine the actual path: net observed displacement, intra-path swing, velocity over intervals, genuine directional persistence or acceleration, a pronounced reversal, and the available same-asset historical context. A completed substantial move can still be material if the last 30 minutes consolidate or partially retrace. A sharp recent counter-move may be important even where a three-hour net return is small. Conversely, a small or purely historical return, a news title, a 24-hour move, a high percentile or a mere sign flip is never enough alone.
Judge proportionality for this individual asset; do not use a fixed numerical percentage cutoff. Do not fabricate intraminute movements, volume, risk, real-time volatility, or higher-frequency prices that are not in the evidence. If no compelling current material event is established, set materiality=routine or unclear, regardless of earlier notifications.

EVENT NOVELTY — SECOND AND INDEPENDENT
Once materiality is established, ask exactly which part of this movement happened AFTER the last relevant previously described price event. Use the supplied prior event's time and actual price whenever verified, together with the current trajectory, prior announced direction and historic covered move.
Classify NEW for a distinct material episode, genuinely new substantial trend extension, or material new reversal. Classify repeated/continuation when the motion materially overlaps what was already described with no significant new increment. Do not automatically veto a substantial new move merely because there was a same-direction alert recently or event counts were high. Do not automatically grant novelty because a previous alert is old or its family differs. A rise then reversal deserves examination of the actual counter-move rather than just three-hour net.
The existing four-hour recipient-level same-family cooldown is applied after model significance by a separate system; NEVER implement that as a blanket model refusal. Do not confuse change since ANY last message with change since the most recent Event Alert when their identities differ.

QUALITY CHECK
Before an alert, consider evidence for and against significance, distinguish actual observed movement from inferred explanation, and check whether the increment since previously communicated movement is supported. If the real price path is meaningful but novelty is uncertain, retain materiality=material, novelty=unclear, and should_alert=false. Do not turn a significant event into a routine one solely due to prior alerts. Do not invent evidence to force a yes or no.
Missing volume, missing interval data or missing volatility must remain missing, not converted to reassuring or alarming interpretations.

OUTPUT
Return only valid JSON with exactly six keys:
symbol, materiality, novelty, should_alert, reason_code, confidence.
materiality: material|routine|unclear.
novelty: new|continuation|repeated|unclear.
confidence: low|medium|high.
should_alert true only if materiality=material and novelty=new; reason_code on true: unusual_move|fast_move|reversal|trend_acceleration|market_news_alignment.
should_alert false otherwise; reason_code on false: routine_move|news_only|unclear.
No hard numeric significance thresholds. News alone means false. No extraneous keys or prose outside JSON."""
def hv(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def pct(a,b):
 if a is None or b is None or not a:return None
 return round((float(b)/float(a)-1)*100,5)
def shortnum(v):
 try:
  if v is None or not math.isfinite(float(v)):return None
  return round(float(v),7)
 except (TypeError,ValueError):return None
def build(case):
 f=case["input"];m=f["market"]
 snap=m.get("snapshots") or []
 series=sorted([{"minutes_from_now":int(s["m"]),"usd":shortnum(s["p"])} for s in snap if s.get("p") is not None and s.get("m") is not None],key=lambda t:t["minutes_from_now"])
 assert len(series)>=2 and series[-1]["minutes_from_now"]==0
 prices={s["minutes_from_now"]:s["usd"] for s in series}
 now=prices[0];segments=[]
 for a,b in zip(series,series[1:]):
  dt=b["minutes_from_now"]-a["minutes_from_now"]
  assert dt>0
  segments.append({"start_m":a["minutes_from_now"],"end_m":b["minutes_from_now"],"minutes":dt,"pct":pct(a["usd"],b["usd"])})
 source_cw=shortnum(m.get("chg_window_percent"))
 source_implied_reference=(now/(1+source_cw/100) if source_cw is not None and source_cw > -99.9 else None)
 match=None
 if source_implied_reference is not None:
  match=min(series,key=lambda x:abs(x["usd"]-source_implied_reference))
  if abs(pct(source_implied_reference,match["usd"]) or 0)>0.015:match=None
 matched_180=prices.get(-180)
 ref_minutes=-int(m.get("analysed_window_minutes") or 180)
 requested_exact=prices.get(ref_minutes)
 last=f.get("last_msg") if isinstance(f.get("last_msg"),dict) else {}
 prev=f.get("previous_event_alert") if isinstance(f.get("previous_event_alert"),dict) else {}
 counts=f.get("recent_event_counts") if isinstance(f.get("recent_event_counts"),dict) else {}
 age=prev.get("age_minutes")
 # A prior Event Alert price is verified only if last_msg is itself that same event.
 prior_price=shortnum(last.get("price")) if last.get("type")=="event_alert" else None
 if age is not None and last.get("type")=="event_alert":
  try:
   a=datetime.datetime.fromisoformat(str(last["time"]).replace("Z","+00:00"))
   b=datetime.datetime.fromisoformat(str(f["timestamp_utc"]).replace("Z","+00:00"))
   if abs((b-a).total_seconds()/60-float(age))>3:prior_price=None
  except (TypeError,ValueError,KeyError):prior_price=None
 upto=series
 max_loss=0.;max_gain=0.;peak=upto[0]["usd"];trough=upto[0]["usd"]
 for s in upto:
  x=s["usd"]
  max_loss=min(max_loss,pct(peak,x) or 0)
  max_gain=max(max_gain,pct(trough,x) or 0)
  peak=max(peak,x);trough=min(trough,x)
 news=[]
 for n in (f.get("news") or [])[:3]:
  if isinstance(n,dict):
   news.append({"headline":str(n.get("title") or "")[:220],"published_utc":n.get("time"),"symbol_relevance":n.get("relevance_label"),"materiality_tag_not_price_proof":n.get("material")})
 extra={
  "symbol":case["symbol"],"observation_utc":f.get("timestamp_utc"),
  "market_evidence":{
   "current_price_usd":shortnum(m.get("price")),
   "chronological_observed_prices":series,
   "observed_segment_returns_pct":segments,
   "earliest_observation_age_minutes":-series[0]["minutes_from_now"],
   "earliest_to_current_pct":pct(series[0]["usd"],now),
   "observed_max_from_peak_drawdown_pct":round(max_loss,5),
   "observed_max_from_trough_rebound_pct":round(max_gain,5),
   "actual_analysed_window_reference_minutes":ref_minutes,
   "calculated_exact_analysed_window_pct_when_point_exists":pct(requested_exact,now),
   "source_reported_analysed_window_pct":source_cw,
   "source_reported_move_implied_reference_age_minutes":-match["minutes_from_now"] if match else None,
   "source_last_30m_pct":shortnum(m.get("chg30m_percent")),
   "source_last_60m_pct":shortnum(m.get("chg1h_percent")),
   "source_last_24h_pct":shortnum(m.get("chg24h_percent")),
   "source_since_last_message_pct":shortnum(m.get("chg_since_msg_percent")),
   "historical_30d_abs_window_percentile":shortnum(m.get("relative_window_percentile_30d")),
   "historical_30d_abs_24h_percentile":shortnum(m.get("relative_24h_percentile_30d")),
   "current_5min_or_15min_data":"not_observed_in_source",
   "live_realized_volatility":"not_observed_in_source",
   "volume_and_liquidity":"not_observed_in_source"
  },
  "event_history":{
   "last_delivered_message_kind":last.get("type"),
   "last_delivered_message_time_utc":last.get("time"),
   "last_delivered_message_price_usd":shortnum(last.get("price")),
   "previous_event_alert_age_minutes":age,
   "previous_event_alert_title":prev.get("title"),
   "previous_event_alert_covered_move_pct":shortnum(prev.get("analysed_window_move")),
   "previous_event_alert_family":prev.get("semantic_family") or prev.get("canonical_event_key"),
   "matched_previous_event_alert_price_usd":prior_price,
   "incremental_change_from_matched_previous_event_alert_pct":pct(prior_price,now) if prior_price else None,
   "alertworthy_events_last_6h":counts.get("h6"),
   "alertworthy_events_last_24h":counts.get("h24"),
   "detailed_full_alert_history":"not_provided"
  },
  "related_news_optional_not_market_evidence":news
 }
 # Never feed the bot's original verdict or earlier model/owner output.
 payload=_json_dumps(extra)
 assert "observed" not in extra and case["observed"]["should_alert"] in (True,False)
 assert json.loads(payload)["symbol"]==case["symbol"]
 return payload
src=json.loads((BASE/"fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf-8"))
assert src["dataset_sha256"]==DATASET and len(src["cases"])==200 and digest(src["cases"])==DATASET
assert len({x["id"] for x in src["cases"]})==200 and collections.Counter(x["symbol"] for x in src["cases"])=={"BTC":50,"ETH":50,"GRAM":50,"SOL":50}
prompt_sha=hv(PROMPT.encode("utf-8"))
jobs=[]
for case in src["cases"]:
 assert digest(case["input"])==case["input_sha256"]
 payload=build(case)
 full=PROMPT+"\n\nEVIDENCE JSON:\n"+payload
 body={"messages":[{"role":"system","content":"You are a careful crypto monitoring assistant."},{"role":"user","content":full}]}
 jobs.append({"id":case["id"],"input_sha256":case["input_sha256"],"symbol":case["symbol"],"prompt":"quality_first",
  "prompt_sha256":hv(full.encode("utf-8")),
  "request_sha256":hv(json.dumps(body,separators=(",",":"),sort_keys=True).encode("utf-8")),
  "body":body})
assert len(jobs)==200 and len({(x["id"],x["prompt"]) for x in jobs})==200
manifest={"task":"CCW-44","dataset_sha256":DATASET,"prompt_instruction_sha256":{"quality_first":prompt_sha},
 "expected":200,"labels_in_model_input":False,"privacy":"private real market source","sample_status":"reused developmental set, not independently blind",
 "token_policy":"quality-first; no filler for absent evidence"}
runner=(BASE/"fresh200_luna_runner_PRIVATE.py").read_text(encoding="utf8")
for a,b in (("/home/ccwbot_ops/ccw29_fresh200_luna",REMOTE),
             ("BUDGET=0.85","BUDGET=0.50"),
             ("DATASET=\"ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d\"","DATASET=\""+DATASET+"\""),
             ("==600","==200"),('"expected":600','"expected":200'),('"task":"CCW-29"','"task":"CCW-44"')):
 if a not in runner and a!="DATASET=\""+DATASET+"\"":raise AssertionError("Expected old runner token absent")
 runner=runner.replace(a,b)
assert 'len({(x["id"],x["prompt"]) for x in originals})==200' in runner
assert "MAX_COMPLETION_TOKENS=4096" in runner and 'KEY_PATH.unlink(missing_ok=True)' in runner
compile(runner,"quality_first_worker.py","exec")
asset={"manifest.json":json.dumps(manifest,separators=(",",":")).encode("utf8"),
       "jobs.json":json.dumps({"manifest":manifest,"jobs":jobs},ensure_ascii=True,separators=(",",":")).encode("utf8"),
       "candidate_quality_first.txt":(PROMPT+"\n").encode("utf8"),
       "openai_luna_200_runner.py":runner.encode("utf8")}
waiter="""#!/usr/bin/env bash
set -euo pipefail
cd /home/ccwbot_ops/ccw44_quality_first_200
for i in {1..2880}; do
 if [[ -s openai_test_key.private ]] && [[ ! -e openai-luna-ledger.json ]]; then
  echo QUALITY_FIRST_KEY_READY
  exec python3 -u openai_luna_200_runner.py
 fi
 sleep 30
done
echo NO_TEST_KEY_IN_24H
"""
asset["wait_and_run.sh"]=waiter.encode("utf8")
(OUT/"quality_first_prompt.txt").write_text(PROMPT+"\n",encoding="utf8")
(OUT/"quality_first_manifest.json").write_text(json.dumps({**manifest,"token_usage":"measure at provider, do not assume target","one_off_budget_usd":0.50,"source_period":"17-22 Oct 2026"},indent=2)+"\n",encoding="utf8")
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops"]
pre=subprocess.run(ssh+[f'test "$(id -un)" = ccwbot_ops && test ! -e {REMOTE} && echo SAFE'],capture_output=True,timeout=25)
assert pre.returncode==0 and b"SAFE" in pre.stdout,repr(pre.stderr[:120])
stream=io.BytesIO()
with tarfile.open(fileobj=stream,mode="w") as t:
 for name,data in asset.items():
  entry=tarfile.TarInfo(name);entry.mode=0o600;entry.size=len(data);t.addfile(entry,io.BytesIO(data))
stage=subprocess.run(ssh+[f'set -eu; umask 077; mkdir -m 700 {REMOTE}; tar -xf - -C {REMOTE}; python3 -m py_compile {REMOTE}/openai_luna_200_runner.py; test ! -e {REMOTE}/openai-luna-ledger.json; echo PRIVATE_STAGED'],input=stream.getvalue(),capture_output=True,timeout=70)
assert stage.returncode==0 and b"PRIVATE_STAGED" in stage.stdout,(stage.returncode,repr(stage.stderr[:120]))
start=subprocess.run(ssh+[f'cd {REMOTE}; nohup bash wait_and_run.sh > openai-luna-status.log 2>&1 < /dev/null & echo KEY_WATCHER_STARTED'],capture_output=True,timeout=25)
assert start.returncode==0 and b"KEY_WATCHER_STARTED" in start.stdout
sizes=[len(x["body"]["messages"][1]["content"].encode("utf8")) for x in jobs]
print(json.dumps({"state":"STAGED_AWAITING_DELEGATED_TEST_KEY","cases":200,"per_symbol":50,
 "source_sha256":DATASET,"prompt_sha256":prompt_sha,"bytes_per_request_min":min(sizes),
 "bytes_per_request_max":max(sizes),"bytes_per_request_avg":round(sum(sizes)/200),
 "hard_budget_usd":0.50,"remote_dir":REMOTE,"no_production_changes":True,"paid_calls_started":False}))
