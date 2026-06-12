# Ops-Agent Service

`ops-agent` is an on-demand diagnostic bundle collector for CCWBot production operations.
It helps Codex produce an English Markdown operational report from sanitized evidence.

## Boundaries

- Runs only when invoked.
- Does not use an LLM.
- Does not write the final report.
- Does not apply fixes.
- Does not expose a public port.
- Does not mount the Docker socket.
- Does not provide raw SQL or shell execution.
- Uses a read-only PostgreSQL role for DB evidence.

Generated bundles and reports are operational artifacts and must stay out of Git.

## Production Access Model

Production collection should use the root-owned safe wrappers documented in
`ops-agent/README.md`:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect
sudo /usr/local/bin/ccwbot-ops-agent-mark-report-success --bundle <bundle> --report <report>
```

Do not run raw `docker compose`, raw `ops-agent`, deployment commands, restarts, migrations,
environment-printing commands, or secret-reading commands as part of normal report collection.

## Required Evidence Reading Order

For each generated bundle, read:

1. `CODEX_INSTRUCTIONS.md`
2. `manifest.json`
3. `bundle_summary.md`
4. `decision_report_context.md`
5. `detectors/detector_summary.md`
6. `detectors/detector_results.json`
7. `redaction_report.json`
8. `limits.json`

Then inspect referenced `evidence/**` files only as needed to verify or expand findings.

## Final Report Flow

1. Run the safe collect wrapper.
2. Read the printed JSON and open the bundle path.
3. Use `docs/ops-agent-report-codex-prompt.md` and `decision_report_context.md`.
4. Write the final Markdown report under `/opt/CCWBot/reports/ops-agent/reports/`.
5. Mark success only after the report exists and the bundle is complete, unless the operator
   explicitly accepts a partial report.

## Safety Rules

- Do not paste raw bundle JSON, logs, Telegram text, IDs, usernames, payment IDs, charge IDs,
  invoice payloads, LLM prompts/outputs, secrets, database URLs, or private identity maps.
- Use redacted refs only when user-specific remediation is necessary.
- Treat detector `unknown` as missing or inconclusive evidence, not healthy status.
- Do not download generated bundles or reports into the repo worktree. If temporary local
  copies are unavoidable, place them under `.cache/tmp` and clean them up.

## Local References

- Current operator runbook: `ops-agent/README.md`
- Report-writing prompt: `docs/ops-agent-report-codex-prompt.md`
- Read-only SQL snippets: `docs/observability.md`
