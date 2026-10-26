"""Finalize the frozen worker's strict schema check and verify isolated server copy. Zero API calls."""
import hashlib,pathlib,subprocess
base=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\economical_200")
worker=(base/"economical_luna_runner_PRIVATE.py").read_bytes()
s=worker.decode("utf8")
assert 'range(1)' in s and '==200' in s and 'BUDGET=0.4' in s and 'MAX_COMPLETION_TOKENS=2048' in s
assert 'elif d["reason_code"] not in NEG or (d["materiality"]=="material" and d["novelty"]=="new")' in s
compile(s,"economical_luna_runner.py","exec")
sha=hashlib.sha256(worker).hexdigest()
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops"]
remote="/home/ccwbot_ops/ccw45_economical_200"
test=subprocess.run(ssh+[f'test "$(id -un)" = ccwbot_ops && test ! -s {remote}/openai_test_key.private && test ! -e {remote}/openai-luna-ledger.json && echo SAFE'],capture_output=True,timeout=25)
assert test.returncode==0 and b"SAFE" in test.stdout,(test.returncode,test.stderr[:300])
upload=subprocess.run(ssh+[f"set -eu; umask 077; cat > {remote}/openai_luna_200_runner.py; chmod 600 {remote}/openai_luna_200_runner.py; python3 -m py_compile {remote}/openai_luna_200_runner.py; sha256sum {remote}/openai_luna_200_runner.py"],input=worker,capture_output=True,timeout=40)
assert upload.returncode==0,(upload.returncode,upload.stderr[:300])
assert upload.stdout.decode().split()[0]==sha
(base/"economical_worker_sha256.txt").write_text(sha+"  openai_luna_200_runner.py\n",encoding="utf8")
print("READY_NO_KEY_NO_PAID_CALLS worker_sha256="+sha)
