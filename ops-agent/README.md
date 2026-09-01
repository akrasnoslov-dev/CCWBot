# CCWBot Ops-Agent

`ops-agent` is a local, on-demand diagnostic bundle collector for Codex. It does not use an LLM, does not expose a port, does not mount the Docker socket, does not apply fixes, and does not provide a raw SQL endpoint.

The Compose overlay must not pass the bot `.env` into the container. Only explicit `OPS_AGENT_*` variables are allowed.
The overlay reads `.ops-agent.env` for the `ops-agent` service only; the base Compose file may still use the project `.env` for normal interpolation.

## Production Read-Only Setup

Create or use a dedicated limited VPS account named `ccwbot_ops` for operator collection access:

```bash
sudo adduser --disabled-password --gecos "" ccwbot_ops
sudo install -d -m 700 -o ccwbot_ops -g ccwbot_ops /home/ccwbot_ops/.ssh
sudoedit /home/ccwbot_ops/.ssh/authorized_keys
sudo chown ccwbot_ops:ccwbot_ops /home/ccwbot_ops/.ssh/authorized_keys
sudo chmod 600 /home/ccwbot_ops/.ssh/authorized_keys
```

Do not give `ccwbot_ops` broad sudo. Do not add it to the `docker` group unless the operator explicitly accepts that Docker group membership is root-equivalent.

Preferred production access is through root-owned wrappers installed from the tracked templates:

```bash
sudo install -m 755 -o root -g root ops-agent/scripts/ccwbot-ops-agent-collect /usr/local/bin/ccwbot-ops-agent-collect
sudo install -m 755 -o root -g root ops-agent/scripts/ccwbot-ops-agent-mark-report-success /usr/local/bin/ccwbot-ops-agent-mark-report-success
sudo chown root:root /usr/local/bin/ccwbot-ops-agent-collect
sudo chown root:root /usr/local/bin/ccwbot-ops-agent-mark-report-success
sudo chmod 755 /usr/local/bin/ccwbot-ops-agent-collect
sudo chmod 755 /usr/local/bin/ccwbot-ops-agent-mark-report-success
```

The collect wrapper allows only `ops-agent collect` with `--period auto|Nh`, `--since <UTC ISO timestamp>`, `--until <UTC ISO timestamp|now>`, and `--no-state-update`. UTC timestamps must use `YYYY-MM-DDTHH:MM:SSZ`, for example `2026-06-06T00:00:00Z`; ambiguous dates such as `06/06/2026` are rejected. The wrapper rejects unsupported flags such as raw LLM samples, protected identity maps, custom output directories, shell fragments, deployment commands, restarts, migrations, environment printing, and secret-reading commands.

The mark-success wrapper allows only `ops-agent mark-report-success` with one bundle path under `/opt/CCWBot/reports/ops-agent/bundles/` or `/app/reports/ops-agent/bundles/`, one Markdown report path under `/opt/CCWBot/reports/ops-agent/reports/` or `/app/reports/ops-agent/reports/`, and optional `--accept-partial`.

Both wrappers execute `/usr/bin/docker` with a minimal environment. If Docker is installed elsewhere on the VPS, update the tracked wrapper template and deploy that change through Git rather than editing `/usr/local/bin` by hand.

Allow only those wrappers through sudoers:

```bash
sudo visudo -f /etc/sudoers.d/ccwbot_ops
```

Use this entry:

```text
Defaults:ccwbot_ops env_reset, secure_path="/usr/bin:/bin"
ccwbot_ops ALL=(root) NOPASSWD: /usr/local/bin/ccwbot-ops-agent-collect
ccwbot_ops ALL=(root) NOPASSWD: /usr/local/bin/ccwbot-ops-agent-mark-report-success
```

Filesystem permission checks:

```bash
sudo -u ccwbot_ops test ! -r /opt/CCWBot/.env
sudo -u ccwbot_ops test ! -r /opt/CCWBot/.ops-agent.env
sudo -u ccwbot_ops test ! -w /opt/CCWBot/main.py
sudo -u ccwbot_ops test ! -w /opt/CCWBot/docker-compose.yml
sudo -u ccwbot_ops test ! -w /opt/CCWBot/ops-agent/scripts/ccwbot-ops-agent-collect
sudo -u ccwbot_ops test ! -w /opt/CCWBot/ops-agent/scripts/ccwbot-ops-agent-mark-report-success
sudo install -d -m 750 -o root -g ccwbot_ops /opt/CCWBot/reports/ops-agent
sudo install -d -m 750 -o root -g ccwbot_ops /opt/CCWBot/reports/ops-agent/bundles
sudo install -d -m 770 -o root -g ccwbot_ops /opt/CCWBot/reports/ops-agent/reports
sudo -u ccwbot_ops test ! -w /opt/CCWBot/reports/ops-agent
sudo -u ccwbot_ops test -r /opt/CCWBot/reports/ops-agent/bundles
sudo -u ccwbot_ops test ! -w /opt/CCWBot/reports/ops-agent/bundles
sudo -u ccwbot_ops test -w /opt/CCWBot/reports/ops-agent/reports
```

