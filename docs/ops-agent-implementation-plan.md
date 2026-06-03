# CCWBot Ops-Agent Implementation Plan

## Purpose

`ops-agent` is a production-local diagnostic bundle collector for CCWBot. It is not the final analyst, does not use an LLM, does not write the final operational report, and does not apply fixes.

The goal is to give Codex a compact, sanitized operational evidence bundle from the production host so Codex can produce a final English Markdown report for the operator.

Hard boundaries:

* `ops-agent` runs on demand, not continuously.
* No public port.
* No Docker socket.
* No LLM calls inside `ops-agent`.
* No automatic fixes.
* No raw SQL endpoint.
* No shell execution in the normal collection path.
* No changes to bot or PostgreSQL Compose services unless strictly required.
* The bot's alert invariant remains unchanged: one market event creates or reuses one AI analysis, then many alert deliveries.

## Target Workflow

1. Operator asks Codex for an operational report for a specific period, or the default period.
2. Codex connects to the CCWBot server over SSH.
3. Codex runs `ops-agent` locally through Docker Compose.
4. `ops-agent` collects operational evidence from PostgreSQL, file logs, health/status sources, and its own state.
5. `ops-agent` sanitizes, compacts, groups, detects known issues, and exports a diagnostic bundle.
6. Codex reads the bundle according to `CODEX_INSTRUCTIONS.md` and `docs/ops-agent-report-codex-prompt.md`.
7. Codex performs final analysis and writes the final Markdown operational report.
8. Codex saves the report under `/opt/CCWBot/reports/ops-agent/reports/`.
9. Codex runs `mark-report-success` only after a report is written and the bundle is complete, unless the operator explicitly accepts a partial report.
10. Codex returns the report to the operator.

Default report period:

* If `ops-agent` state has a successful prior report, collect from that report's `period_end`.
* Otherwise collect the last 24 hours.

## On-Demand Compose Invocation

`ops-agent` should exist as a Compose service definition but normally run on demand:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent collect --period auto
```

The service does not need to stay running. It exits after creating the bundle.

## Proposed Directory Structure

```text
ops-agent/
  Dockerfile
  docker-compose.ops-agent.yml
  README.md
  sql/
    create_readonly_role.sql
  ops_agent/
    __init__.py
    __main__.py
    cli.py
    config.py
    state.py
    bundle.py
    schemas.py
    retention.py
    redaction.py
    detectors.py
    db_queries.py
    collectors/
      __init__.py
      db.py
      health.py
      logs.py
      local_state.py
tests/
  ops_agent/
    test_*.py
docs/
  ops-agent-implementation-plan.md
  ops-agent-report-codex-prompt.md
```

Only the two docs files are part of the initial documentation task. The package files are planned for the implementation task.

## Compose Overlay Plan

Add `ops-agent/docker-compose.ops-agent.yml` in the implementation task.

Service requirements:

* Service name: `ops-agent`.
* Build context: repository root or `ops-agent/`, whichever keeps imports simple.
* Mount logs read-only: `./logs:/app/logs:ro`.
* Mount reports read-write: `./reports/ops-agent:/app/reports/ops-agent:rw`.
* Use the existing Compose network so `ops-agent` can reach `postgres` and `bot`.
* No `ports:`.
* No Docker socket mount.
* No dependency on a continuously running `ops-agent` container.

Expected environment:

* `OPS_AGENT_DATABASE_URL=postgresql+asyncpg://ccwbot_ops_reader:<password>@postgres:5432/ccwbot`
* `OPS_AGENT_HEALTH_URL=http://bot:${HEALTH_PORT:-8080}/health`
* Optional limits such as max bundle size, max log bytes, and query timeout.

## CLI Commands

Implement these commands:

