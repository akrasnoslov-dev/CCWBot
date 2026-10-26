"""Stop unnecessary CCW-29 baseline repeat and continue only new prompts."""
import subprocess, json, hashlib, pathlib
host="ccwbot-prod-ops"
dir="/home/ccwbot_ops/ccw29_replay"
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8",host]
get=subprocess.run(ssh+["cat "+dir+"/runner.py"],capture_output=True,timeout=20)
if get.returncode: raise SystemExit("Cannot read versioned existing runner")
source=get.stdout.decode("utf-8")
needle='for row in jobs:\n   key='
assert source.count(needle)==1
assert 'finished={(x["id"],x["prompt"]) for x in doc["attempts"] if x.get("status")=="valid"}' in source
modified=source.replace(needle,'for row in jobs:\n   if row["prompt"]=="production":continue\n   key=')
assert modified.count('if row["prompt"]=="production":continue')==1
assert hashlib.sha256(modified.encode()).hexdigest()!=hashlib.sha256(source.encode()).hexdigest()
target=dir+"/runner_no_repeat_production.py"
stage="set -eu; test \"$(id -un)\" = ccwbot_ops; test ! -e "+target+"; umask 077; cat > "+target+"; python3 -m py_compile "+target+"; echo MODIFIED_RUNNER_STAGED"
r=subprocess.run(ssh+[stage],input=modified.encode(),capture_output=True,timeout=30)
assert r.returncode==0 and b"MODIFIED_RUNNER_STAGED" in r.stdout,"New runner not staged, current process unchanged"
# Only stop the exact prior Groq worker if still running; never touch prod bot.
oldpid=3781936
kill="set -eu; args=$(ps -p "+str(oldpid)+" -o args= || true); case \"$args\" in *\"runner.py --provider groq\"*) kill -TERM "+str(oldpid)+"; sleep 2 ;; *) : ;; esac; if ps -p "+str(oldpid)+" -o args= | grep -q 'runner.py --provider groq'; then echo OLD_STILL_RUNNING; exit 1; fi; echo GROQ_OLD_STOPPED"
r=subprocess.run(ssh+[kill],capture_output=True,timeout=30)
if r.returncode:raise SystemExit("New runner staged but previous still running; no second launch")
launch="set -eu; cd "+dir+"; nohup python3 -u runner_no_repeat_production.py --provider groq > groq-new-only.log 2>&1 < /dev/null & p=$!; echo NEW_ONLY_PID=$p"
r=subprocess.run(ssh+[launch],capture_output=True,timeout=30)
assert r.returncode==0 and b"NEW_ONLY_PID" in r.stdout
print(r.stdout.decode().strip())
print("SKIP_PENDING_PRODUCTION_CALLS","YES","PREVIOUS_RESULTS_PRESERVED","YES","NEW_PROMPTS","E1/E2 ONLY")
