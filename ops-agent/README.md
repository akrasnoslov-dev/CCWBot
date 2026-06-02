# CCWBot Ops-Agent

`ops-agent` is a local, on-demand diagnostic bundle collector for Codex. It does not use an LLM, does not expose a port, does not mount the Docker socket, does not apply fixes, and does not provide a raw SQL endpoint.

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

First-time DB setup:

```bash
docker compose exec postgres psql -U ccwbot -d ccwbot -f /path/to/ops-agent/sql/create_readonly_role.sql
```

Set `OPS_AGENT_DATABASE_URL` in the production `.env` with the `ccwbot_ops_reader` role:

```text
OPS_AGENT_DATABASE_URL=postgresql+asyncpg://ccwbot_ops_reader:<password>@postgres:5432/ccwbot
```

Smoke test:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent collect --since 2026-06-01T00:00:00Z --until 2026-06-01T01:00:00Z --no-state-update
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent validate-bundle <bundle-path>
```

Optional duplicate market-event bucket size:

```text
OPS_AGENT_DUPLICATE_MARKET_EVENT_BUCKET_MINUTES=15
```

Retention is automatic after collection and can be run manually:

```bash
docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent retention
```
