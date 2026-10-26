"""Replace Groq holdout runner with exact Retry-After compliant resumption, preserving ledger."""
import subprocess,json
host="ccwbot-prod-ops"
remote="/home/ccwbot_ops/ccw29_fresh_holdout"
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8",host]
def command(c,stdin=None):
 return subprocess.run(ssh+[c],input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35)
res=command("cat "+remote+"/runner.py")
assert res.returncode==0
original=res.stdout.decode()
assert original.count("pause=max(1,min(pause+1,180))")==1
changed=original.replace("pause=max(1,min(pause+1,180))","pause=max(1,pause+1)")
needle='  finished={(x["id"],x["prompt"]) for x in doc["attempts"] if x.get("status")=="valid"}'
assert changed.count(needle)==1
changed=changed.replace(needle,'''  # Honor any unresolved server-provided Retry-After before resuming a stopped worker.
  if doc["attempts"]:
   prev=doc["attempts"][-1]
   if prev.get("http_status")==429 and prev.get("retry_after"):
    try: requested=float(prev["retry_after"])
    except (TypeError,ValueError):requested=0
    stamp=datetime.datetime.fromisoformat(prev["timestamp"])
    remaining=max(0,requested+1-(datetime.datetime.now(datetime.timezone.utc)-stamp).total_seconds())
    if remaining:
     print(json.dumps({"provider":a.provider,"initial_retry_after_remaining_seconds":round(remaining,1)}),flush=True)
     time.sleep(remaining)
''' +needle)
# strict prior-state check while process is sleeping, before termination.
res=command("cat "+remote+"/groq-ledger.json")
assert res.returncode==0
ledger=json.loads(res.stdout)
assert ledger["dataset_sha256"]=="cb087b1a52e32b48f96dabda9d9dbf72744fcdb37c273a906572567005fef873"
last=ledger["attempts"][-1]
assert last.get("status")=="http_error" and last.get("http_status")==429,"Last request changed; do not kill during in-flight API call"
stage=f'set -eu; cd {remote}; test ! -e runner_v2.py; umask 077; cat > runner_v2.py; python3 -m py_compile runner_v2.py; echo V2_STAGED'
res=command(stage,changed.encode())
assert res.returncode==0 and b"V2_STAGED" in res.stdout
pid=3789262
# Kill precisely the old Groq holdout runner, not a prod process, confirm it is gone, clean stale lock and restart.
activate=f'''set -eu; cd {remote};
args=$(ps -p {pid} -o args= || true)
case "$args" in *"python3 -u runner.py --provider groq"*) kill -TERM {pid}; sleep 2 ;; *) echo OLD_NOT_RUNNING; exit 1 ;; esac
if ps -p {pid} -o args= | grep -q "runner.py --provider groq"; then echo OLD_STILL_RUNNING; exit 1; fi
rmdir groq.lock
test ! -e runner_v1.py
mv runner.py runner_v1.py
mv runner_v2.py runner.py
nohup python3 -u runner.py --provider groq > groq-v2-status.log 2>&1 < /dev/null & gp=$!
echo GROQ_V2_STARTED_PID=$gp'''
res=command(activate)
if res.returncode!=0:raise RuntimeError("Resumption requires operator inspection; no blind automatic retry")
print(res.stdout.decode().strip())
print("RESUMED_USING_FULL_RETRY_AFTER","YES")
