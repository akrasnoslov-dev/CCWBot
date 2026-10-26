"""CCW-44: optional quality-first enhancement with actual read-only historical price snapshots."""
from __future__ import annotations
import collections,csv,datetime,hashlib,io,json,math,pathlib,statistics,subprocess,time,tarfile
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016/ccw29_private"
OUT=BASE/"quality_first_200"
REMOTE="/home/ccwbot_ops/ccw44_quality_first_200"
DATASET="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
PSQL=r"C:\Program Files\PostgreSQL\18\bin\psql.exe"
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops"]
def run(cmd,timeout=30,input=None):
 p=subprocess.run(ssh+[cmd],input=input,capture_output=True,timeout=timeout)
 if p.returncode:raise RuntimeError("SSH preflight/transfer failed: "+str(p.returncode))
 return p.stdout
pre=run(f'cd {REMOTE}; test ! -e openai_test_key.private && test ! -e openai-luna-ledger.json && echo SAFE')
assert b"SAFE" in pre,"Paid test may have started; no mutation permitted"
jobs_doc=json.loads(run(f"cat {REMOTE}/jobs.json",40));manifest=jobs_doc["manifest"]
assert manifest["dataset_sha256"]==DATASET and len(jobs_doc["jobs"])==200
psql_cmd=[PSQL,"-X","-w","-v","ON_ERROR_STOP=1","-h","127.0.0.1","-p","15433",
 "-U","ccwbot_investigator","-d","ccwbot","-q"]