```bash
ops-agent collect --period auto --output-dir /app/reports/ops-agent
ops-agent collect --since 2026-05-31T00:00:00Z --until 2026-06-01T00:00:00Z
ops-agent collect --since 2026-05-31T00:00:00Z --until now
ops-agent collect --no-state-update
ops-agent collect --include-raw-llm-samples
ops-agent collect --include-protected-identity-map
ops-agent validate-bundle /app/reports/ops-agent/bundles/<bundle-id>
ops-agent mark-report-success --bundle <bundle-path> --report <report-path>
ops-agent inspect-state
ops-agent retention
ops-agent print-readonly-role-sql
```

`collect` must print a single JSON object to stdout:

```json
{
  "status": "complete",
  "bundle_path": "/app/reports/ops-agent/bundles/20260601T120000Z_ab12cd34",
  "codex_instructions_path": "/app/reports/ops-agent/bundles/20260601T120000Z_ab12cd34/CODEX_INSTRUCTIONS.md",
  "manifest_path": "/app/reports/ops-agent/bundles/20260601T120000Z_ab12cd34/manifest.json",
  "period_start": "2026-06-01T00:00:00Z",
  "period_end": "2026-06-01T12:00:00Z"
}
```

Status values: `complete`, `partial`, `failed`.

## Diagnostic Bundle Layout

Bundle directory:

```text
reports/ops-agent/bundles/<UTC>_<bundle_id>/
  CODEX_INSTRUCTIONS.md
  manifest.json
  bundle_summary.md
  redaction_report.json
  limits.json
  detectors/
    detector_summary.md
    detector_results.json
  evidence/
    db/
      aggregate_metrics.json
      anomalies.json
      recent_market_events.json
      recent_alert_failures.json
      recent_llm_failures.json
      recent_news_failures.json
      raw_llm_samples.redacted.json
    health/
      health.json
    logs/
      log_index.json
      pattern_counts.json
      excerpts/
        *.redacted.log
    local_state/
      ops_agent_state_snapshot.json
      legacy_state_snapshot.json
  private/
    identity_map.protected.json
```

`private/identity_map.protected.json` is optional and only created when explicitly requested.

## Bundle Schema

`manifest.json`:

```json
{
  "schema_version": 1,
  "bundle_id": "20260601T120000Z_ab12cd34",
  "collection_status": "complete",
  "period": {
    "start": "2026-06-01T00:00:00Z",
    "end": "2026-06-01T12:00:00Z",
    "source": "auto"
  },
  "generated_at": "2026-06-01T12:00:00Z",
  "ops_agent_version": "0.1.0",
  "collector_status": [
    {"name": "db.alerts_summary", "status": "ok", "error": null}
  ],
  "file_inventory": [
    {"path": "evidence/db/aggregate_metrics.json", "bytes": 1234, "sha256": "..."}
  ],
  "warnings": []
}
```

`detectors/detector_results.json`:

```json
{
  "schema_version": 1,
  "period": {"start": "2026-06-01T00:00:00Z", "end": "2026-06-01T12:00:00Z"},
  "results": [
    {
      "id": "failed_telegram_deliveries",
      "severity": "high",
      "status": "triggered",
      "summary": "12 failed deliveries",
      "evidence_refs": ["evidence/db/recent_alert_failures.json"],
      "metrics": {"failed": 12}
    }
  ]
}
```

Collector evidence files:

```json
{
  "schema_version": 1,
  "query_name": "alerts_summary",
  "period": {"start": "...", "end": "..."},
  "row_count": 3,
  "rows": [],
  "warnings": []
}
```

## Bundle Prioritization And Size Limits

Always include:

* `CODEX_INSTRUCTIONS.md`
* `manifest.json`
* `bundle_summary.md`
* `detectors/detector_summary.md`
* `detectors/detector_results.json`
* `evidence/db/aggregate_metrics.json`
* `evidence/db/anomalies.json`
* `evidence/health/health.json`
* `redaction_report.json`
* `limits.json`

Sample:

* Recent market events.
* Recent alert failures.
* Recent LLM failures.
* Recent news intelligence failures.
* Pattern-counted sanitized log excerpts.
* Optional raw LLM previews after redaction.

