"""Stage verified model-visible pilot calls into isolated CCW-16 workspace.

No keys or labels leave the workstation. No API call here.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.ccw15_prompt_pack import build_prompt, FROZEN_DATASET_SHA256
from scripts.ccw16_dual_provider_pilot import load_manifest, work_items, request_body

ROOT = Path(r"D:\Projects\CCWBot")
PRIVATE = ROOT / "reports" / "event-alert-review-20261016" / "ccw16_private"
manifest = load_manifest(PRIVATE / "pilot-manifest.json")
items = work_items(manifest["cases"])
by_id = {c["id"]: c for c in manifest["cases"]}
calls = []
for job in items:
    case = by_id[job["id"]]
    prompt = build_prompt(case["input"], job["prompt"])
    body = request_body(job["provider"], case["input"], prompt)
    calls.append({
        "id": job["id"],
        "input_sha256": job["input_sha256"],
        "provider": job["provider"],
        "prompt": job["prompt"],
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "body": body,
    })
record = {"version": 1, "dataset_sha256": FROZEN_DATASET_SHA256, "calls": calls}
payload = json.dumps(record, separators=(",",":"), ensure_ascii=True).encode("utf-8")
remote_file = "/home/ccwbot_ops/ccw16_replay/private_calls.json"
command = ("set -eu; test \"$(id -un)\" = ccwbot_ops; umask 077; "
           "test ! -e "+remote_file+"; "
           "cat > "+remote_file+"; chmod 600 "+remote_file+"; "
           "printf 'STAGED_OK\\n'")
result = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "ccwbot-prod-ops", command],
    input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
)
if result.returncode != 0 or b"STAGED_OK" not in result.stdout:
    raise RuntimeError(f"Remote private prompt staging failed (exit={result.returncode})")
print(json.dumps({"staged_cases": len(manifest["cases"]), "staged_calls":len(calls),
                  "input_bytes":len(payload),
                  "ids_unique":len(set((c["id"],c["provider"],c["prompt"]) for c in calls)) == len(calls),
                  "providers": sorted(set(c["provider"] for c in calls))}))
