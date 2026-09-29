# Task: Event Analysis token efficiency

## Goal

Reduce Event Analysis input tokens substantially without changing Event Alert decisions, cadence,
provider routing, cooldowns, or recipient handling.

## Requirements

- Base the integration on PR #255 when available; it is open and changes report-schema paths in
  `bot/services/ai_agent_groq.py`.
- Measure reconstructed pre-change versus post-change prompts using the same sanitized fixtures:
  no news, selected candidate news, and previous Event Alert context.
- Break down static instructions, serialized payload, and total input. Use the model tokenizer when
  available; otherwise label a deterministic estimate.
- Preserve full precision and all validation/grounding contracts. Do not add numeric alert gates.

## Plan

1. Keep the canonical stored Event Analysis input unchanged; build a compact, lossless model-view
   payload that excludes only runtime metadata and static policy already present in instructions.
2. Replace redundant prompt prose with compact, equivalent instructions and a field legend.
3. Version the exact-context contract so prior decisions from the former prompt are not reused;
   exclude fields omitted from the compact model view while retaining the versioned static policy.
4. Add fixture-based contract and measurement tests; run focused tests and project checks.

## Risks and validation

- Risk: compact names could obscure a market fact. Mitigate with an explicit legend and tests for
  all safety/grounding assertions, full-precision values, news, and prior-alert fields.
- No database or migration impact.
- Out of scope: model/provider/cadence/cooldown/recipient/business-logic changes.
