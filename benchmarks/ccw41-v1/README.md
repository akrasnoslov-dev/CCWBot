# CCW-41 Reviewer C offline audit

This protocol supports a third, exploratory, blinded significance review of the existing frozen
200-case Event Alert benchmark. Reviewer A remains authoritative. Reviewer C is not adjudicated
truth, and no majority vote may relabel the benchmark or alter production behavior.

All commands are offline. Use only the canonical local, gitignored files under
`reports/event-alert-review-20261016/`; never commit packets, mappings, results, or case-level
reports. Preparing packets performs no model call. Sending sanitized packets to any model requires
owner approval for that exact interface, data transfer, and any spend.

## Prepare frozen blind packets

```powershell
.\.venv\Scripts\python.exe scripts/ccw41_reviewer_c_audit.py prepare `
  --benchmark reports/event-alert-review-20261016/v2_private_sanitized.json `
  --reviewer-a reports/event-alert-review-20261016/reviewer_A_significance_for_pr1.json `
  --reviewer-b reports/event-alert-review-20261016/reviewer_B_significance_for_pr1.json `
  --private-dir reports/event-alert-review-20261016/ccw41_private `
  --seed ccw41-reviewer-c-v1 --batch-size 20
```

The command validates dataset and reviewer fingerprints, exact 200-case/50-per-symbol coverage,
Reviewer A's 41/112/47 split, and all 99 preserved A/B conflicts. It writes deterministic opaque
packets, a private mapping, and frozen prompt/schema fingerprints. Model-visible packets omit human
labels, bot/provider decisions, generated message copy, source analysis IDs, and technical identity
hashes while retaining the original market, timing, prior-event movement, and ordered news evidence.

## Review and import

Use a fresh review context that has never seen A/B labels or comparison reports. Give it only
`operator_prompt.md`, `reviewer-c-result.schema.json`, and one `packets/batch_NN.json` at a time.
Save each response as `results/batch_NN.json`. Record verified model/interface/reasoning identity,
approval context, request errors, and measured token/cost data when exposed in a private metadata
JSON file.

```powershell
.\.venv\Scripts\python.exe scripts/ccw41_reviewer_c_audit.py import-results `
  --private-dir reports/event-alert-review-20261016/ccw41_private `
  --results-dir reports/event-alert-review-20261016/ccw41_private/results `
  --run-metadata reports/event-alert-review-20261016/ccw41_private/run_metadata_input.json
```

Partial imports are resumable and immutable. Conflicting retries, duplicates, unknown IDs, wrong
hashes, invalid enums, nonexistent evidence paths, and incomplete ambiguous explanations fail
closed. The final record seals only at exactly 200 unique validated results with run metadata.

## Compare only after sealing

```powershell
.\.venv\Scripts\python.exe scripts/ccw41_reviewer_c_audit.py compare `
  --private-dir reports/event-alert-review-20261016/ccw41_private
```

This verifies the original source file hashes before unblinding, then writes a private discrepancy
report and an aggregate-only summary. Pairwise confusion tables include all three warrant values and
explicit denominators. Cohen's kappa is descriptive only. Outputs remain exploratory and cannot
change Reviewer A, CCW-16/29 scoring, production prompts, or alert behavior without a separately
approved protocol revision.
