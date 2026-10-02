# Event Alert render schema hotfix

## Problem

Production after the two-stage Event Analysis rollout showed that significance decisions were now
working, but positive decisions could be lost in the render stage. Groq returned schema/JSON
validation failures for some render calls while fallback providers also failed independently.

The render stage still reused the full ten-field Event Analysis schema even though significance had
already fixed `symbol`, `should_alert=true`, `confidence`, and
`reason_for_no_alert=null`.

## Goal

Reduce render-stage schema/output complexity without changing Event Alert significance, factual
grounding, news policy, cooldown, recipient eligibility, or delivery behavior.

## Contract

The render LLM returns only:

- `event_key`
- `title`
- `message_body`
- `related_news_ids`
- `possible_action`
- `urgency`

The backend deterministically supplies the already-decided fields:

- `symbol`
- `should_alert=true`
- `confidence` from the significance decision
- `reason_for_no_alert=null`

The materialized result must still pass the existing full Event Analysis factual/news validation
before any market event or delivery can be created.

## Acceptance

- Groq structured output uses the dedicated minimal render schema.
- Render prompt does not ask the model to repeat significance fields.
- Existing grounding/news-only/cooldown/delivery behavior is unchanged.
- Regression tests prove a six-field render result becomes a valid positive Event Analysis decision.
- Full test suite and CI pass.
