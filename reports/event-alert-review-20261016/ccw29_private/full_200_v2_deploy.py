"""CCW-29 full 200-case improved-prompt replay; builds audited jobs and starts isolated provider workers."""
from __future__ import annotations
import collections,copy,hashlib,io,json,os,pathlib,subprocess,sys,tarfile
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016"
HERE=BASE/"ccw29_private/full_200_v2"
HERE.mkdir(parents=True,exist_ok=True)
REMOTE="/home/ccwbot_ops/ccw29_full200_v2"
HOST="ccwbot-prod-ops"
DATA_SHA="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import load_frozen,digest
from bot.services.ai_agent_groq import _event_significance_prompt_payload
from bot.alerting.event_identity import _json_dumps
dataset=load_frozen(BASE/"v2_private_sanitized.json")
assert dataset["dataset_sha256"]==DATA_SHA and len(dataset["cases"])==200
assert len({c["id"] for c in dataset["cases"]})==200
assert collections.Counter(c["symbol"] for c in dataset["cases"])=={"BTC":50,"ETH":50,"GRAM":50,"SOL":50}
owner=json.loads((BASE/"ccw41_private/owner_reference_candidate_v1_20261022.json").read_text(encoding="utf-8"))
label={c["id"]:c["final"] for c in owner["case_labels"]}
assert set(label)=={c["id"] for c in dataset["cases"]}
assert set(label.values())<= {"alert","no_alert","ambiguous"}
prod=collections.Counter()
for c in dataset["cases"]:
 yes=c["observed"].get("should_alert")
 assert type(yes) is bool
 lab=label[c["id"]]
 prod["ambiguous" if lab=="ambiguous" else "TP" if lab=="alert" and yes else "FP" if lab=="no_alert" and yes else "FN" if lab=="alert" else "TN"]+=1
print("LOCAL_EVIDENCE_AUDIT",json.dumps({"cases":200,"by_symbol":dict(collections.Counter(c["symbol"] for c in dataset["cases"])),"owner_labels":dict(collections.Counter(label.values())),"observed_production":dict(prod),"source_sha":DATA_SHA}),flush=True)
pr=BASE/"ccw43_private"
e1=(pr/"ccw43_incremental_market_leg_v1.txt").read_text(encoding="utf-8").rstrip("\n")
e2=(pr/"ccw43_two_sided_counterfactual_v1.txt").read_text(encoding="utf-8").rstrip("\n")
assert hashlib.sha256(e1.encode()).hexdigest()=="af47056653aa7257ffe0ab5e339f216b45f889cc6c18890472492a5622a77247"
assert hashlib.sha256(e2.encode()).hexdigest()=="aab1596ee2cf8432a9bb7a427323d3a23a76e82e16f02b0b640a8cfd790f8228"
core,sep,_=e1.partition("CCW-43 E1,")
assert sep and core.strip()==e2.partition("CCW-43 E2,")[0].strip()
core=core.rstrip()
prompts={
 "balanced":core+"""

CCW-29 new balanced market-path decision policy:
FIRST pass: independently judge whether the supplied CURRENT analysed-window movement itself is market-significant for this exact asset. Ground that in its magnitude, actual time-ordered snapshots, supported short-window movements and same-asset history. An old price gap since last message, a sizable 24-hour move, a high percentile, news, another timestamp, or reversal wording CANNOT turn a small CURRENT move into a material event.
SECOND pass (only after material): check that there is a substantively fresh market leg against any previous alert. Compare the actual after-alert displacement cl with cw, observed recent path and previous alert age. An already-mentioned three-hour window overlapping an alert is not fresh by itself. A same-direction drop/rise may nevertheless be NEW if there is clearly material further displacement AFTER that alert supported by current snapshots, even if the preceding alert was just minutes ago or counts are high. A small fresh tick is not sufficient. High cnt or identical directional semantic family alone is not a veto.
Use a fair negative check: if you would issue the same alert from a modest routine cw only because the prior message is old or because cl spans many hours, reject it. Use a fair positive check: if a material cw contains a meaningful additional recent fall/rise that the earlier notification could not have described, retain it. A partial rebound must not erase a confirmed major additional leg; a high c24 must not manufacture a new cw leg.
Do not use rigid percentage thresholds. Keep materiality then novelty then decision in strict six-field schema. If uncertain on either, no alert. No unsupported catalysts or headlines as triggers.""",
 "fresh_leg":core+"""

CCW-29 new recent-episode and false-alarm sanity policy:
Read the price snapshots chronologically (negative minute markers are older; zero is latest). Separate the CURRENT analysed-window market event from historical developments.
1. Is the CURRENT analysed-window net displacement and within-window path itself sufficiently substantial for this asset to interrupt someone? Use cw, observations s, optional c30/c60 and same-asset percentile as context, but do NOT decide significance from cl, c24, prev, news, event counts, a mere direction change or one momentary bounce. Very small and flat present paths are routine even if the previously delivered alert is old, historical percentiles are elevated or unrelated news is dramatic.
2. Only after a MATERIAL current move: what substantive part of this move was not captured by the previous alert? Repeated similarly directed windows can overlap. Check previous delivery age and the displacement since that message, then corroborate with visible CURRENT path; mark repeated/continuation where the same meaningful segment is already covered. Conversely a strong new observed extension after a recent alert, or a separately meaningful reversal, is novel regardless of identical direction, high counts, or short age. Do not impose a global semantic cooldown at this analysis stage: recipient cooldown is a separate later operation.
3. Challenge BOTH types of mistake before deciding: avoid alerts about a routine current-window wobble plus a large stale cl/c24; avoid suppression of a substantive fresh recent extension because of many earlier alerts. Missing short windows should not be fabricated, and absence of recent prior alerts is not affirmative novelty by itself.
Return only the six specified JSON fields, no reasoning preamble. No fixed numerical gates or news-only alerts."""
}
assert len(prompts)==2 and prompts["balanced"]!=prompts["fresh_leg"]
for k,v in prompts.items():
 assert all(t in v for t in ("should_alert","materiality","novelty","reason_code"))
 (HERE/f"candidate_{k}.txt").write_text(v+"\n",encoding="utf-8")
