# LLM structured output and diagnostics hardening

Date: 2026-09-28

## Goal

Reduce avoidable Groq structured-output failures for Event Analysis and Market Heartbeat, and make exhausted provider chains easier to diagnose without exposing prompts, outputs, secrets, or user data.

## Confirmed problem evidence

- Event Analysis and Market Heartbeat currently request OpenAI-compatible JSON Object Mode only.
- Groq production models `openai/gpt-oss-120b` and `openai/gpt-oss-20b` support strict JSON Schema Structured Outputs.
- `GROQ_JSON_MODE_RETRY_PLAIN` is documented but has no runtime consumer.
- Provider-attempt telemetry already persists sanitized `error_reason`, sanitized `error_message`, safe rate-limit headers, and request IDs when present.

## Clarified requirements

- Work from `dev`; target a normal PR back to `dev`.
- No production deployment, restart, environment change, model swap, or database change.
- Keep Gemini and Mistral behavior/configuration unchanged.
- Keep product decisions and validators authoritative; strict schemas may constrain transport shape only.
- Use Groq strict JSON Schema only on Groq models known to support strict mode. Unsupported/overridden Groq models keep current JSON Object Mode.
- Gemini and Mistral fallbacks keep current JSON Object Mode.
- Remove the misleading dead `GROQ_JSON_MODE_RETRY_PLAIN` documentation rather than adding another retry that could increase rate-limit pressure.
- Add only sanitized chain-level diagnostic categories; never log raw provider bodies, prompts, LLM output, credentials, IDs, or user data.

## Scope

### Runtime
- Add provider-specific response-format selection in the LLM router without changing provider order or retry count.
- Add strict JSON schemas for Event Analysis and Market Heartbeat Groq attempts.
- Preserve existing application-level validators after structured decoding.
- Add one sanitized chain-exhaustion log containing only provider names and safe failure categories.

### Documentation/config
- Remove `GROQ_JSON_MODE_RETRY_PLAIN` from `.env.example`, README, and stale explanatory comments.
- Document that current GPT-OSS Groq structured calls use strict schema where implemented and fallbacks keep JSON Object Mode.

### Tests
- Regression test provider-specific response formats: Groq can receive strict schema while Gemini fallback receives ordinary JSON Object Mode.
- Regression tests that Event Analysis and Market Heartbeat send strict schemas to supported Groq GPT-OSS models.
- Regression test that an unsupported Groq model falls back to JSON Object Mode.
- Regression test sanitized chain-exhaustion diagnostics contain categories, not raw error text.
- Existing fallback and schema-validation tests must remain green.

## Out of scope

- Changing Gemini or Mistral model identifiers.
- Changing production provider priority or environment values.
- Increasing provider quotas or account tiers.
- Changing Event Alert significance, heartbeat content rules, Premium behavior, recipient logic, or report/news schemas.
- Adding same-provider retries.

## Risks

- A strict schema that is narrower than the existing validator could change accepted output. Mitigation: model the existing transport fields/types only and leave semantic/non-empty/grounding checks in the current validators.
- A Groq model override may not support strict schemas. Mitigation: gate strict mode by a small allowlist of verified supported model IDs and keep JSON Object Mode otherwise.
- Provider-specific formatting must not leak to fallbacks. Mitigation: router test with Groq -> Gemini.

## DB / migration impact

None.

## Acceptance criteria

- Event Analysis on supported Groq GPT-OSS uses `response_format.type=json_schema`, `strict=true`, all properties required, and `additionalProperties=false`.
- Market Heartbeat on supported Groq GPT-OSS does the same.
- Gemini/Mistral fallback request shape is unchanged.
- Unsupported Groq model override uses current JSON Object Mode.
- No extra provider retry is introduced.
- Chain exhaustion emits safe categorical diagnostics only.
- Dead `GROQ_JSON_MODE_RETRY_PLAIN` documentation is removed.
- Focused tests and repository-required checks pass before merge readiness is claimed.
