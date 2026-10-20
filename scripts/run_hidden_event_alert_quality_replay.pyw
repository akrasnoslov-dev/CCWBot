"""Console-free entry point for the scheduled PR349 quality replay.

Run via the project's pythonw.exe; failures remain visible in the private
launcher status file rather than vanishing with stdout/stderr.
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    status_path = (
        ROOT / "reports" / "event-alert-review-20261016"
        / "merged_pilots_private" / "quality_worker_launcher_status.json"
    )
    try:
        from scripts.auto_event_alert_quality_replay import run_once

        result = run_once()
        failure = result.get("status") in {
            "worker_error_needs_review", "private_dataset_missing",
        }
        status = {"status": "error" if failure else "completed",
                  "worker_status": result.get("status", "unknown")}
    except Exception as exc:
        failure = True
        status = {"status": "error", "error_type": type(exc).__name__,
                  "traceback": traceback.format_exc(limit=8)}
    status["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    status_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = status_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    temporary.replace(status_path)
    return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
