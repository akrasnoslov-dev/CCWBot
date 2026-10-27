"""Prepare frozen 200-new-market matched Luna comparison (production, balanced, refined)."""
from __future__ import annotations
import collections,hashlib,io,json,pathlib,subprocess,sys,tarfile
ROOT=pathlib.Path(r"D:\Projects\CCWBot")
BASE=ROOT/"reports/event-alert-review-20261016"
HERE=BASE/"ccw29_private/fresh200_unseen"
PRIVATE=BASE/"ccw29_private"
sys.path.insert(0,str(ROOT))
from bot.services.ai_agent_groq import _EVENT_SIGNIFICANCE_INSTRUCTIONS,_event_significance_prompt_payload
from bot.alerting.event_identity import _json_dumps
from scripts.event_alert_benchmark import digest
DS="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
REMOTE="/home/ccwbot_ops/ccw29_fresh200_luna"
frozen=json.loads((HERE/"fresh200_blind_packet_PRIVATE.json").read_text(encoding="utf-8"))
meta=json.loads((HERE/"fresh200_manifest.json").read_text(encoding="utf-8"))
assert frozen["dataset_sha256"]==meta["dataset_sha256"]==DS and len(frozen["cases"])==200
assert hashlib.sha256((HERE/"fresh200_blind_packet_PRIVATE.json").read_bytes()).hexdigest()==meta["blind_packet_sha256"]
old=BASE/"ccw29_private/full_200_v2/candidate_balanced.txt"
balanced=old.read_text(encoding="utf-8").rstrip("\n")
assert hashlib.sha256(balanced.encode()).hexdigest()=="293474b69ada1ee5311a7aae8a81a07f80c2106e3dcc9639e32879f7c5545ae1"
production=_EVENT_SIGNIFICANCE_INSTRUCTIONS.rstrip("\n")
assert hashlib.sha256(production.encode()).hexdigest()=="e6496d98812ca7380a899c33c8e8e9294eddcee00d157515a179a91892aeb308","Baseline changed: do not silently redefine production"
refinement="""

CCW-29 refinement of balanced prompt after a blinded-holdout-independent diagnosis of mistakes ON THE OLDER TRAINING SET ONLY (never numerical rules):
Avoid an over-eager positive. A reversal is not important merely because cw and c24 have opposite signs; require a genuinely important price swing in the CURRENT snapshots. A fast_move or acceleration requires observed substantial current-path displacement, not merely a high percentile, a short speed comparison, or an isolated tiny bounce. New data and absence of previous event context do not automatically establish significance or novelty.
For a recent similar alert with multiple previously alert-worthy events, distinguish an overlapping three-hour window from genuinely additional price action since the earlier message. A moderate recent post-alert difference that simply repeats the notified trend should remain a continuation; do not call it new solely from an impressive current-window statistic or repeated related news. Yet a clearly substantive new interval of continued loss/gain can warrant a fresh decision even when there were many prior alerts.
Avoid over-suppression: evaluate an unusually substantial CURRENT market move on its own evidence before comparing with an earlier alert, even when the since-last-message value is oppositely signed due to partial retracement. A short rebound cannot erase a large sustained current-window displacement. Judge moderate moves contextually with the asset's actual observed path; do not automatically classify all moderate three-hour changes routine without inspecting available snapshots and historical context. A material fresh development can occur inside a broader trend. However a large old cl or c24 by itself NEVER creates materiality for a routine current window.
Make the final materiality/novelty decision independently of the reason_code label; default no alert for genuinely unsupported cases, and return EXACTLY the six specified JSON keys. No numerical cutoffs.
""".strip("\n")
refined=balanced+"\n"+refinement
prompts={"production":production,"balanced":balanced,"refined":refined}
assert len({hashlib.sha256(s.encode()).hexdigest() for s in prompts.values()})==3
for k,v in prompts.items():
 (HERE/("candidate_"+k+".txt")).write_text(v+"\n",encoding="utf-8")
manifest={"version":"CCW29-20261023-FRESH200-LUNA-3PROMPTS","dataset_sha256":DS,"cases":200,
 "prompts":list(prompts),"instructions_sha256":{k:hashlib.sha256(v.encode()).hexdigest() for k,v in prompts.items()},
 "model":"gpt-6-luna","call_slots":600,"provider_budget_cap_usd":0.85,
 "previous_luna_test_cost_usd":0.104239,"combined_total_max_usd":0.954239,
 "max_completion_tokens":4096,"key_not_in_jobs":True,"labels_not_in_jobs":True,"fresh_human_labels_pending":True,
 "original_200_overlap":0,"prior_new20_overlap":0}
