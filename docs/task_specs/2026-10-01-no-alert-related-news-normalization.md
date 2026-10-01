# No-alert related-news normalization

## Goal

Eliminate harmless Event Analysis schema failures where the LLM correctly returns `should_alert=false` but also returns a non-empty `related_news_ids` array.

## Production evidence

After the 2026-09-30 Event Analysis grounding/token release, 120 production Event Analysis operations contained 3 Groq schema errors (2.5%). The sample error was:

`related_news_ids must be null or empty for no-alert result`

The same sample retained the target token budget, so this task is intentionally narrow and does not alter prompt size, model/provider routing, cadence, significance logic, or grounding rules.

## Requirements

- For `should_alert=false`, treat any JSON array in `related_news_ids` as non-delivery metadata and normalize it to `[]`.
- Continue accepting `null` as `[]`.
- Continue rejecting malformed non-array/non-null values.
- Do not weaken related-news validation for `should_alert=true`; alert results must still reference only supplied candidate news IDs.
- Do not change factual market validation, significance logic, provider order, models, cadence, cooldown, dedupe, delivery, or database schema.

## Expected files

- `bot/alerting/event_analysis.py`
- `tests/test_event_analysis_validation.py`

## Edge cases

- no-alert + known news ID list -> normalize to `[]`;
- no-alert + unknown news ID list -> normalize to `[]` because no alert is delivered and the field is discarded;
- no-alert + `null`/empty list -> unchanged;
- no-alert + wrong JSON type -> still reject;
- alert + unknown news ID -> still reject.

## Test strategy

1. Add failing regressions for no-alert non-empty news arrays.
2. Implement the smallest validator change.
3. Run repository CI and inspect the final diff/review threads.

## Risk / rollback

Risk is limited to accepting otherwise valid no-alert outputs that contain unused news IDs. The normalized decision still persists `related_news_ids=[]`. Rollback is a code revert; no data migration is required.
