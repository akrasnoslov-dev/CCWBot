"""Read-only provider credential authentication probe on isolated Hetzner identity.
No prompts, chat completions, or secret output."""
import subprocess
import json

remote = r'''
import json
import shlex
import urllib.request
import urllib.error
from pathlib import Path
p = Path("/home/ccwbot_ops/ccw16_replay/secrets/providers.env")
assert p.is_file()
kv = dict(shlex.split(line, posix=True)[0].split("=",1)
          for line in p.read_text(encoding="utf-8").splitlines() if line.strip())
assert set(kv) == {"GROQ_API_KEY","CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID"}
targets = [
 ("groq", "https://api.groq.com/openai/v1/models", kv["GROQ_API_KEY"]),
 ("cloudflare",
  "https://api.cloudflare.com/client/v4/accounts/" +
   kv["CLOUDFLARE_ACCOUNT_ID"] + "/ai/models/search?per_page=1",
  kv["CLOUDFLARE_API_TOKEN"]),
]
for name, endpoint, secret in targets:
    try:
        req=urllib.request.Request(endpoint,headers={
            "Authorization": "Bearer "+secret,
            "User-Agent": "CCW16-credential-preflight/1.0"})
        with urllib.request.urlopen(req, timeout=18) as resp:
            print(json.dumps({"provider":name,"metadata_http_status":resp.status,
                              "authentication":"accepted"}))
    except urllib.error.HTTPError as e:
        print(json.dumps({"provider":name,"metadata_http_status":e.code,
                          "authentication":"not_verified"}))
    except Exception as exc:
        print(json.dumps({"provider":name,"metadata_http_status":None,
                          "authentication":"not_verified",
                          "error_type":type(exc).__name__}))
'''
result=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8",
    "ccwbot-prod-ops","python3 -"], input=remote, text=True,
    capture_output=True, timeout=65)
if result.returncode:
    raise RuntimeError("Remote metadata preflight failed (no secrets printed)")
for line in result.stdout.splitlines():
    record=json.loads(line)
    if not isinstance(record.get("provider"),str):
        raise RuntimeError("Unexpected probe format")
    print(json.dumps(record))
