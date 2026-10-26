"""Resume CCW-29 Groq after server-supplied 429 Retry-After. Preserve previous ledger."""
import importlib.util, pathlib, subprocess
f=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw43_private\ccw29_deploy_isolated.py")
spec=importlib.util.spec_from_file_location("deploy29",str(f));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=m.RUNNER
old='finished={(x["id"],x["prompt"]) for x in doc["attempts"]}'
new='finished={(x["id"],x["prompt"]) for x in doc["attempts"] if x.get("status")=="valid"}'
assert source.count(old)==1
source=source.replace(old,new)
old='''   result=do_call(row,creds);entry.update(result);save(ledger,doc)
   print(json.dumps({"provider":a.provider,"done":len(doc["attempts"]),"total":60,"prompt":row["prompt"],"status":result["status"],"http":result.get("http_status"),"duration_ms":result.get("duration_ms")}),flush=True)
   if result["status"]=="http_error" and result.get("http_status")==429:
    # Respect provider enforcement, never bypass quota or switch to paid routing.
    break'''
new='''   result=do_call(row,creds);entry.update(result);save(ledger,doc)
   for retry in range(1,9):
    if result["status"]!="http_error" or result.get("http_status")!=429:break
    try:pause=int(float(result.get("retry_after") or 20))
    except (ValueError,TypeError):pause=20
    pause=max(1,min(pause+1,180))
    print(json.dumps({"provider":a.provider,"rate_limited":True,"retry_after_seconds":pause,"retry":retry}),flush=True)
    time.sleep(pause)
    entry={k:row[k] for k in ("id","input_sha256","provider","prompt","symbol","prompt_sha256","request_sha256")}
    entry["timestamp"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    entry["retry"]=retry
    entry["status"]="in_flight"
    doc["attempts"].append(entry);save(ledger,doc)
    result=do_call(row,creds);entry.update(result);save(ledger,doc)
   print(json.dumps({"provider":a.provider,"attempts":len(doc["attempts"]),"total_unique":60,"prompt":row["prompt"],"status":result["status"],"http":result.get("http_status"),"duration_ms":result.get("duration_ms")}),flush=True)
   if result["status"]=="http_error" and result.get("http_status")==429:
    break'''
assert source.count(old)==1
source=source.replace(old,new)
remote="/home/ccwbot_ops/ccw29_replay"
cmd="set -eu; cd "+remote+"; test ! -e runner-v1.py; cat > runner-next.py; chmod 600 runner-next.py; python3 -m py_compile runner-next.py; mv runner.py runner-v1.py; mv runner-next.py runner.py; nohup python3 -u runner.py --provider groq > groq-resumed.log 2>&1 < /dev/null & p=$!; echo GROQ_RESUMED_PID=$p"
r=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8",m.HOST,cmd],input=source.encode(),capture_output=True,timeout=60)
print("DEPLOY_EXIT",r.returncode,"RESULT",r.stdout.decode(errors="replace").strip())
if r.returncode:print("ERROR_CLASS","ssh_or_remote_patch_failure");raise SystemExit(1)