print("NEW_PROMPTS",json.dumps({k:hashlib.sha256(v.encode()).hexdigest() for k,v in prompts.items()}),flush=True)
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8",HOST]
def remote(cmd,data=None,timeout=45):
 return subprocess.run(ssh+[cmd],input=data,capture_output=True,timeout=timeout)
pre=remote(f'test "$(id -un)" = ccwbot_ops && test -r /home/ccwbot_ops/ccw16_replay/private_calls.json && test -r /home/ccwbot_ops/ccw16_replay/secrets/providers.env && test ! -e {REMOTE} && echo READY')
assert pre.returncode==0 and b"READY" in pre.stdout,"Preflight failed; nothing changed"
old=remote("cat /home/ccwbot_ops/ccw16_replay/private_calls.json")
assert old.returncode==0
base=json.loads(old.stdout)
assert base["dataset_sha256"]==DATA_SHA
templates={provider:next(x["body"] for x in base["calls"] if x["provider"]==provider and x["prompt"]=="production") for provider in ("groq","cloudflare")}
jobs=[]
for case in dataset["cases"]:
 compact=_json_dumps(_event_significance_prompt_payload(case["input"]))
 assert json.loads(compact)["sym"]==case["symbol"]
 for provider in ("groq","cloudflare"):
  for key,instr in prompts.items():
   body=copy.deepcopy(templates[provider])
   assert len(body["messages"])==2 and body["messages"][0]["content"]=="You are a careful crypto monitoring assistant."
   user=instr+"\nInput JSON:\n"+compact
   body["messages"][1]["content"]=user
   body.pop("max_tokens",None);body.pop("max_completion_tokens",None)
   assert "max_tokens" not in body and "max_completion_tokens" not in body
   assert len(user.encode())<12000
   jobs.append({"id":case["id"],"input_sha256":case["input_sha256"],"symbol":case["symbol"],
    "provider":provider,"prompt":key,"prompt_sha256":hashlib.sha256(user.encode()).hexdigest(),
    "request_sha256":hashlib.sha256(json.dumps(body,separators=(",",":"),sort_keys=True).encode()).hexdigest(),"body":body})