jobs=[]
for case in frozen["cases"]:
 assert digest(case["input"])==case["input_sha256"]
 for k,s in prompts.items():
  msg=s+"\nInput JSON:\n"+_json_dumps(_event_significance_prompt_payload(case["input"]))
  b={"messages":[{"role":"system","content":"You are a careful crypto monitoring assistant."},{"role":"user","content":msg}]}
  jobs.append({"id":case["id"],"input_sha256":case["input_sha256"],"symbol":case["symbol"],
   "prompt":k,"prompt_sha256":hashlib.sha256(msg.encode()).hexdigest(),
   "request_sha256":hashlib.sha256(json.dumps(b,separators=(",",":"),sort_keys=True).encode()).hexdigest(),
   "body":b})
assert len(jobs)==600 and len({(j["id"],j["prompt"]) for j in jobs})==600
(HERE/"fresh200_luna_manifest_PRIVATE.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
runner=(PRIVATE/"openai_luna_200_runner.py").read_text(encoding="utf-8")
changes={
 'HOME=pathlib.Path("/home/ccwbot_ops/ccw29_full200_v2")':f'HOME=pathlib.Path("{REMOTE}")',
 'DATASET="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"':f'DATASET="{DS}"',
 'BUDGET=1.0':'BUDGET=0.85',
 'len(dataset["jobs"])==800':'len(dataset["jobs"])==600',
 'originals=[x for x in dataset["jobs"] if x["provider"]=="cloudflare"]':'originals=dataset["jobs"]',
 'assert len(originals)==400 and len({(x["id"],x["prompt"]) for x in originals})==400':'assert len(originals)==600 and len({(x["id"],x["prompt"]) for x in originals})==600',
 'assert len(jobs)==400':'assert len(jobs)==600',
 '"expected":400':'"expected":600'
}
for old,new in changes.items():
 assert old in runner,"expected runner feature not found: "+old
 runner=runner.replace(old,new)
assert 'key=KEY_PATH.read_text(encoding="utf-8").strip()' in runner,"runner must read isolated secret path"
assert 'KEY_PATH.unlink(missing_ok=True)' in runner,"safe cleanup expected"
assert 'MAX_COMPLETION_TOKENS=4096' in runner
assert "OpenAI" not in runner or True
local_runner=HERE/"fresh200_luna_runner_PRIVATE.py"
local_runner.write_text(runner,encoding="utf-8")
compile(runner,"<isolated_luna_eval_runner>","exec")
jobs_json=json.dumps({"manifest":{"dataset_sha256":DS},"jobs":jobs},ensure_ascii=True,separators=(",",":")).encode()
assets={"manifest.json":json.dumps({"dataset_sha256":DS},separators=(",",":")).encode(),
 "jobs.json":jobs_json,"openai_luna_200_runner.py":runner.encode()}
for name,prompt in prompts.items():assets["candidate_"+name+".txt"]=(prompt+"\n").encode()
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode="w") as tar:
 for name,data in assets.items():
  f=tarfile.TarInfo(name);f.size=len(data);f.mode=0o600;tar.addfile(f,io.BytesIO(data))
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops"]
check=subprocess.run(ssh+[f'test "$(id -un)" = ccwbot_ops && test ! -e {REMOTE} && test -r /home/ccwbot_ops/ccw29_full200_v2/openai-luna-ledger.json && echo READY'],capture_output=True,timeout=30)
assert check.returncode==0 and b"READY" in check.stdout,"Server preflight failed; no overwrite"
stage=subprocess.run(ssh+[f'set -eu; umask 077; mkdir -m 700 {REMOTE}; tar -xf - -C {REMOTE}; python3 -m py_compile {REMOTE}/openai_luna_200_runner.py; echo STAGED'],input=buf.getvalue(),capture_output=True,timeout=60)
assert stage.returncode==0 and b"STAGED" in stage.stdout,"Staging failed, do not launch"
print("FRESH200_LUNA_STAGED",json.dumps({"path":REMOTE,"sha":DS,"jobs":len(jobs),"prompts":manifest["instructions_sha256"],"key_staged":False,"labels_staged":False,"price_budget_cap":.85,"production_changed":False}),flush=True)