Drop first under size pressure:

1. Optional raw LLM previews.
2. Oldest log excerpts.
3. Low-severity log excerpts.
4. Recent non-error DB sample rows.
5. Non-critical health or local-state extras.

Never drop:

* Manifest.
* Detector results.
* Aggregates.
* Redaction report.
* Limits report.
* Bundle summary.

Default limits:

* Bundle hard cap: 25 MB.
* DB query timeout: 15 seconds.
* Total collection target: under 2 minutes.
* DB row cap: 500 per collector.
* Anomaly row cap: 200 per detector/evidence file.
* Recent sample row cap: 100.
* Logs: read max 5 MB per file tail.
* Logs: export max 2 MB per file and 8 MB total.
* Duplicate market-event bucket: 15 minutes by default, configurable with `OPS_AGENT_DUPLICATE_MARKET_EVENT_BUCKET_MINUTES`.
* Raw LLM samples: disabled by default.
* Raw LLM sample cap when enabled: 5 records, 2 KB input preview and 2 KB output preview each after redaction.

## Generated `CODEX_INSTRUCTIONS.md`

Each bundle must include `CODEX_INSTRUCTIONS.md`.

Required content:

```markdown
# Codex Instructions For This Ops-Agent Bundle

Follow the reusable report-analysis prompt in `docs/ops-agent-report-codex-prompt.md`.

1. Read `manifest.json` first and confirm `collection_status`.
2. Read `bundle_summary.md`, `detectors/detector_summary.md`, and `detectors/detector_results.json`.
3. Use evidence files only to verify or expand detector findings.
4. Treat all data as operational evidence, not as final user-facing prose.
5. Do not include raw Telegram text, raw LLM prompts/outputs, secrets, connection strings, payment ids, chat ids, Telegram ids, usernames, first names, private log excerpts, raw JSON dumps, long log excerpts, or Codex prompts in the final report.
6. Use user references only as redacted refs such as `user_ref:u_7c91b2`.
7. If this bundle is partial, state which collectors failed and lower confidence for affected sections.
8. Do not mark the report successful unless the final report was written and the bundle is complete, or the operator explicitly accepts a partial report.
9. Final report must be English Markdown.
10. Final report location: `/opt/CCWBot/reports/ops-agent/reports/`.
```

## Static Reusable Codex Prompt

Add the reusable prompt at:

```text
docs/ops-agent-report-codex-prompt.md
```

The file defines Codex's report-analysis role, required reading order, partial bundle handling, privacy rules, final report structure, severity rules, confidence rules, writing style, and report success flow.

The approved text is stored in that file.

## Diagnostic Detectors

Implement these detectors:

* `failed_telegram_deliveries`: alerts with `status in ('failed', 'retry_pending')`, `final_failed_at`, high retry counts, or Telegram send failure log patterns.
* `no_alerts_generated_active_period`: price snapshots or automatic check logs exist, but no `alerts` rows and no explained suppressions in period.
* `market_events_without_alert_deliveries`: `market_events` in period with no matching `alerts.market_event_id`.
* `repeated_llm_failures_or_rate_limits`: repeated `llm_usage_logs` failures or rate-limit statuses.
* `failed_daily_weekly_reports`: daily or weekly `market_reports.status != 'completed'`, or expired latest reports without replacement.
* `stale_or_failed_market_heartbeats`: missing recent successful heartbeats per enabled symbol or heartbeat failures.
* `duplicate_market_events`: repeated `symbol,event_type,event_key` beyond expected bucket behavior or duplicate-like instance anomalies.
* `duplicate_alert_deliveries`: duplicate deliveries for the same user, symbol, event, or heartbeat.
* `blocked_users_still_active`: `users.bot_blocked=true AND users.is_active=true`.
* `payment_premium_inconsistencies`: paid payments without active/extended Premium, active Premium without a payment or grant trail, expired active subscriptions, or duplicate provider payment ids.
* `news_intelligence_failures`: failed news intelligence rows, high skipped-budget rates, or warning log patterns.
* `stale_price_snapshots`: stale `price_snapshots.checked_at` or `price_state.last_checked_at`.
* `health_endpoint_unavailable`: health fetch failed, timed out, or returned non-ok status.
* `exception_patterns_in_logs`: ERROR, traceback, uncaught exception, schema validation, rate-limit, or other exception patterns.

