"""Stage only sanitized case inputs, checkpoint ledgers and approved API credentials."""
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[2]
out = Path(tempfile.gettempdir()) / "pr349_replay"
if out.exists():
    raise RuntimeError("Do not overwrite existing staging area")
data = root / "reports" / "event-alert-review-20261016"
private = data / "merged_pilots_private"
for name in ("v2_private_sanitized.json", "reviewer_A_significance_for_pr1.json"):
    target = out / "reports" / "event-alert-review-20261016" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(data / name, target)
target_dir = out / "reports" / "event-alert-review-20261016" / "merged_pilots_private"
target_dir.mkdir(parents=True, exist_ok=True)
for name in ("cloudflare_replay_usage_journal.json",):
    if (private / name).exists():
        shutil.copy2(private / name, target_dir / name)
for name in ("fallback_cloudflare_rebalanced_core", "fallback_gemini_rebalanced_core_gemini-3.5-flash-lite"):
    origin = private / name / "replay_state.json"
    target = target_dir / name / "replay_state.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origin, target)
plan = {"deadline_utc": (datetime.now(timezone.utc)+timedelta(hours=72)).isoformat(),
        "candidates": [["cloudflare","rebalanced_core",None],
                       ["gemini","rebalanced_core","gemini-3.5-flash-lite"],
                       ["gemini","global_prior_no_family","gemini-3.5-flash-lite"]]}
(target_dir / "vps_bounded_plan.json").write_text(json.dumps(plan, indent=2)+"\n")
env = dotenv_values(root / ".env")
keys = ("CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID","CLOUDFLARE_MODEL","GEMINI_API_KEY","GEMINI_MODEL")
if not all(env.get(k) for k in ("CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID","GEMINI_API_KEY")):
    raise RuntimeError("Provider credentials absent")
secrets = out / "secrets"
secrets.mkdir(parents=True)
lines = []
for k in keys:
    value = env.get(k)
    if value:
        if any(ch in value for ch in "\r\n\0"):
            raise ValueError("Unsafe env value")
        lines.append(k+"="+value)
(secrets / "provider.env").write_text("\n".join(lines)+"\n", encoding="utf-8")
with (out / "src.tar").open("wb") as archive:
    subprocess.run(["git","archive","--format=tar","HEAD","bot","scripts"],cwd=root,stdout=archive,check=True)
print(json.dumps({"staging":str(out),"archive_bytes":(out/"src.tar").stat().st_size,
                  "cases_bytes":(data/"v2_private_sanitized.json").stat().st_size,
                  "deadline_utc":plan["deadline_utc"]}))
