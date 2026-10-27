"""CCW-29 isolated 200-case replay, never touches production bot, DB or Telegram."""
import argparse,collections,datetime,email.utils,hashlib,json,os,pathlib,shlex,time,urllib.request,urllib.error
P=pathlib.Path("/home/ccwbot_ops/ccw29_full200_v2")
ENV=pathlib.Path("/home/ccwbot_ops/ccw16_replay/secrets/providers.env")
DATASET="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
POS={"unusual_move","fast_move","reversal","trend_acceleration","market_news_alignment"}
NEG={"routine_move","news_only","unclear"}
REQUIRED={"symbol","materiality","novelty","should_alert","reason_code","confidence"}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def credentials():
 assert ENV.is_file() and ENV.stat().st_mode & 0o077==0
 c={}
 for line in ENV.read_text().splitlines():
  if not line.strip():continue
  z=shlex.split(line);assert len(z)==1 and "=" in z[0]
  k,v=z[0].split("=",1);c[k]=v
 assert set(c)=={"GROQ_API_KEY","CLOUDFLARE_ACCOUNT_ID","CLOUDFLARE_API_TOKEN"}
 return c
def validate(reply,symbol):
 try:
  d=json.loads(reply["choices"][0]["message"]["content"])
 except (ValueError,KeyError,IndexError,TypeError):return "invalid_json",None
 if type(d)!=dict or set(d)!=REQUIRED or d["symbol"]!=symbol or type(d["should_alert"])!=bool:return "schema_error",None
 if d["materiality"] not in ("material","routine","unclear") or d["novelty"] not in ("new","continuation","repeated","unclear") or d["confidence"] not in ("low","medium","high"):return "schema_error",None
 if d["should_alert"]:
  if d["materiality"]!="material" or d["novelty"]!="new" or d["reason_code"] not in POS:return "schema_error",None
 elif d["reason_code"] not in NEG:return "schema_error",None
 return "valid",d
def save(path,doc):
 tmp=path.with_suffix(".tmp")
 with open(tmp,"w",encoding="utf-8") as f:
  os.chmod(tmp,0o600);json.dump(doc,f,separators=(",",":"),sort_keys=True);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def retry_seconds(raw):
 try:return max(0,float(raw))
 except (ValueError,TypeError):
  try:return max(0,(email.utils.parsedate_to_datetime(raw)-datetime.datetime.now(datetime.timezone.utc)).total_seconds())
  except (ValueError,TypeError,OverflowError):return 60
