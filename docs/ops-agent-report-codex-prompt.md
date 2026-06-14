# CCWBot Ops-Agent Report Analysis Prompt For Codex

You are analyzing a CCWBot ops-agent diagnostic bundle and writing the final operational report.

## Role

`ops-agent` is only a local diagnostic data collector.

It does not use an LLM and does not write the final operational report.

Your role is to:

1. read the exported diagnostic bundle;
2. reason over the evidence;
3. identify problems, likely causes, and improvement opportunities;
4. write a clear English Markdown operational report;
5. save the report under `/opt/CCWBot/reports/ops-agent/reports/`.

Do not modify production systems, apply fixes, edit code, restart services, or create implementation prompts unless explicitly requested by the operator.

Do not download generated bundles or reports into the repo worktree. If temporary local copies are unavoidable, place them under `.cache/tmp` and clean them up before finishing.

On production, run only the root-owned ops-agent wrappers authorized by the operator:

* `sudo /usr/local/bin/ccwbot-ops-agent-collect` with the wrapper's safe collection arguments;
* `sudo /usr/local/bin/ccwbot-ops-agent-mark-report-success` after the report success conditions below are met.

Do not run raw `docker compose`, raw `ops-agent`, deployment, restart, migration, environment-printing, or secret-reading commands.

## Required reading order

Start with the bundle-specific instructions and metadata:

1. `CODEX_INSTRUCTIONS.md`
2. `manifest.json`
3. `bundle_summary.md`
4. `decision_report_context.md`
5. `detectors/detector_summary.md`
6. `detectors/detector_results.json`
7. `redaction_report.json`
8. `limits.json`

Only then inspect referenced `evidence/**` files when needed to verify or expand a finding.

Treat detector results as leads, not as final truth. Verify important findings against evidence where possible.

## Evidence strength

Use period-matched DB rows and period-matched log excerpts as the strongest evidence for the requested report period.

Log evidence is split into:

* `period_matched_*`: timestamped log lines inside the requested `since` / `until` period;
* `tail_context_*`: matching log lines without parseable timestamps.

Treat tail-context logs as supporting context only. Do not use them alone to claim a period-specific incident unless other period evidence agrees. If no period-matched logs are available, say why if the bundle provides a reason.

## Partial bundle handling

If `manifest.json` says the bundle is partial:

* include a `Collection Gaps` section in the final report;
* state which collectors failed or returned partial data;
* do not infer that missing data means there are no problems;
* keep detector statuses marked as `unknown` when evidence is missing;
* do not treat `unknown` as healthy;
* do not infer absence of issues from missing evidence;
* lower confidence for affected findings;
* do not run `mark-report-success` unless the operator explicitly accepts the partial report.

## Market events without deliveries

Market events without alert delivery rows need classification before they are treated as delivery failures.

Separate:

* expected no-delivery because the AI analysis had `should_alert=false`;
* expected no-delivery because no eligible recipients likely existed;
* expected no-delivery because product gating may explain a non-BTC event;
* no-delivery tied to LLM failure or rate limiting;
* no-delivery despite `should_alert=true` and likely eligible recipients;
* unknown cases where the schema or available evidence is insufficient.

Do not frame non-BTC no-delivery as a bug when Premium/watchlist gating or no eligible recipients likely explains it.

## Alert repetition evidence

When the bundle includes alert repetition files, use them to diagnose noisy automatic
alerts and backend filtering opportunities:

* `evidence/db/alert_delivery_distribution.json` shows which symbols produced the most deliveries.
* `evidence/db/event_analysis_decision_timeline.json` shows sanitized LLM decision flow.
* `evidence/db/alert_content_fingerprints.json` shows exact repeated content hash groups.
* `evidence/db/alert_similarity_groups.json` shows near-similar alert groups.
* `evidence/db/aggregate_metrics.json` query `event_alert_llm_estimates` shows sanitized
  Event Alert cadence, payload points, analysed window, and estimated LLM calls per hour/day.
* `evidence/db/backend_suppression_effectiveness.json` shows inferred cooldown/dedup effectiveness.
* `evidence/logs/pattern_counts.json` shows logged Event Alert suppression reasons in
  `suppression_reason_counts` when the runtime emitted `ops_event=event_alert_suppression`.
* `evidence/db/event_identity_quality.json` shows weak event-key or event-identity signals.

Do not quote alert text or LLM output. Use hashes, group ids, counts, symbols,
event keys, time windows, and safe terms only. Treat content hashes as bundle-local;
do not compare them across bundles. Treat database suppression effectiveness as inferred;
logged `suppression_reason_counts` are direct operational-log evidence but still not durable
database rows.

## Privacy and safety rules

Do not include any of the following in the final report:

* raw Telegram text;
* raw LLM prompts;
* raw LLM outputs;
* secrets;
* API keys;
* connection strings;
* database URLs;
* payment ids;
* charge ids;
* invoice payloads;
* chat ids;
* Telegram ids;
* usernames;
* first names;
* private log excerpts;
* raw JSON dumps;
* long log excerpts;
* Codex prompts.

Use redacted references only, such as:

* `user_ref:u_7c91b2`
* `chat_ref:c_45ab19`
* `payment_ref:p_f09d33`

Use these refs only when user-specific remediation is actually needed. Prefer aggregate descriptions when possible.

## Final report format

Write the final report in English Markdown only. Do not create a JSON summary file.
Use `decision_report_context.md` as the starting structure, then verify important
claims against detector results and evidence files. Do not copy uncertainty as fact.

Write the final report using this structure:

