"""CCW-29 isolated finite provider replay deployer. Not part of tracked repository."""
from __future__ import annotations
import hashlib, io, json, pathlib, subprocess, tarfile, sys
HOME = pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw43_private")
REMOTE = "/home/ccwbot_ops/ccw29_replay"
HOST = "ccwbot-prod-ops"
FILES = {
    "candidate_e1.txt": ("ccw43_incremental_market_leg_v1.txt", "1a74766e81d775d4d93159dd4cae15b7ef8867164f94783ee0aee6ad760120de"),
    "candidate_e2.txt": ("ccw43_two_sided_counterfactual_v1.txt", "4efe2d8b1ae7ff9d429ec9237a885802e1c67afaf9a5160c5a0802f891d55e0a")
}
RUNNER = r'''
"""CCW-29: isolated finite 20 cases x 3 prompts x 2 providers, no production writes."""
import argparse, copy, datetime, hashlib, json, os, pathlib, shlex, time, urllib.request, urllib.error
from collections import Counter
P=pathlib.Path("/home/ccwbot_ops/ccw29_replay")
OLD=pathlib.Path("/home/ccwbot_ops/ccw16_replay")
DATASET="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
EXPECTED_BASE="e6496d98812ca7380a899c33c8e8e9294eddcee00d157515a179a91892aeb308"
CANDIDATES={
 "e1":("candidate_e1.txt","1a74766e81d775d4d93159dd4cae15b7ef8867164f94783ee0aee6ad760120de","af47056653aa7257ffe0ab5e339f216b45f889cc6c18890472492a5622a77247"),
 "e2":("candidate_e2.txt","4efe2d8b1ae7ff9d429ec9237a885802e1c67afaf9a5160c5a0802f891d55e0a","aab1596ee2cf8432a9bb7a427323d3a23a76e82e16f02b0b640a8cfd790f8228")
}
REQUIRED={"symbol","materiality","novelty","should_alert","reason_code","confidence"}
POS={"unusual_move","fast_move","reversal","trend_acceleration","market_news_alignment"}
NEG={"routine_move","news_only","unclear"}
def digest(x): return hashlib.sha256(x).hexdigest()
def read_creds():
 path=OLD/"secrets/providers.env"
 assert path.is_file() and path.stat().st_mode & 0o077 == 0,"isolated free-provider credentials unavailable or insecure"
 pairs={}
 for line in path.read_text().splitlines():
  if not line.strip(): continue
  pieces=shlex.split(line)
  assert len(pieces)==1 and "=" in pieces[0],"credentials parse"
  k,v=pieces[0].split("=",1);pairs[k]=v
 assert set(pairs)=={"GROQ_API_KEY","CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID"},"credential scope"
 return pairs
def read_jobs(provider):
 doc=json.loads((OLD/"private_calls.json").read_text())
 assert doc["dataset_sha256"]==DATASET and len(doc["calls"])==120
 base=[x for x in doc["calls"] if x["provider"]==provider and x["prompt"]=="production"]
 assert len(base)==20 and len({x["id"] for x in base})==20
 instr={}
 for k,(name,filehash,txthash) in CANDIDATES.items():
  raw=(P/name).read_bytes()
  assert digest(raw)==filehash and raw.endswith(b"\n"),"candidate file integrity"
  instr[k]=raw[:-1].decode("utf-8")
  assert digest(instr[k].encode())==txthash
 jobs=[]
 for row in base:
  body=row["body"]
  assert len(body["messages"])==2 and body["messages"][0]["content"]=="You are a careful crypto monitoring assistant."
  old=body["messages"][1]["content"]
  before,sep,compact=old.partition("\nInput JSON:\n")
  assert sep and digest(before.encode())==EXPECTED_BASE,"baseline must match frozen instructions"
  parsed=json.loads(compact)
  assert parsed["sym"] in ("BTC","ETH","SOL","GRAM")
  assert digest(old.encode())==row["prompt_sha256"]
  for key, instruction in [("production",before),("e1",instr["e1"]),("e2",instr["e2"])]:
   changed=copy.deepcopy(body)
   user=instruction+"\nInput JSON:\n"+compact
   changed["messages"][1]["content"]=user
   # Explicit user choice: remove artificial per-request output token ceiling.
   # Provider inherent model/account limits remain and are measured.
   changed.pop("max_tokens",None)
   changed.pop("max_completion_tokens",None)
   jobs.append({"id":row["id"],"input_sha256":row["input_sha256"],
      "provider":provider,"prompt":key,"symbol":parsed["sym"],
      "body":changed,"prompt_sha256":digest(user.encode()),"request_sha256":digest(json.dumps(changed,separators=(",",":"),sort_keys=True).encode())})
 assert len(jobs)==60 and len({(x["id"],x["prompt"]) for x in jobs})==60
 return jobs
def validate(reply,symbol):
 try: raw=reply["choices"][0]["message"]["content"];d=json.loads(raw)
 except (ValueError,KeyError,IndexError,TypeError):return "invalid_json",None
 if not isinstance(d,dict) or set(d)!=REQUIRED or d["symbol"]!=symbol:return "schema_error",None
 if type(d["should_alert"]) is not bool or d["materiality"] not in ("material","routine","unclear") or d["novelty"] not in ("new","continuation","repeated","unclear") or d["confidence"] not in ("low","medium","high"):return "schema_error",None
 if d["should_alert"]:
  if d["materiality"]!="material" or d["novelty"]!="new" or d["reason_code"] not in POS:return "schema_error",None
 elif d["reason_code"] not in NEG:return "schema_error",None
 return "valid",d
def save(path, doc):
 temp=path.with_suffix(".tmp")
 with open(temp,"x",encoding="utf-8") as f:
  os.chmod(temp,0o600)
  json.dump(doc,f,ensure_ascii=True,separators=(",",":"),sort_keys=True)
  f.flush();os.fsync(f.fileno())
 os.replace(temp,path)
def do_call(row,creds):
 prov=row["provider"]
 if prov=="groq":
  url="https://api.groq.com/openai/v1/chat/completions";token=creds["GROQ_API_KEY"]
 else:
  account=creds["CLOUDFLARE_ACCOUNT_ID"]
  assert account.replace("-","").isalnum()
  url=f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions";token=creds["CLOUDFLARE_API_TOKEN"]
 payload=json.dumps(row["body"],separators=(",",":")).encode()
 req=urllib.request.Request(url,data=payload,method="POST",headers={"Authorization":"Bearer "+token,"Content-Type":"application/json","User-Agent":"CCW29-isolated-benchmark/1"})
 start=time.monotonic()
 try:
  with urllib.request.urlopen(req,timeout=180) as response:
   data=json.loads(response.read(600000))
   status=response.status
  verdict,decision=validate(data,row["symbol"])
  result={"status":verdict,"http_status":status,"duration_ms":int((time.monotonic()-start)*1000)}
  if decision is not None:result["decision"]=decision
  usage=data.get("usage",{})
  if isinstance(usage,dict):
   for k in ("prompt_tokens","completion_tokens","total_tokens"):
    if isinstance(usage.get(k),int):result[k]=usage[k]
  return result
 except urllib.error.HTTPError as e:
  retry=e.headers.get("Retry-After","")
  return {"status":"http_error","http_status":e.code,"retry_after":retry[:16],"duration_ms":int((time.monotonic()-start)*1000)}
 except Exception as e:
  return {"status":"transport_error","error_type":type(e).__name__,"duration_ms":int((time.monotonic()-start)*1000)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--provider",choices=("groq","cloudflare"),required=True);a=p.parse_args()
 assert os.getuid()!=0 and pathlib.Path.home()==pathlib.Path("/home/ccwbot_ops")
 lock=P/(a.provider+".lock");os.mkdir(lock,mode=0o700)
 try:
  creds=read_creds();jobs=read_jobs(a.provider)
  ledger=P/(a.provider+"-ledger.json")
  if ledger.exists():
   doc=json.loads(ledger.read_text())
   assert doc["dataset_sha256"]==DATASET and doc["provider"]==a.provider
  else:doc={"version":1,"task":"CCW-29","dataset_sha256":DATASET,"provider":a.provider,"expected":60,"max_tokens_setting":"provider_default_unset","attempts":[]}
  finished={(x["id"],x["prompt"]) for x in doc["attempts"]}
  for row in jobs:
   key=(row["id"],row["prompt"])
   if key in finished:continue
   entry={k:row[k] for k in ("id","input_sha256","provider","prompt","symbol","prompt_sha256","request_sha256")}
   entry["timestamp"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
   entry["status"]="in_flight"
   doc["attempts"].append(entry);save(ledger,doc)
   result=do_call(row,creds);entry.update(result);save(ledger,doc)
   print(json.dumps({"provider":a.provider,"done":len(doc["attempts"]),"total":60,"prompt":row["prompt"],"status":result["status"],"http":result.get("http_status"),"duration_ms":result.get("duration_ms")}),flush=True)
   if result["status"]=="http_error" and result.get("http_status")==429:
    # Respect provider enforcement, never bypass quota or switch to paid routing.
    break
   if result["status"]=="http_error" and result.get("http_status") in (401,402,403):
    break
  counts=Counter(x["status"] for x in doc["attempts"])
  print(json.dumps({"provider":a.provider,"completed":len(doc["attempts"]),"planned":60,"statuses":dict(counts)}),flush=True)
 finally:
  os.rmdir(lock)
if __name__=="__main__":main()
'''
def ssh(command, input_bytes=None):
 return subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8",HOST,command],input=input_bytes,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