def call(row,creds):
 provider=row["provider"]
 if provider=="groq":url="https://api.groq.com/openai/v1/chat/completions";token=creds["GROQ_API_KEY"]
 else:
  account=creds["CLOUDFLARE_ACCOUNT_ID"];assert account.replace("-","").isalnum()
  url=f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions"
  token=creds["CLOUDFLARE_API_TOKEN"]
 payload=json.dumps(row["body"],separators=(",",":")).encode()
 req=urllib.request.Request(url,data=payload,method="POST",headers={"Authorization":"Bearer "+token,"Content-Type":"application/json","User-Agent":"CCW29-200-isolated/1"})
 start=time.monotonic()
 try:
  with urllib.request.urlopen(req,timeout=180) as response:
   obj=json.loads(response.read(1000000));code=response.status
  verdict,dec=validate(obj,row["symbol"])
  result={"status":verdict,"http_status":code,"duration_ms":int((time.monotonic()-start)*1000)}
  if dec is not None:result["decision"]=dec
  usage=obj.get("usage",{})
  if isinstance(usage,dict):
   for k in ("prompt_tokens","completion_tokens","total_tokens"):
    if isinstance(usage.get(k),int):result[k]=usage[k]
  return result
 except urllib.error.HTTPError as e:
  return {"status":"http_error","http_status":e.code,"retry_after":(e.headers.get("Retry-After") or "")[:48],"duration_ms":int((time.monotonic()-start)*1000)}
 except Exception as e:
  return {"status":"transport_error","error_type":type(e).__name__,"duration_ms":int((time.monotonic()-start)*1000)}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--provider",choices=("groq","cloudflare"),required=True)
 p.add_argument("--shard",type=int,required=True)
 p.add_argument("--shards",type=int,required=True)
 a=p.parse_args()
 assert os.getuid()!=0 and pathlib.Path.home()==pathlib.Path("/home/ccwbot_ops")
 assert (a.provider,a.shards) in (("groq",1),("cloudflare",4)) and 0<=a.shard<a.shards
 record=json.loads((P/"jobs.json").read_text())
 manifest=json.loads((P/"manifest.json").read_text())
 assert record["manifest"]==manifest and manifest["dataset_sha256"]==DATASET and len(record["jobs"])==800
 all_jobs=[j for j in record["jobs"] if j["provider"]==a.provider]
 assert len(all_jobs)==400
 jobs=[j for i,j in enumerate(all_jobs) if i%a.shards==a.shard]
 assert len(jobs)==400//a.shards
 assert len({(j["id"],j["prompt"]) for j in jobs})==len(jobs)
 for j in jobs:
  assert j["prompt"] in ("balanced","fresh_leg") and j["provider"]==a.provider
  assert "max_tokens" not in j["body"] and "max_completion_tokens" not in j["body"]
  assert len(j["body"]["messages"])==2
  content=j["body"]["messages"][1]["content"]
  assert sha(content.encode())==j["prompt_sha256"]
  assert sha(json.dumps(j["body"],sort_keys=True,separators=(",",":")).encode())==j["request_sha256"]
  instr=(P/("candidate_"+j["prompt"]+".txt")).read_text(encoding="utf-8").rstrip("\n")
  assert sha(instr.encode())==manifest["prompt_instruction_sha256"][j["prompt"]]
  assert content.startswith(instr+"\nInput JSON:\n")
 secret=credentials()
 name=f"{a.provider}-{a.shard}"
 ledger=P/(name+"-ledger.json")
 lock=P/(name+".lock");os.mkdir(lock,mode=0o700)
 try:
  if ledger.exists():
   doc=json.loads(ledger.read_text())
   assert doc["dataset_sha256"]==DATASET and doc["provider"]==a.provider and doc["shard"]==a.shard
  else:doc={"task":"CCW-29","dataset_sha256":DATASET,"provider":a.provider,"shard":a.shard,"expected_valid":len(jobs),"attempts":[]}
  valid={(r["id"],r["prompt"]) for r in doc["attempts"] if r.get("status")=="valid"}
  for j in jobs:
   key=j["id"],j["prompt"]
   if key in valid:continue
   failures=0
   while True:
    entry={k:j[k] for k in ("id","input_sha256","symbol","provider","prompt","prompt_sha256","request_sha256")}
    entry["timestamp"]=datetime.datetime.now(datetime.timezone.utc).isoformat();entry["status"]="in_flight"
    doc["attempts"].append(entry);save(ledger,doc)
    result=call(j,secret);entry.update(result);save(ledger,doc)
    status=result["status"];http=result.get("http_status")
    if status=="valid":
     valid.add(key)
     print(json.dumps({"provider":a.provider,"shard":a.shard,"valid":len(valid),"expected":len(jobs),"status":"valid"}),flush=True)
     break
    failures+=1
    print(json.dumps({"provider":a.provider,"shard":a.shard,"valid":len(valid),"status":status,"http":http,"retry":failures}),flush=True)
    if status=="http_error" and http in (401,402,403):
     print("STOP_INVALID_AUTH_OR_ACCOUNT",flush=True);return
    if status=="http_error" and http==429:
     sleep=retry_seconds(result.get("retry_after"))+1
     print(json.dumps({"provider":a.provider,"shard":a.shard,"retry_after_seconds":sleep}),flush=True)
     time.sleep(sleep);continue
    if status=="transport_error" and failures<=3:
     time.sleep(min(2**failures,30));continue
    break
  print(json.dumps({"provider":a.provider,"shard":a.shard,"complete":True,"valid":len(valid),"expected":len(jobs),"statuses":dict(collections.Counter(r["status"] for r in doc["attempts"]))}),flush=True)
 finally:os.rmdir(lock)
if __name__=="__main__":main()