Detector statuses:

* `triggered`
* `clear`
* `unknown`

Each detector defines required evidence. Missing DB/log evidence returns `unknown` with an evidence gap instead of `clear`.

Detector threshold defaults:

* Widespread delivery failure: failed deliveries >= 5 or failed rate >= 20%.
* Repeated LLM failures: >= 3 failures or any sustained rate-limit backoff in period.
* Stale price data: no successful BTC check for more than 2x `automatic_check_interval_seconds`, minimum 30 minutes.
* Stale heartbeat: no successful heartbeat for more than 2 hours.
* Failed reports: latest daily older than 8 hours or latest weekly older than 30 hours.

## Severity Rules

Use these levels in detector output and final reports:

* `critical`: bot likely down, health unavailable with no recent successful activity, payment corruption, widespread delivery failure, or repeated LLM/report failure blocking core function.
* `high`: user-visible degradation, repeated delivery failures, stale market data, failed reports, active blocked users, duplicate deliveries, premium/payment inconsistency.
* `medium`: partial degradation, rate-limit pressure, stale heartbeats, news intelligence failures, non-widespread exceptions.
* `low`: noisy logs, isolated failures, cleanup suggestions.
* `info`: normal metrics and no-action observations.

## PostgreSQL Read-Only Role

Create a dedicated read-only role:

```sql
CREATE ROLE ccwbot_ops_reader LOGIN PASSWORD '<set manually>';
GRANT CONNECT ON DATABASE ccwbot TO ccwbot_ops_reader;
GRANT USAGE ON SCHEMA public TO ccwbot_ops_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ccwbot_ops_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE ccwbot IN SCHEMA public GRANT SELECT ON TABLES TO ccwbot_ops_reader;
```

Use:

```text
OPS_AGENT_DATABASE_URL=postgresql+asyncpg://ccwbot_ops_reader:<password>@postgres:5432/ccwbot
```

Normal collection must use only this role.

## Database Collectors And Query List

All queries must be parameterized and read-only. Use `:since` and `:until` for period filters.

Collectors:

* `schema_version`: `SELECT version_num FROM alembic_version`.
* `app_settings`: thresholds, interval, error file logging flag, timestamps.
* `user_summary`: total users, active users, blocked users, admins, new users in period.
* `watchlist_summary`: enabled subscriptions by symbol, free versus premium symbols.
* `premium_summary`: subscription statuses, active/expired counts, expirations in period.
* `payments_summary`: payment counts by status/currency/provider, period totals, anomalous rows, duplicate provider payment checks.
* `price_state_current`: current rows from `price_state` and staleness.
* `price_snapshots_summary`: per-symbol count, min, max, average price, 24h change, and 7d change over period.
* `market_events_summary`: counts by symbol, event type, event key, first/last detected, max absolute move.
* `market_events_recent`: newest limited event rows with market fields only.
* `event_ai_analysis_summary`: counts by symbol/status/should_alert/error_reason, token totals, latest attempt.
* `event_ai_analysis_samples`: sanitized limited metadata, with raw previews only if explicitly enabled.
* `alerts_summary`: counts by symbol, alert type, status, trigger source, fallback, retry state.
* `alerts_failures`: recent failed, retry-pending, or final-failed deliveries.
* `delivery_invariant_checks`: duplicate deliveries, events without deliveries, and events with multiple analysis ids in deliveries.
* `market_heartbeats_summary`: heartbeat status counts, latest generated time, and delivery counts.
* `market_reports_summary`: daily and weekly report cache status and freshness.
* `llm_usage_summary`: calls by provider, model, call type, status, token totals, rate-limit counts, retry-after values.
* `news_items_summary`: counts by LLM status, impact level, duplicate/noise/alert-worthy flags.
* `news_items_recent_high_impact`: public title, source, URL, symbol, category, and impact.
* `seen_news_summary`: count and recent seen window.

