# CCWBot research evidence

`reports/` is the canonical Git-tracked directory for durable CCWBot experiments.
A clean clone of branch `dev` restores the historical evidence and owner evaluations.

## Contents

- [`event-alert-review-20261016/`](event-alert-review-20261016/): historical Event Alerts tests (CCW-16/29/41/43), model ledgers and human reviews.
- [`event-alert-review-20261016/owner_review_20261026/`](event-alert-review-20261016/owner_review_20261026/): the 66 owner reviews, label table, and six-prompt scoring.
- [`ccw25-20261019/`](ccw25-20261019/): offline LLM benchmark evidence, scores and reproducibility metadata.
- [`historical_helpers/`](historical_helpers/): recovered one-off research scripts; the original `event_alert_benchmark.py` is already versioned under `scripts/`.
- [`migration/`](migration/): original scan manifest and UTF-16 conversion records.
- [`context-audit.md`](context-audit.md): research context audit.
- [`ops-agent/`](ops-agent/): historical unverified report; not live production state.

## Import accounting

The original October 26 import recorded 426 staged source files: 331 preserved
byte-for-byte under `reports/`; 2 UTF-16 JSON results restored with equivalent
JSON content; 90 duplicate old source files available in existing Git history
at commit `e0b47e4c95399f930a6a63554ecfe058b58d8cd5`; and 3 local-machine
diagnostic files intentionally excluded from the public repository.
An additional owner review and recovered helper scripts are versioned here.
See [`migration/README.md`](migration/README.md) for provenance and exclusions.

New durable research must be committed directly to `reports/` on `dev`.
Downloaded model weights, caches, raw production logs, local environment
credentials, databases and other regenerable or sensitive machine-specific
files must not be committed. Recorded results are portable, but rerunning
old experiments may require reinstalling their former dependencies.