tunnel=subprocess.Popen(["ssh","-N","-o","BatchMode=yes","-o","ExitOnForwardFailure=yes",
 "-L","127.0.0.1:15433:127.0.0.1:15433","ccwbot-prod-ops"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 identity=None
 for i in range(12):
  if tunnel.poll() is not None:raise RuntimeError("Secure tunnel closed: "+str(tunnel.returncode))
  try:
   p=subprocess.run(psql_cmd+["-t","-A","-c",
    "SELECT current_user, current_setting('transaction_read_only'), current_setting('default_transaction_read_only')"],
    capture_output=True,timeout=7,text=True,encoding="utf8")
   if p.returncode==0:
    identity=p.stdout.strip();break
  except (subprocess.TimeoutExpired,OSError):pass
  time.sleep(1)
 if identity!="ccwbot_investigator|on|on":raise RuntimeError("READ_ONLY_IDENTITY_NOT_VERIFIED")
 query="""COPY (
 SELECT symbol,raw_input_json::jsonb->>'timestamp_utc' AS checked_utc,
        raw_input_json::jsonb->'market'->>'price' AS price,
        NULL::text AS change_24h
 FROM event_ai_analyses
 WHERE created_at >= '2026-09-16T00:00:00Z'::timestamptz
   AND created_at < '2026-10-23T00:00:00Z'::timestamptz
   AND symbol IN ('BTC','ETH','GRAM','SOL')
   AND analysis_type='event_analysis'
   AND raw_input_json IS NOT NULL
 ORDER BY symbol,created_at
 ) TO STDOUT WITH (FORMAT CSV, HEADER TRUE)"""
 p=subprocess.run(psql_cmd+["-c",query],capture_output=True,timeout=120,text=True,encoding="utf8",errors="replace")
 if p.returncode:raise RuntimeError("READ_ONLY_SNAPSHOT_QUERY_FAILED")
 rows=list(csv.DictReader(io.StringIO(p.stdout)))
finally:
 tunnel.terminate()
 try:tunnel.wait(timeout=4)
 except subprocess.TimeoutExpired:tunnel.kill();tunnel.wait(timeout=3)
data=collections.defaultdict(list)
for r in rows:
 if not r["price"] or not r["checked_utc"]:continue
 try:
  x=datetime.datetime.fromisoformat(r["checked_utc"]).replace(tzinfo=datetime.timezone.utc).timestamp()
  price=float(r["price"]);assert math.isfinite(price) and price>0
 except (ValueError,AssertionError):continue
 data[r["symbol"]].append((x,price))
assert all(len(data[x])>=1000 for x in ("BTC","ETH","GRAM","SOL")),json.dumps({k:len(v) for k,v in data.items()})
def fmt(t):
 return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()
def stats(series):
 x=[100*(b[1]/a[1]-1) for a,b in zip(series,series[1:]) if 900<=b[0]-a[0]<=3300]
 return {"usable_intervals":len(x),"abs_30m_pct_median":round(statistics.median(map(abs,x)),4) if x else None,
  "abs_30m_pct_p90":round(sorted(map(abs,x))[int(.9*(len(x)-1))],4) if len(x)>10 else None,
  "return_30m_pct_stdev":round(statistics.pstdev(x),4) if len(x)>2 else None}
def reduce_history(series,asof):
 last=[r for r in series if asof-24*3600 <= r[0]<=asof]
 bins={}
 for t,v in last:
  i=int((asof-t)//1800)
  if 0<=i<=47 and (i not in bins or t>bins[i][0]):bins[i]=(t,v)
 selected=sorted(bins.values())
 return [{"ts_utc":fmt(t),"minutes_before_now":round((asof-t)/60,1),"price_usd":round(v,8)} for t,v in selected]
valid_counts=collections.Counter();periods=[]
for job in jobs_doc["jobs"]:
 txt=job["body"]["messages"][1]["content"]
 prefix,sep,old=txt.partition("\n\nEVIDENCE JSON:\n");assert sep
 payload=json.loads(old)
 ts=datetime.datetime.fromisoformat(payload["observation_utc"].replace("Z","+00:00")).timestamp()
 coins=data[job["symbol"]]
 eligible=[r for r in coins if r[0]<=ts]
 assert len(eligible)>=200
 hist=reduce_history(eligible,ts)
 seven=[r for r in eligible if r[0]>=ts-7*86400]
 month=[r for r in eligible if r[0]>=ts-30*86400]
 st7,st30=stats(seven),stats(month)
 assert len(hist)>=12 and st7["usable_intervals"]>=24,(job["id"],len(hist),st7)
 payload["verified_price_history"]={
  "actual_24h_event_ai_analyses_market_price_30m_buckets":hist,
  "no_interpolation_or_fabricated_points":True,
  "source":"read_only_event_ai_analyses_market_price",
  "rolling_7d_observed_return_distribution":st7,
  "rolling_30d_observed_return_distribution":st30,
  "volatility_regime_note":"Observed short-window changes are distribution evidence only. No hard alert threshold or probability confidence is implied.",
  "coverage_notes":{"actual_24h_snapshot_bucket_count":len(hist),
                    "sampled_30m_prices_not_tick_data":True}}
 valid_counts[job["symbol"]]+=1;periods.append(len(hist))
 new=prefix+sep+json.dumps(payload,ensure_ascii=False,separators=(",",":"),sort_keys=True)
 job["body"]["messages"][1]["content"]=new
 job["prompt_sha256"]=hashlib.sha256(new.encode()).hexdigest()
 job["request_sha256"]=hashlib.sha256(json.dumps(job["body"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
assert len(jobs_doc["jobs"])==200 and all(valid_counts[x]==50 for x in ("BTC","ETH","GRAM","SOL"))
manifest["verified_long_price_history"]=True
manifest["long_history_source"]="ccwbot_investigator read-only event_ai_analyses_market_price"
manifest["source_window"]="Sep 16–Oct 23 2026, no future observations in each case"
jobbytes=json.dumps(jobs_doc,ensure_ascii=True,separators=(",",":")).encode()
manbytes=json.dumps(manifest,ensure_ascii=True,separators=(",",":")).encode()
assert jobs_doc["manifest"]==manifest
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode="w") as tf:
 for name,b in (("jobs.json",jobbytes),("manifest.json",manbytes)):
  e=tarfile.TarInfo(name);e.size=len(b);e.mode=0o600;tf.addfile(e,io.BytesIO(b))
# Recheck no key or ledger immediately before replacing; make no production DB writes.
cmd=f'set -eu; cd {REMOTE}; test ! -e openai_test_key.private; test ! -e openai-luna-ledger.json; tar -xf - -C {REMOTE}; python3 -c "import json; a=json.load(open(\\"manifest.json\\"));b=json.load(open(\\"jobs.json\\")); assert len(b[\\"jobs\\"])==200 and b[\\"manifest\\"]==a"; echo QUALITY_RICH_24H_STAGED'
result=run(cmd,timeout=50,input=buffer.getvalue())
assert b"QUALITY_RICH_24H_STAGED" in result
(OUT/"quality_first_manifest.json").write_text(json.dumps({**manifest,"one_off_budget_usd":.50,"source_period":"Oct17–22","input_history_rows":len(rows),"per_case_24h_buckets":{ "min":min(periods),"max":max(periods),"avg":round(sum(periods)/200,2)}},indent=2)+"\n",encoding="utf8")
print(json.dumps({"status":"200_QUALITY_RICH_24H_STAGED_AWAITING_KEY",
 "historical_snapshot_rows":len(rows),"per_symbol_rows":{k:len(v) for k,v in data.items()},
 "buckets24h_min":min(periods),"buckets24h_avg":round(sum(periods)/200,1),
 "average_request_bytes":round(sum(len(j["body"]["messages"][1]["content"].encode()) for j in jobs_doc["jobs"])/200),
 "production_modified":False,"paid_calls_started":False}))
