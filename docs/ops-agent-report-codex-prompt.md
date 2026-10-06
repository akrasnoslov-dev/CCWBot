# CCWBot Ops-Agent Report Analysis

Use `docs/ops_agent_service.md` for production access, safety, bundle publication, partial-bundle,
and report-success rules. This document owns evidence interpretation and final report shape.

## Goal

Write one concise English Markdown operational report from the sanitized published bundle.
Do not apply fixes or change production while generating the report.

## Preflight

Analyze only a published directory under `reports/ops-agent/bundles/` with `manifest.json`.
Never analyze `.in-progress/`.

If collection stdout/exit status is unavailable, recover the result with:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --status latest
```

The manifest is authoritative for bundle status, period, collector status, and file inventory.

## Token-efficient reading contract

Mandatory first read only:

1. `manifest.json`
2. `decision_report_context.md`

Do **not** preload `CODEX_INSTRUCTIONS.md`, `bundle_summary.md`,
`detectors/detector_summary.md`, `detectors/detector_results.json`,
`redaction_report.json`, `limits.json`, or `evidence/**`.

After the two mandatory files:

- identify triggered/unknown findings, collection gaps, and explicit investigation questions;
- open only evidence paths referenced by those items;
- inspect additional sanitized evidence only when needed to prove/disprove a material conclusion;
- do not inspect healthy evidence streams merely to restate that they are healthy;
- stop reading once the report decision is supported.

Detector results are leads. Verify material triggered findings against referenced sanitized evidence
before calling a root cause confirmed.

## Evidence rules

Use period-matched DB/log evidence as strongest period evidence. Tail-context logs are supporting
context only and cannot alone prove a period-specific incident.

Classify every material conclusion as:

- **Confirmed** - direct evidence proves it.
- **Likely** - evidence strongly supports it but a causal link remains unproven.
- **Unknown** - evidence is insufficient.

Never turn inaccessible evidence into "missing production evidence".

If the manifest is partial, continue with unaffected evidence, list every non-ok collector, state
the sanitized reason when available, and lower confidence only where the missing evidence matters.
`unknown` is not healthy.

## Event Alert invariants

Keep pipeline stages separate: market-event generation, candidate crossing, pre-LLM reuse,
suppression/cooldown, LLM decision, event creation, recipient eligibility, and delivery.

Preserve:

```text
1 coin market event = 1 AI analysis = many alert deliveries
```

Recipient Premium/watchlist filtering can explain no delivery to a recipient; it cannot by itself
explain why no market event was generated. News is supporting context, not a standalone market-event
trigger unless current repository behavior explicitly says otherwise.

Do not recommend threshold, suppression, reuse, gating, prompt, identity, or delivery changes unless
sanitized evidence shows current behavior is wrong.

## Investigation questions

Answer each supplied question explicitly. For each, give the conclusion, evidence, confidence,
missing evidence if any, and next action. Do not manufacture a root cause.

## Final report format

Default target: **800-1500 words**. Expand only when an investigation genuinely requires it.

```markdown
# CCWBot Operational Report

## Executive Summary
Status: healthy / needs attention / degraded
Top issue: ...
Affected users: ...
Next action: ...

## Coverage
- Window: ...
- Bundle: ...
- Bundle status: ...
- Collection gaps: ...

## Findings
| Severity | Confidence | Finding | User impact | Evidence | Action |
|---|---|---|---|---|---|

## Operational Metrics
| Metric | Value | Notes |
|---|---:|---|

## Investigation Questions
<!-- Include only when supplied. -->

## Limitations / Evidence Gaps

## Evidence References
```

Rules:

- put each finding in one place; do not repeat it in separate Confirmed/Likely/Severity sections;
- express confidence in the Findings table;
- omit healthy/default detail unless it changes the operator decision;
- use percentages beside counts when a meaningful denominator exists;
- use sanitized paths/refs, never raw evidence dumps;
- if there are no findings, say the available evidence is healthy and keep the report short;
- do not restate repository rules in the report;
- do not include implementation prompts.

## Report completion

Save only under `/opt/CCWBot/reports/ops-agent/reports/`.

Follow `docs/ops_agent_service.md` for report-success state. Never advance report-success state
when the operator has explicitly prohibited it, when the report was not written, or when the bundle
is not certifiable.