Verify `ccwbot_ops` can read generated bundles, write only final Markdown reports under `/opt/CCWBot/reports/ops-agent/reports/`, and cannot write tracked files or wrapper templates. If any check fails, stop and fix permissions before collecting.

Create the production ops-agent environment manually. Do not copy the bot `.env`; use `.ops-agent.env.example` as the placeholder-only reference and create only the minimal `OPS_AGENT_*` values needed by the collector:

```bash
sudo chown root:root /opt/CCWBot/.env
sudo chmod 600 /opt/CCWBot/.env
sudo install -m 600 -o root -g root /dev/null /opt/CCWBot/.ops-agent.env
sudoedit /opt/CCWBot/.ops-agent.env
sudo chown root:root /opt/CCWBot/.ops-agent.env
sudo chmod 600 /opt/CCWBot/.ops-agent.env
```

Required production contents:

```text
OPS_AGENT_DATABASE_URL=postgresql+asyncpg://ccwbot_ops_reader:<password>@postgres:5432/ccwbot
OPS_AGENT_HEALTH_URL=http://bot:8080/health
```

Normal production collection:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect
```

Post-deploy verification after Event Alert delivery-gap changes:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --period 2h --until now --no-state-update
```

Use the generated sanitized bundle and report context to confirm `/health` is OK, container state is
healthy or explicitly marked unavailable, `market_events_without_alert_deliveries` is clear or only
contains explicit expected skip reasons, and there are no new critical/high unexplained Event Alert
detector findings. Perform a basic Telegram smoke check with a private test chat, but do not record
Telegram user ids, private message text, payment ids, raw logs, raw DB rows, or raw bundle JSON in
the report. After ops-agent changes, rebuild the `ops-agent` Docker image during production deploy
before relying on this verification.

Explicit production collection period:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since 2026-05-27T00:00:00Z --until now
```

Explicit periods must have `since < until` and must not exceed 720 hours.
Use UTC ISO input only: `YYYY-MM-DDTHH:MM:SSZ`. Do not use slash-form dates.

DB collectors run as isolated read-only collectors. If one DB collector fails, the bundle records
that collector as failed with a sanitized error category, continues later collectors, and marks the
bundle `partial`. Use the generated collector status table to distinguish `Collector failed` from
true `Unknown` evidence.

Ops-agent/report PRs are observability-only unless the task explicitly asks for runtime changes.
Partial reports must list failed or partial collectors in `Collector Status`; missing evidence and
detector `unknown` states are not healthy results.

After ops-agent code changes, production deploy requires explicitly rebuilding the `ops-agent`
Docker image. A bot-only rebuild does not verify the collector image.

Before releasing DB query changes, run the PostgreSQL query-contract test against a local
throwaway database:

```bash
OPS_AGENT_POSTGRES_TEST_DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:<port>/<test_db> \
  python -m pytest tests/ops_agent/test_db_queries_and_detectors.py::test_all_ops_agent_queries_explain_against_migrated_postgres_schema -v