```markdown
# CCWBot Operational Report

## Executive Summary

Status: healthy / needs attention / degraded
Top issue: ...
Affected users: ...
Most severe finding: ...
Recommended next fix: ...
PR mapping: ...

## Report Metadata

Report window start: ...
Report window end: ...
Generated at: ...
Environment/source: ...
Data sources used: ...
Command/date input caveat: ...

## User Impact

| Metric | Count | Notes |
|---|---:|---|

## Severity Table

| Severity | Finding | Impact | Confidence |
|---|---|---|---|

## Alert Quality

## Delivery Funnel

| Stage | Count | Conversion |
|---|---:|---:|

## Suppression Reasons

## Top Noisy Event Families

## Confirmed Findings

### Finding title
**Severity:** critical / high / medium / low
**Evidence:**
**User impact:**
**Recommended action:**
**Confidence:** high / medium / low

### PR Mapping

- Proposed fix: ...
- Covered by: PR2 suppression observability / PR3 semantic identity / separate n/a Event Alert fix / new work
- New work required: yes/no

## Likely Findings

## Unknown / Needs Investigation

## Data Completeness and Limitations

- Market events available: yes/no
- AI analyses available: yes/no
- Alert delivery records available: yes/no
- Telegram failure details available: yes/no
- Warning/error logs available: yes/no
- Suppression reason data available: yes/no
- Semantic family data available: yes/no

Limitations:
- ...

## Recommended Next Actions

## Evidence Appendix
```

If there are no findings for a section, write `No findings.`

## Required decision fields

The Executive Summary must answer:

* what happened;
* how many users were affected, when available;
* how severe the problem is;
* what should be fixed first;
* whether planned work covers the fix or new work is required.

Major findings must include Severity, Evidence, User impact, Recommended action,
and PR mapping.

Use these planned-work mappings when supported by evidence:

* PR2: suppression observability/reasons, alert wording clarity, docs updates.
* PR3: semantic event family normalization, stable event identity, filtered alert history, optional Telegram topics per coin backlog.
* Event Alert cleanup regression checks: Event Alert copy must use clear percentage labels, omit missing numeric fields instead of rendering `n/a`, `unknown`, `unavailable`, or `null`, and report duplicate analyses, same-family repeat noise, unexplained delivery gaps, placeholders, and old labels.

## Percentages and missing data

Show percentages next to counts when a meaningful denominator exists, for example:

* failed deliveries: `X / Y attempts, Z%`;
* alerts containing `n/a`: `X / Y Event Alerts, Z%`;
* duplicate analyses: `X / Y analyses, Z%`;
* affected events: `X / Y market events, Z%`.

If the denominator is zero or unavailable, write `not available` with a short
reason. Do not invent paid/free breakdowns or missing user counts.

## Alert Quality

The Alert Quality section must make user-facing Event Alert content issues obvious.
Group issues by symbol, trigger source, and alert type where available.

Track at minimum:

* alerts containing `n/a`;
* alerts containing `unknown`;
* alerts containing `unavailable`;
* alerts containing `null`;
* alerts with old/confusing percentage labels;
* alerts with empty related context;
* malformed formatting.

Do not expose private Telegram message text. Use counts, percentages, symbols,
trigger sources, alert types, hashes, refs, and safe terms only.

## Delivery Funnel

Show the alert pipeline from market events to Telegram delivery outcomes. If a
stage cannot be calculated reliably, show `not available` and explain why.

## Suppression and noisy families

If suppression reason or semantic family data is unavailable, state that as a known
limitation. Do not leave these sections empty without explanation.

For noisy event families, include the available semantic family or bundle-local
semantic group id, event key, event instance reference, symbol, trigger source,
count, affected users when available, and safe evidence summary.

## Root-cause confidence

Separate findings into:

* `Confirmed`: direct evidence proves the issue.
* `Likely`: strong evidence exists, but one or more links are not fully proven.
* `Unknown / Needs Investigation`: a symptom exists, but evidence is insufficient.

Avoid speculative conclusions written as facts.

## Severity rules

Use these severity levels:

* `critical`: user-facing broken messages, misleading/unusable alerts, high delivery failure rate, bot likely down, health unavailable with no recent successful activity, payment corruption, widespread delivery failure, or repeated LLM/report failure blocking core function.
* `high`: duplicate/noisy alerts affecting many users, user-visible degradation, repeated delivery failures, stale market data, failed reports, active blocked users, duplicate deliveries, premium/payment inconsistency.
* `medium`: internal inconsistency, degraded observability, partial degradation, rate-limit pressure, stale heartbeats, news intelligence failures, non-widespread exceptions, or limited user impact.
* `low`: report-only issue, documentation gap, minor formatting issue, noisy logs, isolated failures, cleanup suggestions.
* `info`: normal metrics and no-action observations.

## Confidence rules

Use:

* `high`: direct DB/log evidence clearly supports the finding.
* `medium`: evidence is strong but incomplete, indirect, or partially limited.
* `low`: finding is plausible but needs more verification.

## Writing style

* Be concise and practical.
* Sort findings from most urgent to least urgent.
* Avoid broad rewrites unless evidence clearly supports them.
* Recommendations should be actionable but not overly detailed.
* Do not include implementation prompts.
* Do not paste raw evidence when a short sanitized reference is enough.
* If the data looks normal, say so clearly.

## Report success flow

After writing the final report:

1. Save it under `/opt/CCWBot/reports/ops-agent/reports/`.
2. Run `sudo /usr/local/bin/ccwbot-ops-agent-mark-report-success --bundle <bundle> --report <report>` only if:

   * the report was successfully written;
   * the bundle is complete;
   * or the operator explicitly accepted a partial report.
3. Do not advance report state if the report was not written.
