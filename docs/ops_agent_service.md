# Ops-Agent Service

`ops-agent` is an on-demand diagnostic bundle collector for CCWBot production operations.
It helps Codex produce an English Markdown operational report from sanitized evidence.

## Boundaries

- Runs only when invoked.
- Does not use an LLM.
- Does not write the final report.
- Does not apply fixes.
- Ops-agent/report PRs are observability-only unless the task explicitly asks for runtime changes.
- Does not expose a public port.
- Does not mount the Docker socket.
- Does not provide raw SQL or shell execution.
- Uses a read-only PostgreSQL role for DB evidence.

Generated bundles and reports are operational artifacts and must stay out of Git.

After ops-agent code changes, production deploy requires explicitly rebuilding the `ops-agent`
Docker image. A normal bot-only deploy is not enough to prove the collector image changed.

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

If a bundle or report is partial, include `Collector Status` in the report and list every failed
or partial collector. Missing evidence, skipped evidence, and detector `unknown` states are not
healthy evidence; describe them as gaps and lower confidence for affected findings.

## Event Alert Regression Section

Generated decision context includes `## Event Alert Regression Checks`. The section is Markdown-only
and summarizes:

- duplicate attached successful Event Alert analyses for one market event;
- same-family Event Alerts delivered inside cooldown without escalation evidence;
- same-family repeats allowed by urgency increase, material analysed-window movement increase, or
  another market-context reason;
- pre-LLM similar-context reuse counts by symbol and semantic family;
- same-family or same-news repeats suppressed before the Event Analysis LLM;
- delivered repeats that were allowed only because of news, which should be treated as a
  regression after PR2;
- `should_alert=true` analyses with no sent delivery and no persisted suppression, cooldown,
  failure, rate-limit, filtered, not-scheduled, or no-recipient outcome;
- user-facing Event Alert placeholders such as `n/a`, `unknown`, `unavailable`, or `null`;
- old/confusing percentage labels such as `Since last BTC alert`, `Analysed-window change`, and
  generic `Price change`.

Generated decision context also includes `## Decision Reasons`, based on sanitized
`alert_delivery_outcomes` fields. It reports counts for `news_only_rejected`, `llm_no_alert`,
`semantic_cooldown_suppressed`, `similar_context_reused`, pre-LLM similar-context skips,
`allowed_market_context_changed`, delivered rows with decision reasons, missing/unknown decision
reasons, and generic `Possible action` wording as a quality metric only.

An `OK` status means none of those regressions were found in collected evidence. `Warning` means
likely same-family repeat noise needs review. `Critical` means a core invariant, observability, or
user-facing copy regression was found.

## Safety Rules

- Do not paste raw bundle JSON, logs, Telegram text, IDs, usernames, payment IDs, charge IDs,
  invoice payloads, LLM prompts/outputs, secrets, database URLs, or private identity maps.
- Use redacted refs only when user-specific remediation is necessary.
- Treat detector `unknown` as missing or inconclusive evidence, not healthy status.
- Treat missing collector evidence as incomplete, not as proof that the system is healthy.
- Do not download generated bundles or reports into the repo worktree. If temporary local
  copies are unavoidable, place them under `.cache/tmp` and clean them up.

## Forensic Correlation Evidence

`evidence/db/llm_operation_reconciliation.json` groups provider attempts by the opaque logical
operation reference and joins them to a final Event Analysis, Market Heartbeat, or market-report
row when both sides retain the correlation field. Historical `NULL` values and failed telemetry
writes are inconclusive, not successful operations.

`evidence/logs/pattern_counts.json` retains aggregate counters and adds strict allowlisted match
records. They contain only timestamp/scope, pattern/category, safe event/call/provider/model/
symbol/status/reason fields, and a bundle-local operation reference when logged. They never
contain raw or redacted log lines, user text, IDs, prompt/output, exception bodies, headers, or
credentials.

Similarity groups include HMAC-derived membership references for recipient, delivery, event,
analysis, and outcome status. They are stable only inside the current bundle and allow a report to
distinguish repeated recipient delivery, distinct recipients, multiple events, and suppressed
outcomes without exposing source IDs. Similarity remains evidence, not proof of duplication.

## Local References

- Current operator runbook: `ops-agent/README.md`
- Report-writing prompt: `docs/ops-agent-report-codex-prompt.md`
- Read-only SQL snippets: `docs/observability.md`
