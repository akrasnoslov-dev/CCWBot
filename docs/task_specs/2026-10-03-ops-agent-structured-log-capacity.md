# Ops-agent structured log export capacity

## Problem

Production bundle `20261003T172117Z_cc57fa09` matched 16,389 period records but exported only 8,653. The export consumed about 2.15 MB even though the configured total structured-record budget was 8 MB. The binding limit was the 2 MB per-file cap because the current production period was concentrated in one operational log source.

## Goal

Allow a single retained log source to use the full existing 8 MB structured-record export budget while keeping the existing total cap and 25 MB bundle hard cap.

## Requirements

- Keep full-file scanning unchanged.
- Keep newest-record retention unchanged.
- Keep aggregate/dimension counts uncapped and unchanged.
- Change the default per-file structured-record export cap from 2 MB to 8 MB, matching the existing total cap.
- Preserve environment overrides for both caps.
- Surface both structured-log byte caps in `limits.json`.
- Add a sanitized `event_alert_render_validation_reason_summary` aggregate that classifies the
  existing `llm_usage_logs.error_message` into fixed reason categories without exporting raw error
  messages. This permits historical render failures to be diagnosed after the updated ops-agent is
  deployed.
- Do not expose raw logs or broaden the allowlisted structured record fields.
- Do not change DB collectors, detectors, or runtime bot behavior.

## Out of scope

- Increasing the 8 MB total structured-log budget.
- Increasing the 25 MB bundle hard cap.
- Changing redaction or raw-log policy.
- Production deployment/rebuild.

## Test strategy

- Regression test proves the default per-file cap can consume the total 8 MB budget.
- Existing custom-cap tests continue proving per-file and total limits are enforced.
- Focused ops-agent suite must pass.
- Full repository tests remain green.

## Acceptance criteria

- Default per-file cap equals the existing 8 MB total cap.
- Custom environment/config overrides still work.
- `limits.json` reports both configured structured-log byte caps.
- No raw log content is added to bundles.