## Log Collectors

Read these files if present:

* `logs/ccwbot-operational.log*`
* `logs/ccwbot-warnings-errors.log*`

Collect:

* Pattern counts by `ops_event`.
* WARNING and ERROR excerpts.
* Traceback excerpts with limited surrounding lines.
* CoinGecko 429 and rate-limit lines.
* Telegram delivery failure lines.
* LLM failure, rate-limit, and schema validation lines.
* Report and heartbeat failure lines.
* Payment rejection lines.

Log evidence must be redacted and truncated before export.
When timestamps can be parsed, log evidence is split into timestamped period-matched excerpts and unscoped tail-context excerpts. Lines without parseable timestamps are not period evidence. `log_index.json`, `pattern_counts.json`, and `bundle_summary.md` identify which evidence scope each count or excerpt belongs to.

## Bot Operational Logging Changes

Implementation should add always-on redacted rotating operational logs:

* File: `logs/ccwbot-operational.log`.
* Rotation: 10 MB.
* Backups: 5.
* Encoding: UTF-8.
* Level: INFO and above.
* Formatter: existing secret redaction plus URL credential masking.

Keep existing admin-controlled warning/error file logging unchanged.

Exact logging touchpoints:

* `main.configure_logging`: attach operational file handler and keep noisy third-party INFO logs reduced.
  * INFO sample: `ops_event=bot_start environment=production health_port=8080`
* `main.main`: startup, health server started, shutdown.
  * INFO sample: `ops_event=health_started port=8080`
* `bot/runtime.initialize_database`: database configured without URL.
  * INFO sample: `ops_event=db_configured backend=postgres`
* `bot/runtime.close_database`: database resources closed.
  * INFO sample: `ops_event=db_closed`
* `bot/alerts.schedule_automatic_market_check`: interval configured.
  * INFO sample: `ops_event=automatic_check_scheduled interval_seconds=600`
* `bot/alerts.automatic_price_check`: cycle completion, symbols checked, delivered count, skipped reason, CoinGecko 429.
  * INFO sample: `ops_event=automatic_check_completed symbols=BTC,ETH delivered_symbols=1 duration_seconds=2.31`
  * WARNING sample: `ops_event=automatic_check_failed reason=http_error error_class=HTTPStatusError`
* `bot/alerts._deliver_market_event_alert`: recipients, sent, failed, skipped duplicates, market event id.
  * INFO sample: `ops_event=event_alert_delivery_summary symbol=BTC market_event_id=123 eligible=10 sent=9 failed=1 skipped_duplicates=0`
* `bot/alerts._deliver_market_heartbeat`: due recipients and result.
  * INFO sample: `ops_event=heartbeat_delivery_summary symbol=BTC heartbeat_id=22 due=8 sent=8 failed=0`
* `bot/alerts.generate_market_heartbeats`: generated, skipped, failed.
  * INFO sample: `ops_event=heartbeat_generation_completed generated=3 fresh_skipped=2`
* `bot/reports.generate_report_cache`: daily/weekly generated, schema failure, skipped, failed.
  * INFO sample: `ops_event=market_report_generated report_type=daily status=completed`
  * WARNING sample: `ops_event=market_report_failed report_type=weekly reason=schema_error`
* `bot/services/ai_agent_groq._run_groq_chat_completion`: LLM call status without prompt or output.
  * INFO sample: `ops_event=llm_call_completed provider=groq model=<model> call_type=event_analysis status=success`
* `bot/services/ai_agent_groq._start_llm_rate_limit_backoff`: rate-limit backoff.
  * WARNING sample: `ops_event=llm_rate_limit_started provider=groq model=<model> call_type=event_analysis retry_after_seconds=300`