```

The test runs Alembic to head, `EXPLAIN`s every ops-agent DB query, and verifies malformed
`alerts.numeric_context` text does not break same-family or same-news collectors.

The command prints one JSON object with the generated bundle path. Codex should read the bundle in this order:

1. `CODEX_INSTRUCTIONS.md`
2. `manifest.json`
3. `bundle_summary.md`
4. `decision_report_context.md`
5. `detectors/detector_summary.md`
6. `detectors/detector_results.json`
7. `redaction_report.json`
8. `limits.json`

Final report writing remains Codex's responsibility using `docs/ops-agent-report-codex-prompt.md`. The generated `decision_report_context.md` is Markdown-only decision context; use it to start the final report, then verify important claims against detectors and evidence. Save final reports under `/opt/CCWBot/reports/ops-agent/reports/`, then run `sudo /usr/local/bin/ccwbot-ops-agent-mark-report-success --bundle <bundle> --report <report>` only after a complete bundle has produced a written report. Codex must not download generated bundles or reports into the repo worktree. If temporary local copies are unavoidable, place them under `.cache/tmp` and clean them up before finishing.

Log evidence is period-aware when CCWBot timestamps are parseable. Bundles separate timestamped
period-matched structured match records from unscoped tail-context records and include
skipped/unparseable counts. Records use a strict safe-field allowlist; bundles never include raw
or redacted log lines. Period-matched evidence is stronger for the requested report period.

Detector `unknown` means evidence is missing or inconclusive, not healthy. Market events without deliveries are classified into expected no-delivery, LLM failure/rate-limit, `should_alert=true` delivery gaps, and unknown buckets where the available schema cannot prove the reason.

First-time DB setup uses a read-only PostgreSQL role:

```bash
docker compose exec postgres psql -U ccwbot -d ccwbot -f /path/to/ops-agent/sql/create_readonly_role.sql
```

Set `OPS_AGENT_DATABASE_URL` in `/opt/CCWBot/.ops-agent.env` with the `ccwbot_ops_reader` role:

```text
OPS_AGENT_DATABASE_URL=postgresql+asyncpg://ccwbot_ops_reader:<password>@postgres:5432/ccwbot
```

The `.ops-agent.env.example` values are placeholders only and must not contain real passwords.

By default, the health collector uses the production-safe Compose `bot` service name:

```text
OPS_AGENT_HEALTH_URL=http://bot:8080/health
```

For local Windows/Docker Desktop testing, override it in `.ops-agent.env` if the bot is reachable through the host:

```text
OPS_AGENT_HEALTH_URL=http://host.docker.internal:8080/health
```

## Report Workflow

1. Run collection with the safe production command.
2. Read the printed JSON and open the bundle path.
3. Read `decision_report_context.md`, then have Codex write the final Markdown report under `/opt/CCWBot/reports/ops-agent/reports/`.
4. Run the safe mark-success wrapper only after the written report exists. The command validates the bundle before advancing state, rejects paths outside ops-agent report/bundle directories, and refuses tampered bundles.

Safe production command:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect
```

Safe explicit-period production command:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since 2026-05-27T00:00:00Z --until now
```

Do not print, paste, or publish `docker compose config` output from production. Compose may interpolate `OPS_AGENT_DATABASE_URL` or other environment-local values into that output.

Smoke test without advancing state:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since 2026-06-01T00:00:00Z --until 2026-06-01T01:00:00Z --no-state-update
```

Mark a completed report successful:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-mark-report-success --bundle /opt/CCWBot/reports/ops-agent/bundles/<bundle-id> --report /opt/CCWBot/reports/ops-agent/reports/<report-file>.md
```

Optional duplicate market-event bucket size:

```text
OPS_AGENT_DUPLICATE_MARKET_EVENT_BUCKET_MINUTES=15
```

Optional alert repetition evidence settings:

```text
OPS_AGENT_ALERT_EVIDENCE_ROW_CAP=500
OPS_AGENT_EVENT_ALERT_SEMANTIC_COOLDOWN_SECONDS=14400
OPS_AGENT_ALERT_EVIDENCE_QUERY_TIMEOUT_SECONDS=45
OPS_AGENT_ALERT_EVIDENCE_BUCKET_HOURS=3
```

The `db.alert_repetition_evidence` collector queries the period in per-bucket windows
(`OPS_AGENT_ALERT_EVIDENCE_BUCKET_HOURS`, newest first) with its own dedicated timeout
(`OPS_AGENT_ALERT_EVIDENCE_QUERY_TIMEOUT_SECONDS`), separate from the general
`OPS_AGENT_DB_QUERY_TIMEOUT_SECONDS`. A single slow bucket fails on its own; the remaining
buckets still run and the collector reports `partial` instead of losing all alert evidence.

The aggregate DB evidence includes `event_alert_llm_estimates` with sanitized Event Alert
LLM pressure fields:

* `event_analysis_interval_seconds`
* `payload_points`
* `analysed_window_minutes`
* `estimated_event_alert_llm_calls_per_hour`
* `estimated_event_alert_llm_calls_per_day`

Alert repetition evidence is derived from read-only DB queries and written as sanitized
hash/group data only. The bundle does not include full alert messages, raw LLM prompts,
raw LLM outputs, Telegram ids, chat ids, usernames, secrets, or connection strings.
Generated files include:

* `evidence/db/alert_delivery_distribution.json`
* `evidence/db/alert_quality.json`
* `evidence/db/event_analysis_decision_timeline.json`
* `evidence/db/alert_content_fingerprints.json`
* `evidence/db/alert_similarity_groups.json`
* `evidence/db/llm_operation_reconciliation.json`
* `evidence/db/backend_suppression_effectiveness.json`
* `evidence/db/event_identity_quality.json`

Content and analysis hashes are bundle-local HMAC references. They can group repeated
content inside one bundle, but cannot be compared across separate bundles. Similarity membership
records add bundle-local recipient, alert, event, analysis, and outcome references so a report can
classify repeated deliveries without source identifiers. Cooldown
effectiveness is inferred from analysis, event, and delivery rows because suppression
decisions are not stored as durable rows.

### Report freshness semantics

The `failed_daily_weekly_reports` detector uses freshness thresholds of runtime interval
plus one hour of scheduler grace (daily: 4h + 1h = 18000s; weekly: 24h + 1h = 90000s).
Expected regeneration semantics — reports should not speculate beyond this:

* The bot's scheduled cache refresh regenerates each report on its runtime interval
  (daily every 4h, weekly every 24h). The bot-side job regenerates whenever the cached
  report expires within its own 30-minute grace window, so a healthy scheduler keeps the
  cache age at or below interval + generation time.
* On-command `/dailyreport` and `/weeklyreport` generation may additionally refresh the
  cache at any time; a fresher-than-expected cache is normal.
* Detector metrics include per-report-type `latest_generation_age_seconds`,
  `runtime_interval_seconds`, `scheduler_grace_seconds`, and
  `expected_next_scheduled_refresh_at` so age can be judged against the expected next
  scheduled refresh directly from the evidence.

### Container restart counts

`compose ps --format json` does not include restart counts, so the collect wrapper also
captures a sanitized `docker inspect` snapshot (container name + `RestartCount` only) and
passes it via `OPS_AGENT_DOCKER_RESTARTS_JSON_PATH`. When the snapshot is missing or
unreadable, `restart_count` stays `null`, the docker evidence carries a
`restart_counts_unavailable` warning, and the report renders restart counts as unknown —
incomplete evidence, never healthy. After changing
`ops-agent/scripts/ccwbot-ops-agent-collect`, re-install the copy in `/usr/local/bin`
manually — `git pull` does not update it:

```bash
sudo install -m 755 -o root -g root /opt/CCWBot/ops-agent/scripts/ccwbot-ops-agent-collect /usr/local/bin/ccwbot-ops-agent-collect
```

### Log pattern counting

`heartbeat_failure` counts per-failure lines only: per-delivery
`ops_event=heartbeat_delivery_failed`, `ops_event=heartbeat_generation_failed`, and
schema-validation failures. `heartbeat_delivery_summary ... failed=N` lines repeat
already-counted per-delivery failures and are intentionally not matched, so the pattern
count tracks the DB delivery-failure truth instead of double-counting.

### News-candidate signal

Event-analysis evidence includes `related_news_candidates_count` (aggregate
`event_analysis_news_candidates_summary` and per-sample column): the number of candidate
news items present in the analysis input. Counts only — never news content. A zero count
means no relevant news existed for that analysis; `alerts_with_candidates_but_no_attached_news`
counts should_alert=true analyses that had candidates available but attached none, which
is the signal for a possible news-attach gap. This is observability only; it does not
change news-attach behavior.

### Collection state

`state.json` records each run under `recent_runs` including `failed_collectors`
(collector names only), so recurring `partial` runs are diagnosable from the state
snapshot alone.

Retention is automatic after collection and can be run manually:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent retention
```

