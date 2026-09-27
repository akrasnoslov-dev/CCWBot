# Onboarding analytics and release follow-up

## Goal

Correct the direct Telegram Ads measurement contract, resolve PR #245's P1 review thread, obtain
review evidence for the Graphify payload already in `dev`, and release `dev` to `main` only when
the complete payload meets repository gates.

## Clarified requirements

- Direct Telegram Ads accepts `t.me/YFCCWbot` but rejects the `?start=a1_<code>` parameter, so it
  does not produce CCWBot source/campaign/creative attribution.
- Measure an observed new-user cohort during the UTC half-open Ads window with
  `users.created_at >= :experiment_start` and `< :experiment_end`. It is not exactly attributed:
  organic users may be included.
- Count a downstream event only when it is on/after that user's creation time. Immediate metrics
  must also occur before `:experiment_end`; delayed metrics must be labelled within-window or use
  a separately stated follow-up horizon.
- The previous 25% is active progression to a brief; v2 completion is automatic first-value
  delivery. Compare downstream interaction/conversion events rather than treating these as the
  same engagement metric.

## Scope and non-goals

- Update canonical analytics documentation and add a documentation/query-contract check if one is
  meaningful. Resolve the valid PR #245 thread after the change.
- Review PR #244's Graphify developer-tooling payload against required routing gates.
- Correct the valid Graphify release findings: remove its ineffective global hook and unportable
  merge-driver declaration, and make package installation and external semantic extraction
  explicitly opt-in.
- No runtime analytics behavior, schema migration, event expansion, payment, attribution, alert,
  entitlement, or deployment change.

## Validation

1. Test the documentation query contract for the cohort source, half-open bounds, event ordering,
   and metric interpretation before updating the document.
2. Run focused and repository-required verification.
3. Obtain growth-analytics reviews plus the required Graphify/release-payload review evidence.
4. Review the full `origin/main...origin/dev` diff before creating a release PR.