* `bot/services/news_intelligence_service`: processed, skipped, failed counts.
  * INFO sample: `ops_event=news_intelligence_batch_completed fetched=20 success=5 skipped_budget=3 failed=1`
* `bot/services/price_service._get_with_retry`: CoinGecko 429 and stale-cache fallback.
  * WARNING sample: `ops_event=coingecko_rate_limit attempt=2 max_retries=2 stale_cache_available=true`
* `bot/payments.successful_payment_handler`: processed, duplicate, rejected payments with no payment ids.
  * INFO sample: `ops_event=premium_payment_processed provider=telegram_stars status=processed`
  * WARNING sample: `ops_event=premium_payment_rejected reason=invalid_payload`
* `bot/handlers.log_request`: command handled/denied summaries without private text.

Avoid logging:

* Private Telegram message text.
* Raw prompts.
* Raw LLM outputs.
* Secrets.
* Database URLs.
* Payment ids.
* Charge ids.
* Invoice payloads.
* Usernames.
* First names.

## Privacy, Redaction, And User References

Default export must redact:

* Telegram user ids.
* Telegram chat ids.
* Usernames.
* First names.
* Payment ids.
* Charge ids.
* Invoice payloads.
* Provider subscription ids.
* Tokens and API keys.
* Database URLs and URL credentials.
* Raw private Telegram text.

Use per-bundle stable refs:

* `user_ref:u_7c91b2`
* `chat_ref:c_45ab19`
* `payment_ref:p_f09d33`

Refs must be stable only within one bundle. Use a per-bundle random salt or HMAC key that is not exported in normal evidence.

Final reports should use aggregate descriptions by default. Use refs only when user-specific remediation is required.

## Optional Protected Identity Map

`--include-protected-identity-map` may write:

```text
private/identity_map.protected.json
```

Rules:

* Only create it when explicitly requested.
* Use owner read/write permissions where supported.
* Exclude it from normal evidence references.
* Mark it as protected in `manifest.json`.
* Codex must not quote mapping contents in final reports.
* It follows the same retention period as its bundle.

## State File Schema And Since-Last-Report Behavior

State path:

```text
reports/ops-agent/state/state.json
```

Schema:

```json
{
  "schema_version": 1,
  "last_successful_report": {
    "report_id": "20260601T120000Z_ops_report",
    "bundle_id": "20260601T120000Z_ab12cd34",
    "period_start": "2026-06-01T00:00:00Z",
    "period_end": "2026-06-01T12:00:00Z",
    "completed_at": "2026-06-01T12:10:00Z",
    "report_path": "/app/reports/ops-agent/reports/20260601T121000Z_ops_report.md",
    "bundle_path": "/app/reports/ops-agent/bundles/20260601T120000Z_ab12cd34",
    "bundle_sha256": "..."
  },
  "last_collection": {
    "bundle_id": "20260601T120000Z_ab12cd34",
    "status": "complete",
    "period_start": "2026-06-01T00:00:00Z",
    "period_end": "2026-06-01T12:00:00Z"
  },
  "recent_runs": []
}
```

Behavior:

* `collect --period auto` starts at `last_successful_report.period_end` when present.
* If no successful report exists, it collects the last 24 hours.
* `collect` updates `last_collection`.
* `mark-report-success` updates `last_successful_report`.
* Partial bundles do not advance `last_successful_report` unless explicitly accepted by the operator.

## Retention Policy

Retain:

* Bundles for 60 days.
* Reports for 60 days.
* Maximum 30 bundle directories.
* Maximum 30 report files.

Always preserve:

* Current active bundle.
* `reports/ops-agent/state/state.json`.

Run retention after successful collection and through explicit `ops-agent retention`.

## Server Runbook

### First-Time Setup

