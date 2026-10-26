# Event Alert research archive

This is the canonical repository-backed evidence index for CCWBot Event Alert research. Use these versioned files as inputs; do **not** depend on local `D:\Projects\CCWBot\reports` or old chat attachments to recover previous experiments.

## Snapshot imported 2026-10-26

- [Historical experiment evidence](versioned_evidence_20261026/reports/): **331 original research files**, committed to `dev` at `38eb9e6756a50959d86ba69c14c17cc4965fa9f0`.
- [Original import manifest](versioned_evidence_20261026/IMPORT_MANIFEST.json): SHA-256, size and original relative path for all 426 staged files; records 331 originally copied and 95 originally excluded.
- [UTF-16 owner scoring recovery](versioned_evidence_20261026/utf16_recovered/): **2 more complete JSON reports** converted from UTF-16LE to UTF-8; source and converted SHA-256 in [conversion manifest](versioned_evidence_20261026/utf16_recovered/UTF16_RECOVERY_MANIFEST.json).
- [66 owner blind decisions and comments](owner_review_20261026/owner_blind_disagreements_66.json): original reviewed disagreement subset; includes annotations and source-case hashes.
- [Six-prompt detailed scoring](owner_review_20261026/six_prompt_scoring.json): per-prompt confusion counts, per-coin breakdown, and case-level error IDs.
- [Six-prompt assessment](owner_review_20261026/six_prompt_analysis.md) and [aggregate findings](../../docs/event_alert_owner_disagreement_20261026.md).
- [66 anonymized decision labels](owner_labels_66.csv): short machine-readable decision-only alternative to the full owner review.
- [Historical benchmark helpers](historical_helpers/): recovered original `build_review.py`, `monitor_resources.ps1` and two isolated-provider launch shell scripts. The original frozen `validation/scripts/event_alert_benchmark.py` is already tracked unchanged as `scripts/event_alert_benchmark.py`.

Frozen cohort: **200** BTC/ETH/GRAM/SOL market cases, **1,200** saved GPT-6 Luna prompt decisions (six variants), **66** owner-reviewed disagreement cases (24 alert / 34 no_alert / 8 ambiguous). The selected 58 decisive disagreements cannot establish population accuracy. Dataset SHA-256: `ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d`.

## Accounting of the original 95 exclusions

The original immutable import manifest still records 95 skipped staged files. These are now accounted for as follows:

- **90 archived duplicate application-source files** under `ccw25-20261019/dev-source/`: canonical source is already stored in this same repository at Git commit [`e0b47e4`](https://github.com/akrasnoslov-dev/CCWBot/tree/e0b47e4c95399f930a6a63554ecfe058b58d8cd5); every one of the 90 paths exists in that historical tree. The original source SHA-256 manifest is stored at [`dev_source_manifest.json`](versioned_evidence_20261026/reports/ccw25-20261019/dev_source_manifest.json). Do not duplicate source trees inside research.
- **2 UTF-16 JSON review results**: recovered in `utf16_recovered/`; original hashes retained.
- **3 machine-specific diagnostic files**: `ccw25-20261019/host_evidence.json`, `resource_samples.jsonl`, `workstation.json`. Omitted intentionally for host privacy and because hardware profiling is not required to replay saved Event Alert outcomes; filenames and SHA-256 are preserved in the original manifest.

Consequently, all **423/426** original staged files needed for durable project research or already represented by immutable Git history are now backed by this repository; the remaining three are local-machine diagnostics excluded by design. Original 10,005 generated caches/test temp files were deliberately omitted. This is an archival record, not a claim that every local scratch file is checked into Git.

## Operational notes

1. Use `dev` branch as the development research reference. `main` and production deployment do not depend on archived research evidence.
2. Historical scripts may contain obsolete local absolute paths. Their **inputs and saved evaluations** are preserved here; do not assume scripts can be rerun without adapting environment dependencies or installing old model binaries.
3. Privacy screening was heuristic, not a guarantee. Never publish credentials, real Telegram user/recipient identifiers, databases or unredacted production diagnostic bundles; do not restore the three host-specific files blindly.
4. The original `reports/` folder may be kept as local cache. When future experiments produce new durable evidence, put sanitized results directly under `research/event_alerts/`, update an inventory and commit to `dev`. Do not silently create research artifacts that exist only on someone's computer.