## Emergency Disable

Stop using the overlay command and remove or unset `OPS_AGENT_DATABASE_URL` from `/opt/CCWBot/.ops-agent.env`. This only disables future ops-agent DB collection; it does not change bot runtime behavior. Do not restart production services solely for ops-agent unless a separate deployment requires it.

To disable shell collection access immediately:

```bash
sudo rm -f /etc/sudoers.d/ccwbot_ops
sudo chmod 000 /usr/local/bin/ccwbot-ops-agent-collect
sudo chmod 000 /usr/local/bin/ccwbot-ops-agent-mark-report-success
```

To revoke the read-only database role:

```sql
REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM ccwbot_ops_reader;
REVOKE USAGE ON SCHEMA public FROM ccwbot_ops_reader;
REVOKE CONNECT ON DATABASE ccwbot FROM ccwbot_ops_reader;
ALTER ROLE ccwbot_ops_reader NOLOGIN;
```

## Credential Rotation

Rotate the `ccwbot_ops_reader` password in PostgreSQL, update only `OPS_AGENT_DATABASE_URL` in `/opt/CCWBot/.ops-agent.env`, and run a no-state smoke test. Never copy the bot `DATABASE_URL`, Telegram token, Groq key, production `.env`, or production `.ops-agent.env` into reports or chat.

Rotate SSH access by replacing `/home/ccwbot_ops/.ssh/authorized_keys`, preserving owner `ccwbot_ops:ccwbot_ops` and mode `600`.

## Cleanup

Use `retention` for normal cleanup. If manual cleanup is required, remove only old files under `/opt/CCWBot/reports/ops-agent/bundles/` and `/opt/CCWBot/reports/ops-agent/reports/`. Do not remove `.env`, `.ops-agent.env`, database volumes, tracked project files, or live logs needed for incident analysis.

Generated bundles and reports are local operational artifacts. Keep `.ops-agent.env`, `reports/ops-agent/bundles/`, and `reports/ops-agent/reports/` ignored by Git; commit only safe templates such as `.ops-agent.env.example` and the wrapper scripts.
