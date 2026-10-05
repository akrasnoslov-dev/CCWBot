# Production diagnostic fixes - 2026-10-05

## Goal
Fix the four confirmed issues from production diagnostics: stale scheduled market reports, persistent Event Analysis no-alert calibration, missing exact movement evidence in sanitized ops bundles, and false-positive similarity findings from no-alert analyses.

## Requirements
- Preserve LLM-owned Event Alert significance; no deterministic numeric alert thresholds.
- Preserve market-event-first, news-not-standalone, exact-context reuse, strict 4h semantic cooldown, recipient and delivery invariants.
- Scheduled report refresh must remain global and must not add unnecessary market/LLM generation.
- Sanitized evidence may expose numeric market movement/context only; never raw prompts, raw model output, secrets, recipient identifiers, or raw input JSON.
- Similarity detector must not flag repeated no-alert analyses with zero market events/deliveries as user-facing alert noise.
- No production deployment in this task.

## Root-cause hypotheses to verify
1. Report scheduler repeats at the cache TTL and is anchored to container startup; after a restart it can skip a still-fresh cache and wait another full TTL, allowing staleness.
2. Significance prompt remains too weakly calibrated after the 2026-10-02 compact-prompt fix and can default to conservative no-alert decisions despite model-visible relative-move evidence.
3. Alert repetition SQL does not project no-alert analysis movement values from persisted raw input into sanitized structured fields.
4. similar_alert_groups detector triggers on raw similarity groups even when should_alert_true=0 and market_events/deliveries=0.

## Acceptance criteria
- Scheduler checks often enough that restart phase cannot create a stale gap; generation still occurs only near/after expiry.
- Significance prompt explicitly treats market movement alone as sufficient evidence when noteworthy, uses relative context when present, and forbids defaulting to no-alert because news is absent, without numeric gates.
- Decision timeline exposes analysed-window, 24h, and relative percentile fields for no-alert analyses.
- Similarity detector ignores groups with no repeated positive alert decisions/user-facing events.
- Focused regressions fail before implementation and pass after.
- Relevant suites and repository-required verification pass.

## Expected areas
- bot/alerts.py
- bot/services/ai_agent_groq.py
- ops-agent/ops_agent/collectors/db.py
- ops-agent/ops_agent/alert_similarity.py
- ops-agent/ops_agent/detectors.py
- focused tests and canonical docs if behavior text needs clarification

## Risks
- Too-frequent scheduler checks must not cause extra LLM/CoinGecko generations.
- Prompt calibration must not become a hidden deterministic threshold.
- Ops evidence must remain sanitized.