1. Deploy the implementation through Git to `/opt/CCWBot`.
2. Create the read-only PostgreSQL role with `ops-agent/sql/create_readonly_role.sql`.
3. Keep `/opt/CCWBot/.env` root-owned with mode `600`; `ccwbot_ops` must not be able to read it.
4. Create `/opt/CCWBot/.ops-agent.env` manually on production with only minimal `OPS_AGENT_*` values. Keep it root-owned with mode `600`; `ccwbot_ops` must not be able to read it.
5. Install root-owned safe wrappers:

```bash
sudo install -m 755 -o root -g root ops-agent/scripts/ccwbot-ops-agent-collect /usr/local/bin/ccwbot-ops-agent-collect
sudo install -m 755 -o root -g root ops-agent/scripts/ccwbot-ops-agent-mark-report-success /usr/local/bin/ccwbot-ops-agent-mark-report-success
```

The wrappers execute `/usr/bin/docker` with a minimal environment. If Docker is installed elsewhere, update the tracked wrapper template through Git.

6. Allow only those wrappers through sudoers:

```text
Defaults:ccwbot_ops env_reset, secure_path="/usr/bin:/bin"
ccwbot_ops ALL=(root) NOPASSWD: /usr/local/bin/ccwbot-ops-agent-collect
ccwbot_ops ALL=(root) NOPASSWD: /usr/local/bin/ccwbot-ops-agent-mark-report-success
```

7. Create the report tree:

```bash
sudo install -d -m 750 -o root -g ccwbot_ops /opt/CCWBot/reports/ops-agent
sudo install -d -m 750 -o root -g ccwbot_ops /opt/CCWBot/reports/ops-agent/bundles
sudo install -d -m 770 -o root -g ccwbot_ops /opt/CCWBot/reports/ops-agent/reports
```

`ccwbot_ops` may read generated bundles and may write only final Markdown reports under `/opt/CCWBot/reports/ops-agent/reports/` if needed. It must not be able to read `.env` or `.ops-agent.env`, write bundles directly, write tracked files or wrapper templates, run arbitrary Docker commands, print environments, deploy, restart services, or run migrations.

Generated bundles and reports are operational artifacts and must stay ignored by Git. Commit only safe templates and wrapper scripts.

8. Validate Compose locally before deployment and avoid publishing production Compose output:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml config >/dev/null
```

### Smoke Test

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since <1-hour-ago UTC timestamp> --until now --no-state-update
```

### Normal Codex Workflow

1. SSH to the server.
2. Run the safe collection wrapper:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect
```

For an explicit incident window, run:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since 2026-05-27T00:00:00Z --until now
```

Explicit periods must have `since < until` and must not exceed 720 hours.

3. Read stdout JSON.
4. Read the bundle in the required order.
5. Write the final report under `/opt/CCWBot/reports/ops-agent/reports/`.
6. Run the safe mark-success wrapper only if the report was written and the bundle is complete, unless the operator explicitly accepts a partial report:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-mark-report-success --bundle /opt/CCWBot/reports/ops-agent/bundles/<bundle-id> --report /opt/CCWBot/reports/ops-agent/reports/<report-file>.md
```

7. Return the Markdown report to the operator.

### Emergency Disable

Stop using the overlay command and remove or unset `OPS_AGENT_DATABASE_URL`.

To disable DB access:

```sql
ALTER ROLE ccwbot_ops_reader NOLOGIN;
```

### Credential Rotation

1. Generate a new password.
2. Run:

```sql
ALTER ROLE ccwbot_ops_reader PASSWORD '<new-password>';
```

3. Update production `.ops-agent.env`.
4. Run the smoke test.
5. Confirm old credentials no longer work if they were stored elsewhere.

### Manual Cleanup

Prefer:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent retention
```

If manual cleanup is needed, delete only old entries under:

* `/opt/CCWBot/reports/ops-agent/bundles/`
* `/opt/CCWBot/reports/ops-agent/reports/`

Do not delete `reports/ops-agent/state/state.json` unless intentionally resetting the report period.

## Test Plan