assert len(jobs)==800 and len({(j["provider"],j["prompt"],j["id"]) for j in jobs})==800
print("JOBS_AUDIT",json.dumps({"calls":len(jobs),"by_provider":dict(collections.Counter(j["provider"] for j in jobs)),"models":dict(collections.Counter(j["body"]["model"] for j in jobs)),"token_output_caps_present":False}),flush=True)
manifest={"task":"CCW-29","dataset_sha256":DATA_SHA,"case_count":200,"new_candidates":list(prompts),
 "prompt_instruction_sha256":{k:hashlib.sha256(v.encode()).hexdigest() for k,v in prompts.items()},
 "expected_calls":800,"provider_work_shards":{"groq":1,"cloudflare":4},
 "labels_sent_to_server":False,"baseline_rerun":False,"production_bot_changed":False,
 "max_output_tokens":"unset_provider_default","source_type":"200_original_historical_owner_tuned_not_blind"}
(HERE/"manifest_private.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
jobdoc={"manifest":manifest,"jobs":jobs}
worker=HERE/"worker.py"
assert worker.exists() and worker.stat().st_size>3000,"Run the companion audited isolated worker before staging"
payload={"manifest.json":json.dumps(manifest,indent=2).encode(),
 "jobs.json":json.dumps(jobdoc,separators=(",",":"),ensure_ascii=True).encode(),"worker.py":worker.read_bytes()}
for key in prompts:payload[f"candidate_{key}.txt"]=(HERE/f"candidate_{key}.txt").read_bytes()
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode="w") as tar:
 for name,b in payload.items():
  t=tarfile.TarInfo(name);t.size=len(b);t.mode=0o600;tar.addfile(t,io.BytesIO(b))
stage=remote(f'set -eu; test "$(id -un)" = ccwbot_ops; umask 077; mkdir -m 700 {REMOTE}; tar -xf - -C {REMOTE}; python3 -m py_compile {REMOTE}/worker.py; echo READY_STAGED',buf.getvalue(),90)
assert stage.returncode==0 and b"READY_STAGED" in stage.stdout, "Stage verification failed; do not auto launch"
# Stop obsolete small test (only when both PID and cwd are verified) to release its provider budget.
old_stop=remote('''set -eu;
pid=3791077
if test -d /proc/$pid; then
 cwd=$(readlink /proc/$pid/cwd || true)
 args=$(ps -p $pid -o args= || true)
 if test "$cwd" = /home/ccwbot_ops/ccw29_fresh_holdout; then
  case "$args" in *"runner.py --provider groq"*) kill -TERM "$pid"; echo OLD_20_STOPPED_FOR_FULL_200 ;; *) echo OLD_NOT_MATCHED ;; esac
 else echo OLD_NOT_MATCHED; fi
else echo OLD_ALREADY_FINISHED; fi''')
assert old_stop.returncode==0,"Old-workload check failed; full replay is staged but not started"
print("OLD_WORKER",old_stop.stdout.decode().strip(),flush=True)
start=f'''set -eu; cd {REMOTE};
test ! -e groq-0.lock; test ! -e cloudflare-0.lock;
nohup python3 -u worker.py --provider groq --shard 0 --shards 1 > groq-0.log 2>&1 < /dev/null & gp=$!
for idx in 0 1 2 3; do nohup python3 -u worker.py --provider cloudflare --shard "$idx" --shards 4 > "cloudflare-$idx.log" 2>&1 < /dev/null & done
echo FULL200_STARTED_GROQ_PID=$gp
'''
launch=remote(start,timeout=30)
assert launch.returncode==0 and b"FULL200_STARTED_GROQ_PID=" in launch.stdout,"Launch not confirmed; inspect safely"
print(launch.stdout.decode().strip())
print("DONE_STAGED","source_200_verified","two_new_prompts","800_new_calls","no_new_baseline",flush=True)
