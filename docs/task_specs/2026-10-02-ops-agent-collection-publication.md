# Ops-Agent Collection Publication Reliability

## Goal

Make production ops-agent collection failures unambiguous and recoverable without weakening the existing read-only production access model.

## Confirmed failure

`BundleWriter.initialize()` currently creates the final public bundle directory and writes `CODEX_INSTRUCTIONS.md` before collection starts. If the process is interrupted or finalization fails before `manifest.json` is published, a directory can remain under `bundles/` even though it is not a valid bundle. The current root wrapper also `exec`s the collector, so no durable sanitized terminal result remains when SSH/task tooling loses stdout or the exit code.

The exact trigger of the observed production interruption is unknown.

## Requirements

- Stage each collection under private `.in-progress/<bundle-id>` and publish to `bundles/<bundle-id>` only after the manifest is durable.
- Publication must be an atomic same-filesystem rename.
- Published bundles must remain readable through the existing `ccwbot_ops` access model.
- Persist a sanitized wrapper receipt with invocation id, start/end timestamps, terminal state, exit code, and published bundle path when available.
- Never persist raw stderr.
- Support `sudo /usr/local/bin/ccwbot-ops-agent-collect --status latest` to recover the latest receipt.
- Support wrapper-only `--since-container-start`; resolve only the fixed `ccwbot` container's `StartedAt`, normalize it to UTC, and pass it to the collector as `--since`.
- Keep the 720-hour collection cap unchanged. If container start would exceed it, fail before collection, persist a sanitized failure receipt, and do not silently clamp the period.
- Reject staged paths from bundle validation and report-success flows.
- Treat only manifest-bearing published directories as reportable bundles.
- Update canonical ops/report documentation and the production runbook.

## Out of scope

- Product, Event Alert, Premium, payment, or delivery behavior.
- Database writes or schema changes.
- Deployment/restart/migration behavior.
- Broad Docker access for `ccwbot_ops`.
- Extending the 720-hour collection limit.

## Acceptance criteria

- Interrupted or failed collection cannot leave an apparent bundle under `bundles/`.
- Successful collection publishes exactly one manifest-bearing bundle atomically.
- Non-zero collector exits remain recoverable from a sanitized receipt.
- `--status latest` returns the latest receipt without starting collection.
- `--since-container-start` uses only `ccwbot` StartedAt and fails safely above 720 hours.
- Staging directories are private and cannot be accepted as report-success bundle paths.
- Regression/contract tests cover staging, publication, receipts, non-zero exits, container-start handling, and staged-path rejection.

## Verification

- `ruff check` for changed Python files.
- `pytest tests/ops_agent/`.
- PostgreSQL integration tests may remain skipped when no local test DB URL is configured because this task changes no DB query.
- Full diff self-review with observability, security, test/CI, and production-deploy risk checks.
