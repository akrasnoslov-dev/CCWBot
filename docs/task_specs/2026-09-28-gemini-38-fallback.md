# Gemini 3.8 fallback recovery

Date: 2026-09-28

## Goal

Restore the Gemini fallback by replacing the unavailable `gemini-2.5-flash` default with the
current stable `gemini-3.8-flash` model and make the existing reasoning/budget logic treat the
new model family correctly.

Production evidence collected through the documented read-only investigator path confirmed that
`gemini-2.5-flash` returns HTTP 404 `NOT_FOUND` with a provider message that it is no longer
available to new users. No Gemini success was found in the investigated period.

Current Google documentation identifies `gemini-3.8-flash` as a stable production model,
supports structured output and thinking levels `low`, `medium`, and `high`, and maps OpenAI
compatibility `reasoning_effort` to Gemini thinking levels.

## Clarified requirements

- Change the shipped Gemini fallback default to `gemini-3.8-flash`.
- Keep `GEMINI_MODEL` override support unchanged.
- Treat Gemini 3 models as reasoning-capable for the OpenAI-compatible endpoint.
- Treat Gemini 3 models as thinking models so the existing effective-token-budget protection
  applies.
- Keep the project's existing default reasoning effort of `low`.
- Omit deprecated sampling parameters for Gemini 3.x requests. The shared provider currently sends
  `temperature=0.0`; Gemini 3.x must not receive it. Preserve existing sampling behavior for Groq,
  Mistral, and non-Gemini-3 models.
- Add regression coverage for model resolution, reasoning effort, effective token budget, and the
  provider request payload.
- Update canonical docs/examples that still describe the shipped Gemini 2.5 default.

## Out of scope

- No production environment edits or deployment.
- No Groq provider order, model, token budget, quota, retry, breaker, or routing changes.
- No Mistral model or quota changes.
- No Daily Report structured-output redesign.
- No changes to Event Alert, Premium, watchlist, recipient, payment, or delivery behavior.
- No database/schema/migration changes.
- No new dependency.

## Acceptance criteria

- With `GEMINI_MODEL` unset, Gemini resolves to `gemini-3.8-flash`.
- Existing explicit `GEMINI_MODEL` overrides still win.
- `gemini-3.8-flash` receives `reasoning_effort="low"` by default and honors existing
  per-call/global low/medium/high overrides.
- `gemini-3.8-flash` receives thinking headroom through the existing effective budget path.
- Non-reasoning models continue to omit `reasoning_effort`.
- Gemini 3.x requests omit `temperature`; Groq, Mistral, and Gemini 2.5 requests keep the existing
  `temperature=0.0` behavior.
- Focused tests fail before implementation and pass after implementation.
- Full repository verification is green before merge readiness is claimed.
- PR remains against `dev`; no merge or production deploy is performed without explicit approval.

## Expected files/areas

- `bot/services/llm/config.py`
- `bot/services/llm/base_provider.py`
- `bot/services/llm/gemini_provider.py`
- `tests/test_llm_config_budgets.py`
- `tests/test_llm_router.py`
- provider payload tests if needed
- `.env.example`
- `README.md`
- `docs/llm_usage.md`

## Risks

- Gemini 3 thinking is level-based rather than the Gemini 2.5 fixed thinking-budget interface.
  Google documents that max output tokens include thought tokens, so the existing headroom
  protection remains necessary; this task does not attempt to invent a new dynamic token formula.
- A broad model-name marker could accidentally classify unrelated models. Use a Gemini-family marker
  narrow enough to match current Gemini 3 model IDs without changing arbitrary custom providers.
- Production may explicitly override `GEMINI_MODEL`; a code default change alone does not replace
  an explicit production env value.
- Google's Gemini 3.8 migration guide explicitly requires removing `temperature`, `top_p`, and
  `top_k`. CCWBot currently sends only `temperature`; the fix must be model/provider-specific so
  Groq and Mistral behavior does not drift.

## Migration / data impact

None. No database schema, migration, persisted data, or production configuration is changed by this
PR.

## Proposed decomposition

1. Restore the shipped Gemini model default and reasoning/thinking capability detection.
2. Make sampling parameters provider/model-specific so Gemini 3.x omits deprecated sampling
   controls without changing Groq, Mistral, or Gemini 2.5 request behavior.
3. Keep provider request-shape regressions and call-type budget/reasoning tests as executable
   contracts.
4. Update canonical LLM documentation and configuration examples.
5. Complete routed review plus a bounded live Gemini smoke before merge readiness.

## Test strategy

1. Add regression expectations for the new default and Gemini 3 reasoning/thinking behavior first.
2. Confirm those expectations fail against the old implementation.
3. Add a provider-payload regression proving Gemini 3.x omits `temperature` while Groq, Mistral,
   and Gemini 2.5 retain `temperature=0.0`; confirm the Gemini 3 expectation fails first.
4. Implement the smallest provider/model-specific request-shaping change plus docs.
5. Run focused LLM config/router/provider tests.
6. Run repository-required lint, compile, full pytest, and Compose validation.
7. Complete self-review and required routed review agents before marking the PR ready.
8. Run a bounded live Gemini smoke only from a secure local environment with an existing Gemini key;
   do not expose credentials or use production/user data.
