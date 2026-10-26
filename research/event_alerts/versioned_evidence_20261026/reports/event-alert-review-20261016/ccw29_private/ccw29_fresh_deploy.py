"""Stage and execute a finite, blind, genuine new-event holdout replay. No production changes."""
from __future__ import annotations
import copy,hashlib,importlib.util,io,json,pathlib,subprocess,sys,tarfile
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016"
HERE=BASE/"ccw29_private/fresh_holdout"
PRIV=BASE/"ccw43_private"
HOST="ccwbot-prod-ops"
REM="/home/ccwbot_ops/ccw29_fresh_holdout"
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import digest
from bot.services.ai_agent_groq import _event_significance_prompt_payload
from bot.alerting.event_identity import _json_dumps
blind=json.loads((HERE/"holdout_20_blind_packet_PRIVATE.json").read_text(encoding="utf-8"))
manifest=json.loads((HERE/"holdout_manifest.json").read_text(encoding="utf-8"))
assert manifest["dataset_sha256"]==blind["dataset_sha256"]=="cb087b1a52e32b48f96dabda9d9dbf72744fcdb37c273a906572567005fef873"
assert len(blind["cases"])==20 and {c["symbol"] for c in blind["cases"]}=={"BTC","ETH","GRAM","SOL"}
assert all(digest(c["input"])==c["input_sha256"] for c in blind["cases"])
assert (HERE/"reviewer_gpt6_provisional_blind.json").exists(),"Seal blind provisional review BEFORE running candidate predictions"
assert hashlib.sha256((HERE/"reviewer_gpt6_provisional_blind.json").read_bytes()).hexdigest()=="e90075842d5765cdeb5708b20515964f60c6e3f34a79638e4173dcbd3d0ccd2e"
prompt_info={
 "e1":("ccw43_incremental_market_leg_v1.txt","1a74766e81d775d4d93159dd4cae15b7ef8867164f94783ee0aee6ad760120de"),
 "e2":("ccw43_two_sided_counterfactual_v1.txt","4efe2d8b1ae7ff9d429ec9237a885802e1c67afaf9a5160c5a0802f891d55e0a")
}
prompts={}
for key,(name,sha) in prompt_info.items():
 raw=(PRIV/name).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==sha and raw.endswith(b"\n")
 prompts[key]=raw[:-1].decode("utf-8")
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8",HOST]
pre=subprocess.run(ssh+[f'test "$(id -un)" = ccwbot_ops && test -r /home/ccwbot_ops/ccw16_replay/private_calls.json && test -r /home/ccwbot_ops/ccw16_replay/secrets/providers.env && test ! -e {REM} && echo READY'],capture_output=True,timeout=30)
assert pre.returncode==0 and b"READY" in pre.stdout,"remote preflight failed, no changes made"
old=subprocess.run(ssh+["cat /home/ccwbot_ops/ccw16_replay/private_calls.json"],capture_output=True,timeout=30)
assert old.returncode==0
base=json.loads(old.stdout)
assert base["dataset_sha256"]=="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
templates={provider:next(x["body"] for x in base["calls"] if x["provider"]==provider and x["prompt"]=="production") for provider in ("groq","cloudflare")}
rows=[]
for case in blind["cases"]:
 for provider in ("groq","cloudflare"):
  for version,txt in prompts.items():
   body=copy.deepcopy(templates[provider])
   assert len(body["messages"])==2 and body["messages"][0]["content"]=="You are a careful crypto monitoring assistant."
   body["messages"][1]["content"]=txt+"\nInput JSON:\n"+_json_dumps(_event_significance_prompt_payload(case["input"]))
   body.pop("max_tokens",None);body.pop("max_completion_tokens",None)
   message=body["messages"][1]["content"]
   assert len(message.encode()) < 6000, "cloudflare request conservative envelope"
   rows.append({"id":case["id"],"input_sha256":case["input_sha256"],"provider":provider,"prompt":version,
      "symbol":case["symbol"],"prompt_sha256":hashlib.sha256(message.encode()).hexdigest(),
      "request_sha256":hashlib.sha256(json.dumps(body,separators=(",",":"),sort_keys=True).encode()).hexdigest(),
      "body":body})