def main():
 payload={}
 for dest,(name,sha) in FILES.items():
  b=(HOME/name).read_bytes()
  assert hashlib.sha256(b).hexdigest()==sha,(name,"hash mismatch")
  payload[dest]=b
 payload["runner.py"]=RUNNER.encode("utf-8")
 payload["authorization.json"]=json.dumps({"issue":"CCW-29","owner_approved":True,"scope":"20 frozen inputs x 3 prompts (incl matched fresh production control) x Groq/Cloudflare; 120 one-shot attempts","output_token_ceiling":"unset; provider defaults","paid_service":False,"production_bot_modified":False},indent=2).encode()
 test=ssh('test "$(id -un)" = ccwbot_ops && test -r /home/ccwbot_ops/ccw16_replay/private_calls.json && test -r /home/ccwbot_ops/ccw16_replay/secrets/providers.env && test ! -e '+REMOTE+' && echo READY')
 if test.returncode or b"READY" not in test.stdout: raise RuntimeError("PRECHECK_FAILED: SSH alias, isolated credentials/source or existing run directory; nothing changed")
 buf=io.BytesIO()
 with tarfile.open(fileobj=buf,mode="w") as tar:
  for name,b in payload.items():
   info=tarfile.TarInfo(name);info.size=len(b);info.mode=0o600;tar.addfile(info,io.BytesIO(b))
 stage='set -eu; umask 077; mkdir -m 700 '+REMOTE+'; tar -xf - -C '+REMOTE+'; test -s '+REMOTE+'/runner.py; python3 -m py_compile '+REMOTE+'/runner.py; echo STAGED'
 r=ssh(stage,buf.getvalue())
 if r.returncode or b"STAGED" not in r.stdout: raise RuntimeError("STAGING_FAILED: inspect SSH privately; do not blindly re-stage")
 launch='set -eu; cd '+REMOTE+'; nohup python3 -u runner.py --provider groq > groq-status.log 2>&1 < /dev/null & gp=$!; nohup python3 -u runner.py --provider cloudflare > cloudflare-status.log 2>&1 < /dev/null & cp=$!; printf "CCW29_LAUNCHED groq_pid=%s cloudflare_pid=%s\n" "$gp" "$cp"'
 r=ssh(launch)
 if r.returncode or b"CCW29_LAUNCHED" not in r.stdout: raise RuntimeError("LAUNCH_UNVERIFIED: stage succeeded; inspect remote status")
 print(r.stdout.decode().strip())
 print("STAGED_FILES",sorted(payload),"MAX_TOKENS","unset","PLANNED_REQUESTS",120,"PROD_DB_TELEGRAM","untouched")
if __name__=="__main__":main()
