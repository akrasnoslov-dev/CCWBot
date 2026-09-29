# Task: Free-tier LLM resilience, report schema hardening, and config drift

Date: 2026-09-29

## Goal

Keep CCWBot's LLM runtime aligned with the project's zero-cost/free-tier constraint, harden Daily/Weekly Market Report structured output on Groq, and prevent stale model overrides from drifting away from pinned repository defaults.

## Clarified requirements

- CCWBot development/runtime should strive to remain free; do not make paid LLM/API subscriptions or billing-enabled tiers a requirement without explicit owner approval.
- Do not change the Event Alert model in this task. Current Groq free-tier limits and model lifecycle must be evaluated separately before any model switch.
- Harden Market Report calls so supported Groq models use strict JSON Schema, while Gemini/Mistral and unsupported Groq models retain JSON Object Mode.
- Keep application-level Market Report validation after provider-side structured output.
- Make repository defaults authoritative by default: model env variables should be optional overrides, not pinned template values that silently outlive code defaults.
- Production `.env` remains operator-owned and is not committed; stale production overrides must be removed during deployment.

## Out of scope

- Purchasing/upgrading any LLM provider tier.
- Changing Event Alert significance/business logic, cadence, cooldowns, or recipient behavior.
- Changing provider order.
- Changing the Groq Event Analysis model without a separate evidence-backed quality/capacity task.
- Direct production deployment or editing the production `.env` from this repository task.

## Acceptance criteria

- Canonical project context states the free-tier/no-required-paid-LLM constraint.
- Groq Daily/Weekly/Market Report requests use strict JSON Schema on verified strict-schema Groq models.
- All report fields required by application validation are also required by the provider schema; nested coin-card fields are required and extra properties are disabled.
- Gemini/Mistral fallback behavior remains JSON Object Mode.
- Unsupported/custom Groq report models remain JSON Object Mode.
- `.env.example` leaves Gemini/Mistral model IDs as commented optional overrides so code defaults stay authoritative.
- LLM documentation explains the no-cost constraint, strict report schema behavior, and stale-env-override drift handling.
- Focused regression tests cover the report response-format behavior.
- Required repository verification is green before merge readiness is claimed.

## Expected files

- `docs/project_context.md`
- `docs/llm_usage.md`
- `.env.example`
- `bot/services/ai_agent_groq.py`
- `tests/test_ai_agent_groq.py`

## Risks

- A strict schema unsupported by the provider/model would turn a report call into a deterministic request error. Guard it with the existing verified-model allowlist and retain JSON Object Mode elsewhere.
- Over-constraining semantic content in the provider schema could reject otherwise valid daily/weekly reports. Keep semantic rules in existing application validation; use the provider schema primarily for shape/completeness.
- Removing template model overrides does not alter an already-deployed production `.env`; deployment must remove stale overrides explicitly.

## Migration / data impact

None. No database/schema migration.

## Test strategy

- Add focused tests that fail before implementation because Market Report currently sends JSON Object Mode to Groq.
- Verify strict Groq report schema contains all required top-level and coin-card fields.
- Verify a custom/unsupported Groq report model still receives JSON Object Mode.
- Run focused LLM tests and repository-required verification/CI.