Add tests for:

* CLI argument parsing.
* Period resolution.
* Since-last-success behavior.
* State schema read/write.
* `mark-report-success`.
* Bundle manifest and file inventory.
* Bundle checksums.
* Partial collector status.
* Bundle prioritization and drop order under size pressure.
* Redaction of secrets, database URLs, URL credentials, Telegram ids, chat ids, usernames, first names, payment ids, and invoice payloads.
* Stable per-bundle refs.
* Non-stability of refs across bundles.
* Optional protected identity map generation.
* Every detector listed in this plan.
* Log collector pattern extraction, period filtering, and unscoped tail-context handling.
* Log truncation.
* Duplicate market-event bucket detection for clear, triggered, and unknown cases.
* No-delivery event classification for expected no-alert, product/no-recipient gating, LLM/rate-limit, `should_alert=true` gaps, and unknown cases.
* Read-only SQL guard: collector SQL starts with `SELECT` or `WITH` and uses parameters.
* Static prompt file existence and expected content.
* Compose overlay config validation.

Default project verification after implementation:

```bash
python -m py_compile main.py bot/config.py bot/storage.py bot/health.py bot/alerting/alert_rules.py bot/alerting/alert_severity.py bot/db/database.py bot/domain/premium.py bot/domain/supported_coins.py bot/services/price_service.py bot/services/news_service.py bot/services/ai_agent_groq.py
ruff check .
python -m pytest tests/ -v
docker compose config >/dev/null
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml config >/dev/null
```

## End-To-End Acceptance Criteria

Acceptance scenario: Codex generates an operational report since the last successful report using `ops-agent` bundle collection.

Flow:

1. Seed or mock `state/state.json` with `last_successful_report.period_end=T1`.
2. Seed test DB/log fixtures with events from `T1` to `T2`.
3. Run:

```bash
ops-agent collect --period auto --output-dir <tmp>
```

4. Assert bundle period starts at `T1` and ends near `T2`.
5. Assert these files exist:
   * `CODEX_INSTRUCTIONS.md`
   * `manifest.json`
   * `bundle_summary.md`
   * `detectors/detector_summary.md`
   * `detectors/detector_results.json`
   * `redaction_report.json`
   * `limits.json`
6. Assert raw ids and secrets do not appear in exported evidence.
7. Simulate Codex reading required files and writing:

```text
<tmp>/reports/<timestamp>_ops_report.md
```

8. Run:

```bash
ops-agent mark-report-success --bundle <bundle> --report <report>
```

9. Assert state advances to the bundle period end.
10. Run another `collect --period auto`.
11. Assert the second collection starts from the new `last_successful_report.period_end`.
12. Assert partial bundles do not advance state unless explicitly accepted.

## Implementation Phases

### Phase 1: Documentation And Contract

* Add `docs/ops-agent-implementation-plan.md`.
* Add `docs/ops-agent-report-codex-prompt.md`.

### Phase 2: Ops-Agent Skeleton

* Add package skeleton.
* Add CLI.
* Add config loading.
* Add state file handling.
* Add bundle writer.
* Add retention.
* Add Compose overlay and Dockerfile.

### Phase 3: Collectors And Redaction

* Add DB collectors.
* Add health collector.
* Add log collector.
* Add local state collector.
* Add redaction and reference mapping.
* Add optional protected identity map.

### Phase 4: Detectors And Codex Bundle Contract

* Add detector engine.
* Add detector outputs.
* Add generated `CODEX_INSTRUCTIONS.md`.
* Add bundle summary generation.
* Add partial bundle handling.

### Phase 5: Bot Operational Logging

* Add always-on operational rotating file logging.
* Add safe `ops_event=` logs at the planned touchpoints.
* Keep existing warning/error logging behavior.

### Phase 6: Tests And Release Safety

* Add focused unit and integration tests.
* Validate Compose overlay.
* Run default verification.
* Prepare PR description with security, DB, logging, and behavior confirmations.
