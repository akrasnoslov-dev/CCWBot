"""CCW-45 paid OpenAI Luna test. Isolated 200 cases x 2 prompts; $1 request-budget guard, no production changes."""
from __future__ import annotations
import collections,concurrent.futures,datetime,email.utils,hashlib,json,os,pathlib,shlex,threading,time,urllib.error,urllib.request
HOME=pathlib.Path("/home/ccwbot_ops/ccw45_economical_200")
DATASET="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
KEY_PATH=HOME/"openai_test_key.private"
LEDGER=HOME/"openai-luna-ledger.json"
BUDGET=0.4
INPUT_USD_PER_TOKEN=0.10/1_000_000
OUTPUT_USD_PER_TOKEN=0.50/1_000_000
MAX_COMPLETION_TOKENS=2048
THREADS=4
POS={"unusual_move","fast_move","reversal","trend_acceleration","market_news_alignment"}
NEG={"routine_move","news_only","unclear"}
FIELDS={"symbol","materiality","novelty","should_alert","reason_code","confidence"}
def digest(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atom(doc):
 p=LEDGER.with_suffix(".tmp")
 with open(p,"x",encoding="utf-8") as f:
  os.chmod(p,0o600);json.dump(doc,f,ensure_ascii=True,sort_keys=True,separators=(",",":"));f.flush();os.fsync(f.fileno())
 os.replace(p,LEDGER)
def check_reply(obj,symbol):
 try:d=json.loads(obj["choices"][0]["message"]["content"])
 except (ValueError,KeyError,IndexError,TypeError):return "invalid_json",None
 if type(d)!=dict or set(d)!=FIELDS or d.get("symbol")!=symbol:return "schema_error",None
 if type(d.get("should_alert"))!=bool:return "schema_error",None
 if d["materiality"] not in ("material","routine","unclear") or d["novelty"] not in ("new","continuation","repeated","unclear") or d["confidence"] not in ("low","medium","high"):return "schema_error",None
 if d["should_alert"]:
  if d["materiality"]!="material" or d["novelty"]!="new" or d["reason_code"] not in POS:return "schema_error",None
 elif d["reason_code"] not in NEG or (d["materiality"]=="material" and d["novelty"]=="new"):return "schema_error",None
 return "valid",d
def provider_retry_seconds(value):
 try:return max(0,float(value))
 except (ValueError,TypeError):
  try:return max(0,(email.utils.parsedate_to_datetime(value)-datetime.datetime.now(datetime.timezone.utc)).total_seconds())
  except (ValueError,TypeError,OverflowError):return 30
def call_one(job,key):
 # Only six output fields, no tools, no paid Fast tier, no altered prompt.
 body={"model":"gpt-6-luna","messages":job["body"]["messages"],"response_format":{"type":"json_object"},
       "max_completion_tokens":MAX_COMPLETION_TOKENS}
 headers={"Authorization":"Bearer "+key,"Content-Type":"application/json","User-Agent":"CCW45-isolated-Luna-eval/1"}
 request=urllib.request.Request("https://api.openai.com/v1/chat/completions",
       data=json.dumps(body,separators=(",",":")).encode(),headers=headers,method="POST")
 for retry in range(1):
  start=time.monotonic()
  try:
   with urllib.request.urlopen(request,timeout=180) as resp:
    raw=resp.read(1000000)
    data=json.loads(raw)
    http=resp.status
   verdict,decision=check_reply(data,job["symbol"])
   usage=data.get("usage") or {}
   inp=usage.get("prompt_tokens");out=usage.get("completion_tokens")
   if type(inp)==int and type(out)==int and inp>=0 and out>=0:
    # Uncached pricing is an upper bound when caching is applied; reasoning included in output tokens.
    estimated=inp*INPUT_USD_PER_TOKEN+out*OUTPUT_USD_PER_TOKEN
   else:estimated=job["reserved_usd"]
   result={"status":verdict,"http_status":http,"duration_ms":int((time.monotonic()-start)*1000),
           "estimated_charged_usd":round(estimated,9),
           "prompt_tokens":inp if type(inp)==int else None,
           "completion_tokens":out if type(out)==int else None}
   if decision is not None:result["decision"]=decision
   return result
  except urllib.error.HTTPError as e:
   status=e.code
   if False and status==429 and retry<5:
    pause=provider_retry_seconds(e.headers.get("Retry-After"))+1
    time.sleep(pause);continue
   return {"status":"http_error","http_status":status,"attempt":retry+1,
            "estimated_charged_usd":job["reserved_usd"] if status not in (400,401,403,404,429) else 0.0,
            "duration_ms":int((time.monotonic()-start)*1000)}
  except (urllib.error.URLError,TimeoutError,ValueError,OSError) as e:
   # Unknown completion state: count conservative maximum, do not blindly repeat charged requests.
   return {"status":"transport_error","error_type":type(e).__name__,
           "estimated_charged_usd":job["reserved_usd"],
           "duration_ms":int((time.monotonic()-start)*1000)}
 return {"status":"http_error","http_status":429,"estimated_charged_usd":0.0}
def main():
 assert os.getuid()!=0 and pathlib.Path.home()==pathlib.Path("/home/ccwbot_ops")
 assert HOME.is_dir()
 key=KEY_PATH.read_text(encoding="utf-8").strip()
 assert len(key)>20 and key.startswith("sk-"),"OpenAI test credential not valid-shaped"
 manifest=json.loads((HOME/"manifest.json").read_text())
 dataset=json.loads((HOME/"jobs.json").read_text())
 assert dataset["manifest"]==manifest and manifest["dataset_sha256"]==DATASET and len(dataset["jobs"])==200
 originals=dataset["jobs"]
 assert len(originals)==200 and len({(x["id"],x["prompt"]) for x in originals})==200
 jobs=[]
 for j in originals:
  txt=j["body"]["messages"][1]["content"]
  ins=(HOME/("candidate_"+j["prompt"]+".txt")).read_text(encoding="utf-8").rstrip("\n")
  assert txt.startswith(ins+"\nEVIDENCE JSON:\n")
  assert digest(ins.encode())==manifest["prompt_instruction_sha256"][j["prompt"]]
  assert digest(txt.encode())==j["prompt_sha256"]
  assert j["body"]["messages"][0]["content"]=="You are a careful crypto monitoring assistant."
  # Conservative input-token upper bound from UTF8 bytes plus message framing.
  input_token_upper_bound=sum(len(x["content"].encode("utf-8")) for x in j["body"]["messages"])+1024
  reserved=(input_token_upper_bound*INPUT_USD_PER_TOKEN+MAX_COMPLETION_TOKENS*OUTPUT_USD_PER_TOKEN)
  jobs.append(dict(j,reserved_usd=round(reserved,9)))
 assert len(jobs)==200 and all(j["reserved_usd"]<0.01 for j in jobs)
 assert sum(j["reserved_usd"] for j in jobs)<=BUDGET,"200 calls cannot fit hard budget; zero calls allowed"
 if LEDGER.exists():
  record=json.loads(LEDGER.read_text())
  assert record["dataset_sha256"]==DATASET and record["provider"]=="openai" and record["model"]=="gpt-6-luna" and record["budget_usd"]==BUDGET
 else:
  record={"task":"CCW-45","dataset_sha256":DATASET,"provider":"openai","model":"gpt-6-luna",
    "budget_usd":BUDGET,"price_input_per_million":0.10,"price_output_per_million":0.50,
    "max_completion_tokens":MAX_COMPLETION_TOKENS,"expected":200,"attempts":[]}
  atom(record)
 recorded={(r["id"],r["prompt"]) for r in record["attempts"]}
 spent=sum(x.get("estimated_charged_usd",x.get("reserved_usd",0)) for x in record["attempts"])
 assert spent<=BUDGET+1e-8,"Previously recorded cost exceeds budget"
 pending={};next_index=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as pool:
  while True:
   while len(pending)<THREADS and next_index<len(jobs):
    j=jobs[next_index];next_index+=1;k=(j["id"],j["prompt"])
    if k in recorded:continue
    pending_reserved=sum(p["reserved_usd"] for p in pending.values())
    if spent+pending_reserved+j["reserved_usd"]>BUDGET:
     print(json.dumps({"budget_stop":True,"spent_usd_upper":round(spent,6),
       "inflight_reserved_usd":round(pending_reserved,6),"expected":200}),flush=True)
     next_index=len(jobs);break
    entry={k:j[k] for k in ("id","input_sha256","symbol","prompt","prompt_sha256","request_sha256","reserved_usd")}
    entry["status"]="in_flight";entry["timestamp"]=now()
    record["attempts"].append(entry);atom(record);recorded.add(k)
    fut=pool.submit(call_one,j,key)
    pending[fut]=entry
   if not pending:break
   done,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
   for future in done:
    entry=pending.pop(future)
    try:out=future.result()
    except Exception as e:
     out={"status":"internal_error","error_type":type(e).__name__,"estimated_charged_usd":entry["reserved_usd"]}
    actual=out["estimated_charged_usd"]
    assert 0<=actual<=entry["reserved_usd"]+1e-7,"Metered response exceeds conservative reserved budget"
    entry.update(out);atom(record);spent+=actual
    completed=collections.Counter(r.get("status") for r in record["attempts"])
    print(json.dumps({"provider":"openai","model":"gpt-6-luna","valid":completed["valid"],
      "attempts":sum(completed.values()),"expected":200,"spent_usd_upper":round(spent,6),
      "last_status":out["status"],"last_http":out.get("http_status")}),flush=True)
    if out.get("http_status") in (400,401,402,403) and out["status"]!="valid":
     next_index=len(jobs)
     print("STOP_AUTH_OR_ACCOUNT_ACCESS",flush=True)
  result=collections.Counter(x.get("status") for x in record["attempts"])
  print(json.dumps({"run_finished":True,"valid":result["valid"],"attempts":len(record["attempts"]),
       "expected":200,"spent_usd_upper":round(spent,6),"budget_usd":BUDGET,
       "statuses":dict(result)}),flush=True)
 # Remove temporary delegated secret from isolated workspace on completed/blocked run.
 KEY_PATH.unlink(missing_ok=True)
if __name__=="__main__":main()
