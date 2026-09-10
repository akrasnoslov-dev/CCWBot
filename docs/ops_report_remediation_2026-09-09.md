# Operations Report Remediation — 2026-09-09

## Purpose

This dated investigation records the conclusions and remediation for the five areas raised by the
production operations report. Canonical behavior remains in `docs/development.md`,
`docs/observability.md`, `docs/llm_usage.md`, and `docs/ops_agent_service.md`.

## Production Baseline

A fresh read-only two-hour production bundle was collected before making changes. It completed all
63 collectors. Twenty-three detectors were clear and one detector triggered: Premium/payment
consistency. All five current Event Analysis operations succeeded, no provider incidents or Event
Alert delivery failures appeared, and nine sampled logical LLM operations reconciled to durable
outcomes. Eleven similar-context decisions were reused.

The baseline proves that current Event Analysis, Market Heartbeat, and report operations already
carry correlation IDs. It does not validate code that has not yet been deployed.

## Conclusions and Changes

### Premium/payment consistency

The reported expired `status='active'` rows are normal natural-expiry state, not entitlement
leaks. Runtime access is granted only while `active_until > now`; expired users cannot receive
Premium-only coin delivery. The ops query incorrectly treated lifecycle status as current access.

The detector now flags only an active row with a missing expiry and uses the same strict boundary
as runtime (`>` active, `<=` expired). A regression test pins expired-active access denial.

### Event identity and cooldown

The ETH key churn statistic did not prove weak identity. Distinct semantic families can correctly
produce distinct keys, and backend canonicalization already normalizes common ETH variants. The
weak-identity detector now requires suspicious keys or same-content key splitting.

The GRAM cooldown warning was partly an observer gap: durable allowed-repeat reasons were omitted
from similarity evidence, forcing an incomplete urgency/movement inference. The collector now
retains safe decision reasons and recognizes direction reversal, market-structure change, and
cumulative strengthening. Runtime regressions cover ETH and GRAM canonicalization, suppression,
and allowed cumulative strengthening.

### LLM reliability and correlation

The report combined provider-attempt failures with terminal product failures. Provider rate
limits, fallback attempts, backoff skips, and terminal outcomes are now reported separately. The
detector no longer states that correlation is absent; it uses uncapped reconciliation and coverage
aggregates and triggers on proven gaps or missing operation IDs.

News Intelligence now shares one operation UUID across router attempts and stores a sanitized
terminal outcome. Cached news records attribute the provider/model that actually answered, while a
model-aware input hash preserves cache invalidation. Hourly budget accounting covers all providers.

### User-facing alert quality

No formatter defect was found. Market-only ETH, SOL, and GRAM alerts intentionally omit the
related-news block when none exists. Regression tests verify the title/body, analyzed-window move,
possible action, and single disclaimer render without placeholders, internal labels, or an empty
news section.

### Evidence truncation and tracing

The old fixed 500-record structured-log cap could discard the majority of a busy interval. It is
removed. Every retained log file is streamed completely. Detailed records retain newest-first byte
bounds, while uncapped safe dimension counts preserve totals across retained files and truncation
remains explicit.

Event Alert logs now connect candidate crossing, LLM operation start, and terminal decision through
a sanitized context fingerprint. Bundles export only bundle-local HMAC references.

## Post-deploy Verification

After merge, backup, migration, bot deploy, and explicit ops-agent image rebuild, wait for at least
one new News Intelligence operation, then collect from the recorded UTC deploy start through now
without advancing state. Confirm Collector Status is complete and:

- Premium/payment consistency is clear unless a genuine missing-expiry row exists.
- LLM correlation and coverage evidence is present, correlated operations are greater than zero,
  and missing IDs and reconciliation gaps are both zero for new rows.
- ETH/GRAM identity and cooldown detectors do not trigger without suspicious split evidence.
- structured log metadata reports byte-bounded selection and complete dimension totals.
- no user-facing Event Alert quality regression is reported.
