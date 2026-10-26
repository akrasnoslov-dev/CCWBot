"""CCW-29 blind AI review worker: reuses existing provider transport; no prod writes."""
import argparse,collections,datetime,hashlib,importlib.util,json,os,pathlib,time
BASE=pathlib.Path("/home/ccwbot_ops/ccw29_review_fresh200")
DS="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
MODELS={"llama":"@cf/meta/llama-4-scout-17b-16e-instruct","qwen":"@cf/qwen/qwen3-30b-a3b-fp8"}
spec=importlib.util.spec_from_file_location("transport","/home/ccwbot_ops/ccw29_full200_v2/worker.py")
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
def validate(resp,sym):
 try:j=json.loads(resp["choices"][0]["message"]["content"])
 except (IndexError,KeyError,ValueError,TypeError):return "invalid_json",None
 if not isinstance(j,dict) or set(j)!={"warrant","materiality","novelty","rationale"}:return "schema_error",None
 if j["warrant"] not in ("alert","no_alert","ambiguous") or j["materiality"] not in ("material","routine","unclear") or j["novelty"] not in ("new","repeated","unclear"):return "schema_error",None
 if not isinstance(j["rationale"],str) or not (12<=len(j["rationale"])<=1600):return "schema_error",None
 if j["warrant"]=="alert" and (j["materiality"],j["novelty"])!=("material","new"):return "schema_error",None
 return "valid",j
w.validate=validate
def main():
 p=argparse.ArgumentParser();p.add_argument("--model",choices=MODELS,required=True);p.add_argument("--shard",type=int,required=True);a=p.parse_args()
 assert os.getuid()!=0 and pathlib.Path.home()==pathlib.Path("/home/ccwbot_ops") and 0<=a.shard<4
 f=json.loads((BASE/"blind_review_jobs.json").read_text())
 assert f["dataset_sha256"]==DS and len(f["cases"])==200 and len(f["instructions"])>300
 assert hashlib.sha256(f["instructions"].encode()).hexdigest()==f["instructions_sha256"]
 cases=[c for i,c in enumerate(f["cases"]) if i%4==a.shard]
 assert len(cases)==50
 token=w.creds()
 key=a.model+"-"+str(a.shard)
 ledger=BASE/(key+"-ledger.json")
 lock=BASE/(key+".lock");os.mkdir(lock,0o700)
 try:
  if ledger.exists():
   doc=json.loads(ledger.read_text());assert doc["dataset_sha256"]==DS and doc["model"]==MODELS[a.model]
  else:doc={"dataset_sha256":DS,"model":MODELS[a.model],"reviewer":a.model,"expected":50,"attempts":[]}
  done={x["id"] for x in doc["attempts"] if x["status"]=="valid"}
  for c in cases:
   if c["id"] in done:continue
   assert "observed" not in c and "sampling_cohort" not in c
   payload={"model":MODELS[a.model],"response_format":{"type":"json_object"},"max_tokens":1200,"temperature":0.15,
    "messages":[{"role":"system","content":f["instructions"]},{"role":"user","content":"Blind market source JSON:\n"+json.dumps(c["input"],ensure_ascii=True,separators=(",",":"),sort_keys=True)}]}
   row={"id":c["id"],"provider":"cloudflare","symbol":c["symbol"],"body":payload}
   retry=0
   while True:
    rec={"id":c["id"],"input_sha256":c["input_sha256"],"status":"in_flight","timestamp":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    doc["attempts"].append(rec);w.save_atomic(ledger,doc)
    answer=w.api_call(row,token);rec.update(answer);w.save_atomic(ledger,doc)
    if answer["status"]=="valid":
     done.add(c["id"]);print(json.dumps({"reviewer":a.model,"shard":a.shard,"valid":len(done),"expected":50}),flush=True);break
    retry+=1
    if answer["status"]=="http_error" and answer.get("http_status") in (401,402,403):
     print("ACCOUNT_BLOCK",a.model,answer.get("http_status"),flush=True);return
    if answer["status"]=="http_error" and answer.get("http_status")==429:
     delay=w.parse_retry(answer.get("retry_after"))+1
     print("RATE_LIMIT",a.model,round(delay),flush=True);time.sleep(delay);continue
    if retry<=2 and answer["status"] in ("invalid_json","schema_error","transport_error"):
     time.sleep(2*retry);continue
    print("FAILED",a.model,c["id"],answer["status"],flush=True);break
  print(json.dumps({"reviewer":a.model,"shard":a.shard,"finished":True,"valid":len(done),"expected":50}),flush=True)
 finally:os.rmdir(lock)
if __name__=="__main__":main()
