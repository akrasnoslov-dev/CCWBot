"""Finish immutable fresh200 Luna staging manifest preflight, without reading secret or running API calls."""
import hashlib,io,json,pathlib,subprocess,tarfile
BASE=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh200_unseen")
m=json.loads((BASE/"fresh200_luna_manifest_PRIVATE.json").read_text(encoding="utf8"))
remote="/home/ccwbot_ops/ccw29_fresh200_luna"
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops"]
r=subprocess.run(ssh+[f"cat {remote}/jobs.json"],capture_output=True,timeout=30)
assert r.returncode==0
d=json.loads(r.stdout)
assert len(d["jobs"])==600 and d["manifest"]=={"dataset_sha256":m["dataset_sha256"]}
new={"dataset_sha256":m["dataset_sha256"],"prompt_instruction_sha256":m["instructions_sha256"]}
d["manifest"]=new
assert len({(j["id"],j["prompt"]) for j in d["jobs"]})==600
assets={"jobs.json":json.dumps(d,ensure_ascii=True,separators=(",",":")).encode(),"manifest.json":json.dumps(new,separators=(",",":")).encode()}
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode="w") as tar:
 for name,data in assets.items():
  item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o600;tar.addfile(item,io.BytesIO(data))
test=f'set -eu; test "$(id -un)" = ccwbot_ops; cd {remote}; test ! -e openai-luna-ledger.json; test ! -e openai_test_key.private; tar -xf -; python3 -m py_compile openai_luna_200_runner.py; python3 -c "import json;d=json.load(open(\\"jobs.json\\"));m=json.load(open(\\"manifest.json\\"));assert d[\\"manifest\\"]==m and len(d[\\"jobs\\"])==600 and len(m[\\"prompt_instruction_sha256\\"])==3"; echo MANIFEST_VERIFIED'
p=subprocess.run(ssh+[test],input=buf.getvalue(),capture_output=True,timeout=45)
assert p.returncode==0 and b"MANIFEST_VERIFIED" in p.stdout,repr(p.stderr[:200])
print("FRESH_200_LUNA_JOBS_AND_PROMPT_HASHES_VERIFIED; NO_PAID_CALLS_YET")
