"""Stage and launch two independent AI reviewers, no production decisions in their inputs."""
import hashlib,io,json,pathlib,subprocess,tarfile
BASE=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private")
F=BASE/"fresh200_unseen"
DS="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
REMOTE="/home/ccwbot_ops/ccw29_review_fresh200"
blind=json.loads((F/"fresh200_blind_packet_PRIVATE.json").read_text(encoding="utf8"))
assert blind["dataset_sha256"]==DS and len(blind["cases"])==200
assert len({x["id"] for x in blind["cases"]})==200
assert all("observed" not in x and "baseline" not in x and "should_alert" not in x for x in blind["cases"])
instructions="""Act as an independent BLIND product evaluator of a cryptocurrency market Event Alert. You have not seen the production bot decision, any candidate model decisions, or other evaluator votes. Decide whether an Event Alert is warranted for the CURRENT observed market price move on this specific asset at this moment. Alert ONLY if: (1) the CURRENT observed movement itself is materially notable for the asset from price snapshots, net change, measured time windows, and same-asset historical context (no fixed numeric cutoff); AND (2) it is meaningfully NEW beyond what was already communicated by any recent Event Alerts (meaningful fresh extension or reversal qualifies despite prior similar alert). Old 24-hour moves, since-message displacement, a historical percentile, related news, or frequent previous alerts alone can neither establish nor veto current materiality. News alone never merits an event alert. Evaluate snapshots chronologically and use only supplied evidence; do not invent missing short intervals, volume, catalysts or price history. A small current wobble within a big older move is usually not material, but a major current move is not negated by a later modest rebound. For prior alerts, compare actual elapsed time and additional current price action rather than assuming a global cooldown. If evidence is insufficient or truly borderline choose ambiguous; do not force a confident binary label. Return ONLY valid JSON with exactly four fields: warrant = alert|no_alert|ambiguous; materiality = material|routine|unclear; novelty = new|repeated|unclear; rationale = a concise, specific, evidence-based explanation in English naming the observed market move and novelty context. Alert is allowed only with materiality material and novelty new."""
jobs={"dataset_sha256":DS,"instructions":instructions,"instructions_sha256":hashlib.sha256(instructions.encode()).hexdigest(),
 "cases":[{"id":x["id"],"symbol":x["symbol"],"input_sha256":x["input_sha256"],"input":x["input"]} for x in blind["cases"]]}
worker=(BASE/"blind_ai_review_worker.py").read_bytes()
compile(worker.decode(),"<review_worker>","exec")
assets={"blind_review_jobs.json":json.dumps(jobs,separators=(",",":"),ensure_ascii=True).encode(),"worker.py":worker}
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode="w") as tf:
 for name,data in assets.items():
  item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o600;tf.addfile(item,io.BytesIO(data))
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops"]
pre=subprocess.run(ssh+[f'test "$(id -un)" = ccwbot_ops && test ! -e {REMOTE} && echo READY'],capture_output=True,timeout=20)
assert pre.returncode==0 and b"READY" in pre.stdout
stage=subprocess.run(ssh+[f'set -eu; umask 077; mkdir -m 700 {REMOTE}; tar -xf - -C {REMOTE}; python3 -m py_compile {REMOTE}/worker.py; echo STAGED'],input=buf.getvalue(),capture_output=True,timeout=55)
assert stage.returncode==0 and b"STAGED" in stage.stdout,repr(stage.stderr[:300])
run=f'set -eu; cd {REMOTE}; for model in llama qwen; do for shard in 0 1 2 3; do nohup python3 -u worker.py --model "$model" --shard "$shard" > "$model-$shard.log" 2>&1 < /dev/null & done; done; echo AI_REVIEW_STARTED'
launch=subprocess.run(ssh+[run],capture_output=True,timeout=30)
assert launch.returncode==0 and b"AI_REVIEW_STARTED" in launch.stdout,repr(launch.stderr[:300])
(F/"ai_review_manifest_PRIVATE.json").write_text(json.dumps({"dataset_sha256":DS,"cases":200,"reviewers":["llama-4-scout","qwen3-30b"],"not_human":True,"worker_sha256":hashlib.sha256(worker).hexdigest(),"instructions_sha256":jobs["instructions_sha256"]},indent=2)+"\n",encoding="utf8")
print("STAGED_AND_STARTED",DS,"200 PER INDEPENDENT AI MODEL","NO_CANDIDATE_DECISIONS","PRODUCTION_UNCHANGED")
