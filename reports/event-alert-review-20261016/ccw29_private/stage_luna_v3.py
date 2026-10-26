"""CCW-29: prepare exact-match Luna v3 replay on 200 frozen events, no production writes."""
from __future__ import annotations
import hashlib,io,json,pathlib,subprocess,tarfile
HERE=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh200_unseen")
PROMPT_FILE=HERE/"candidate_refined_v3_UNTESTED.txt"
RUNNER_FILE=HERE/"fresh200_luna_runner_PRIVATE.py"
DATASET="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
REMOTE="/home/ccwbot_ops/ccw29_fresh200_luna_v3"
BUDGET=0.35
assert PROMPT_FILE.is_file() and RUNNER_FILE.is_file()
m=json.loads((HERE/"fresh200_luna_manifest_PRIVATE.json").read_text(encoding="utf8"))
assert m["dataset_sha256"]==DATASET and m["call_slots"]==600
text=PROMPT_FILE.read_text(encoding="utf-8").rstrip("\r\n")
assert len(text)>1000 and "OUTPUT exactly six JSON keys" in text and "No fixed numeric significance cutoff" in text
old=(HERE/"candidate_refined.txt").read_text(encoding="utf-8").rstrip("\n")
assert hashlib.sha256(old.encode()).hexdigest()==m["instructions_sha256"]["refined"]
s=hashlib.sha256(text.encode()).hexdigest()
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops"]
source=subprocess.run(ssh+["cat /home/ccwbot_ops/ccw29_fresh200_luna/jobs.json"],capture_output=True,timeout=30)
assert source.returncode==0 and source.stdout
data=json.loads(source.stdout)
assert data["manifest"]["dataset_sha256"]==DATASET and len(data["jobs"])==600
old_jobs=[j for j in data["jobs"] if j["prompt"]=="refined"]
assert len(old_jobs)==200 and len({j["id"] for j in old_jobs})==200
jobs=[]
for oldj in old_jobs:
 msg=oldj["body"]["messages"]
 assert len(msg)==2 and msg[0]=={"role":"system","content":"You are a careful crypto monitoring assistant."}
 prefix="Input JSON:\n"
 c=msg[1]["content"];needle=old+"\n"+prefix
 assert c.startswith(needle)
 original=c[len(needle):]
 assert len(original)>100 and original.strip().startswith("{")
 newmsg=text+"\n"+prefix+original
 body={"messages":[msg[0],{"role":"user","content":newmsg}]}
 out={k:oldj[k] for k in ("id","input_sha256","symbol")}
 out.update(prompt="v3",prompt_sha256=hashlib.sha256(newmsg.encode()).hexdigest(),
            request_sha256=hashlib.sha256(json.dumps(body,separators=(",",":"),sort_keys=True).encode()).hexdigest(),
            body=body)
 assert oldj["input_sha256"]==out["input_sha256"]
 jobs.append(out)
manifest={"dataset_sha256":DATASET,"prompt_instruction_sha256":{"v3":s}}
jobdoc={"manifest":manifest,"jobs":jobs}
assert len(jobs)==200
runner=RUNNER_FILE.read_text(encoding="utf-8")
substitutions={
 "/home/ccwbot_ops/ccw29_fresh200_luna":REMOTE,
 "BUDGET=0.85":"BUDGET=0.35",
 'len(dataset["jobs"])==600':'len(dataset["jobs"])==200',
 'assert len(originals)==600':'assert len(originals)==200',
 'assert len(jobs)==600':'assert len(jobs)==200',
 '"expected":600':'"expected":200',
}
for a,b in substitutions.items():
 assert a in runner,(a,"missing from original runner");runner=runner.replace(a,b)
assert 'key=KEY_PATH.read_text(encoding="utf-8").strip()' in runner
assert 'KEY_PATH.unlink(missing_ok=True)' in runner
assert 'MAX_COMPLETION_TOKENS=4096' in runner
assert runner.count("BUDGET=0.35")==1
compile(runner,"luna_v3_worker.py","exec")
assets={
 "manifest.json":json.dumps(manifest,separators=(",",":")).encode(),
 "jobs.json":json.dumps(jobdoc,ensure_ascii=True,separators=(",",":")).encode(),
 "candidate_v3.txt":(text+"\n").encode(),
 "openai_luna_200_runner.py":runner.encode(),
}
waiter="""#!/usr/bin/env bash
set -euo pipefail
cd /home/ccwbot_ops/ccw29_fresh200_luna_v3
for i in {1..1440}; do
 if [[ -s openai_test_key.private ]]; then
   sleep 3
   if [[ -s openai_test_key.private ]] && [[ ! -e openai-luna-ledger.json ]]; then
     echo LUNA_V3_KEY_READY
     exec python3 -u openai_luna_200_runner.py
   fi
 fi
 sleep 30
done
echo NO_TEST_KEY_IN_12H
exit 2
"""
assets["wait_and_run.sh"]=waiter.encode()
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode="w") as tar:
 for name,body in assets.items():
  ti=tarfile.TarInfo(name);ti.size=len(body);ti.mode=0o600;tar.addfile(ti,io.BytesIO(body))
test=subprocess.run(ssh+[f'test "$(id -un)" = ccwbot_ops && test ! -e {REMOTE} && echo READY'],capture_output=True,timeout=25)
assert test.returncode==0 and b"READY" in test.stdout
cmd=f'set -eu; umask 077; mkdir -m 700 {REMOTE}; tar -xf - -C {REMOTE}; python3 -m py_compile {REMOTE}/openai_luna_200_runner.py; test ! -e {REMOTE}/openai-luna-ledger.json; echo VERIFIED'
staging=subprocess.run(ssh+[cmd],input=buf.getvalue(),capture_output=True,timeout=45)
assert staging.returncode==0 and b"VERIFIED" in staging.stdout,(staging.returncode,staging.stderr[:200])
(HERE/"v3_luna_manifest_PRIVATE.json").write_text(json.dumps({"dataset_sha256":DATASET,"prompts":{"v3":s},
 "count":200,"budget_this_run_usd":BUDGET,"prior_openai_tests_total_usd":0.261808,
 "cumulative_budget_cap_usd":0.611808,"new_cost_if_all_valid_estimated_usd":0.053,
 "production_changed":False,"saved_key_present":False},indent=2)+"\n",encoding="utf8")
launch=subprocess.run(ssh+[f'set -eu; cd {REMOTE}; nohup bash wait_and_run.sh > openai-luna-status.log 2>&1 < /dev/null & echo WAITING_FOR_PRIVATE_TEST_KEY'],capture_output=True,timeout=30)
assert launch.returncode==0 and b"WAITING_FOR_PRIVATE_TEST_KEY" in launch.stdout
print(json.dumps({"dataset_sha256":DATASET,"original_cases":len(jobs),"v3_prompt_sha256":s,
 "budget_cap_usd":BUDGET,"watcher_started":True,"paid_calls_started":False,"key_needed":True,
 "remote_dir":REMOTE,"production_changed":False}))