assert len(rows)==80 and len({(x["id"],x["provider"],x["prompt"]) for x in rows})==80
jobs={"version":1,"dataset_sha256":blind["dataset_sha256"],"blind_packet_sha256":manifest["blind_packet_sha256"],"calls":rows}
spec=importlib.util.spec_from_file_location("ccw29deploy",PRIV/"ccw29_deploy_isolated.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
runner=m.RUNNER
oldpath='P=pathlib.Path("/home/ccwbot_ops/ccw29_replay")'
assert runner.count(oldpath)==1
runner=runner.replace(oldpath,f'P=pathlib.Path("{REM}")')
assert runner.count('DATASET="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"')==1
runner=runner.replace('DATASET="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"',f'DATASET="{blind["dataset_sha256"]}"')
a=runner.index("def read_jobs(provider):")
b=runner.index("def validate(reply,symbol):")
new_read=r'''def read_jobs(provider):
 doc=json.loads((P/"holdout_calls.json").read_text())
 assert doc["dataset_sha256"]==DATASET and len(doc["calls"])==80
 selected=[r for r in doc["calls"] if r["provider"]==provider]
 assert len(selected)==40 and len({(r["id"],r["prompt"]) for r in selected})==40
 for r in selected:
  assert r["prompt"] in ("e1","e2") and r["symbol"] in ("BTC","ETH","GRAM","SOL")
  assert len(r["body"]["messages"])==2 and "max_tokens" not in r["body"] and "max_completion_tokens" not in r["body"]
  assert digest(r["body"]["messages"][1]["content"].encode())==r["prompt_sha256"]
  assert digest(json.dumps(r["body"],separators=(",",":"),sort_keys=True).encode())==r["request_sha256"]
 return selected
'''
runner=runner[:a]+new_read+runner[b:]
assert 'finished={(x["id"],x["prompt"]) for x in doc["attempts"]}' in runner
runner=runner.replace('finished={(x["id"],x["prompt"]) for x in doc["attempts"]}', 'finished={(x["id"],x["prompt"]) for x in doc["attempts"] if x.get("status")=="valid"}')
assert '"expected":60' in runner and '"total":60' in runner
runner=runner.replace('"expected":60','"expected":40').replace('"total":60','"total":40')
oldblock='''   result=do_call(row,creds);entry.update(result);save(ledger,doc)
   print(json.dumps({"provider":a.provider,"done":len(doc["attempts"]),"total":40,"prompt":row["prompt"],"status":result["status"],"http":result.get("http_status"),"duration_ms":result.get("duration_ms")}),flush=True)
   if result["status"]=="http_error" and result.get("http_status")==429:
    # Respect provider enforcement, never bypass quota or switch to paid routing.
    break'''
newblock='''   result=do_call(row,creds);entry.update(result);save(ledger,doc)
   for retry in range(1,9):
    if result["status"]!="http_error" or result.get("http_status")!=429:break
    try:pause=int(float(result.get("retry_after") or 20))
    except (TypeError,ValueError):pause=20
    pause=max(1,min(pause+1,180))
    print(json.dumps({"provider":a.provider,"rate_limited":True,"retry_after_seconds":pause,"retry":retry}),flush=True)
    time.sleep(pause)
    entry={k:row[k] for k in ("id","input_sha256","provider","prompt","symbol","prompt_sha256","request_sha256")}
    entry["timestamp"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    entry["retry"]=retry
    entry["status"]="in_flight"
    doc["attempts"].append(entry);save(ledger,doc)
    result=do_call(row,creds);entry.update(result);save(ledger,doc)
   print(json.dumps({"provider":a.provider,"attempts":len(doc["attempts"]),"planned_unique":40,"prompt":row["prompt"],"status":result["status"],"http":result.get("http_status"),"duration_ms":result.get("duration_ms")}),flush=True)
   if result["status"]=="http_error" and result.get("http_status")==429:break'''
assert runner.count(oldblock)==1
runner=runner.replace(oldblock,newblock)
assets={"holdout_calls.json":json.dumps(jobs,separators=(",",":"),ensure_ascii=True).encode(),"runner.py":runner.encode(),
 "stage_manifest.json":json.dumps({"purpose":"CCW-29 unseen frozen 20 inputs; E1/E2 only; no original 200 cases","dataset_sha256":blind["dataset_sha256"],
 "calls":80,"max_tokens":"unset","labels_uploaded":False,"prod_modified":False},indent=2).encode()}
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode="w") as tar:
 for name,b in assets.items():
  info=tarfile.TarInfo(name);info.size=len(b);info.mode=0o600;tar.addfile(info,io.BytesIO(b))
cmd=f'set -eu; test "$(id -un)" = ccwbot_ops; umask 077; mkdir -m 700 {REM}; tar -xf - -C {REM}; python3 -m py_compile {REM}/runner.py; echo FRESH_STAGED'
stage=subprocess.run(ssh+[cmd],input=buf.getvalue(),capture_output=True,timeout=60)
if stage.returncode or b"FRESH_STAGED" not in stage.stdout:raise RuntimeError("staging failed; inspect manually, no automatic retrigger")
cmd=f'set -eu; cd {REM}; nohup python3 -u runner.py --provider groq > groq-status.log 2>&1 < /dev/null & gp=$!; nohup python3 -u runner.py --provider cloudflare > cloudflare-status.log 2>&1 < /dev/null & cp=$!; echo FRESH_HOLDOUT_LAUNCHED groq=$gp cloudflare=$cp'
launch=subprocess.run(ssh+[cmd],capture_output=True,timeout=30)
if launch.returncode or b"FRESH_HOLDOUT_LAUNCHED" not in launch.stdout:raise RuntimeError("remote launch unverified")
(HERE/"staged_calls_manifest_PRIVATE.json").write_text(json.dumps({"dataset_sha256":blind["dataset_sha256"],"count":len(rows),"calls_sha256":hashlib.sha256(assets["holdout_calls.json"]).hexdigest(),"runner_sha256":hashlib.sha256(assets["runner.py"]).hexdigest()},indent=2)+"\n",encoding="utf-8")
print(launch.stdout.decode().strip())
print("PREFLIGHT_PASS","source20",len(blind["cases"]),"new_calls",len(rows),"models",sorted({x["body"]["model"] for x in rows}),"max_tokens_unset",True,"labels_staged",False)
