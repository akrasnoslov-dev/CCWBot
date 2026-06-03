# CCWBot Ops-Agent

`ops-agent` is a local, on-demand diagnostic bundle collector for Codex. It does not use an LLM, does not expose a port, does not mount the Docker socket, does not apply fixes, and does not provide a raw SQL endpoint.

The Compose overlay must not pass the bot `.env` into the container. Only explicit `OPS_AGENT_*` variables are allowed.

## Production Read-Only Setup

Create a dedicated OS/service account on the VPS if operators need shell access. It should only be able to run the collection command, read mounted logs, and write under `/opt/CCWBot/reports/ops-agent/`. Do not give it bot token access, Docker socket access beyond the required Compose run, or write access to tracked project files.

Normal production collection:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent collect --period auto
```

The command prints one JSON object with the generated bundle path. Codex should read the bundle in this order:

1. `CODEX_INSTRUCTIONS.md`
2. `manifest.json`
3. `bundle_summary.md`
4. `detectors/detector_summary.md`
5. `detectors/detector_results.json`
6. `redaction_report.json`
7. `limits.json`

Final report writing remains Codex's responsibility using `docs/ops-agent-report-codex-prompt.md`. Save final reports under `/opt/CCWBot/reports/ops-agent/reports/`, then run `mark-report-success` only after a complete bundle has produced a written report.

Log evidence is period-aware when CCWBot timestamps are parseable. Bundles separate timestamped period-matched excerpts from unscoped tail-context excerpts and include skipped/unparseable counts. Period-matched logs are stronger evidence for the requested report period.

Detector `unknown` means evidence is missing or inconclusive, not healthy. Market events without deliveries are classified into expected no-delivery, LLM failure/rate-limit, `should_alert=true` delivery gaps, and unknown buckets where the available schema cannot prove the reason.

First-time DB setup uses a read-only PostgreSQL role:

```bash
docker compose exec postgres psql -U ccwbot -d ccwbot -f /path/to/ops-agent/sql/create_readonly_role.sql
```

Set `OPS_AGENT_DATABASE_URL` in the production `.env` with the `ccwbot_ops_reader` role:

```text
OPS_AGENT_DATABASE_URL=postgresql+asyncpg://ccwbot_ops_reader:<password>@postgres:5432/ccwbot
```

The `.env.example` values are placeholders only and must not contain real passwords.

By default, the health collector uses the production-safe Compose `bot` service name:

```text
OPS_AGENT_HEALTH_URL=http://bot:8080/health
```

For local Windows/Docker Desktop testing, override it in `.env` if the bot is reachable through the host:

```text
OPS_AGENT_HEALTH_URL=http://host.docker.internal:8080/health
```

## Report Workflow

1. Run collection with the safe production command.
2. Read the printed JSON and open the bundle path.
3. Have Codex write the final Markdown report under `/opt/CCWBot/reports/ops-agent/reports/`.
4. Run `validate-bundle` against the bundle.
5. Run `mark-report-success` only after the written report exists. The command rejects paths outside ops-agent report/bundle directories and refuses tampered bundles.

Safe production command:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent collect --period auto
```

Smoke test without advancing state:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent collect --since 2026-06-01T00:00:00Z --until 2026-06-01T01:00:00Z --no-state-update
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent validate-bundle <bundle-path>
```

Mark a completed report successful:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent mark-report-success --bundle /app/reports/ops-agent/bundles/<bundle-id> --report /app/reports/ops-agent/reports/<report-file>.md
```

Optional duplicate market-event bucket size:

```text
OPS_AGENT_DUPLICATE_MARKET_EVENT_BUCKET_MINUTES=15
```

Retention is automatic after collection and can be run manually:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent retention
```

## Emergency Disable

Stop using the overlay command and remove or unset `OPS_AGENT_DATABASE_URL`. This only disables future ops-agent DB collection; it does not change bot runtime behavior. Do not restart production services solely for ops-agent unless a separate deployment requires it.

## Credential Rotation

Rotate the `ccwbot_ops_reader` password in PostgreSQL, update only `OPS_AGENT_DATABASE_URL` in the environment-local production `.env`, and run a no-state smoke test. Never copy the bot `DATABASE_URL`, Telegram token, Groq key, or production `.env` into reports or chat.

## Cleanup

Use `retention` for normal cleanup. If manual cleanup is required, remove only old files under `/opt/CCWBot/reports/ops-agent/bundles/` and `/opt/CCWBot/reports/ops-agent/reports/`. Do not remove `.env`, database volumes, tracked project files, or live logs needed for incident analysis.
