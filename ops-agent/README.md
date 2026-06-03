# CCWBot Ops-Agent

`ops-agent` is a local, on-demand diagnostic bundle collector for Codex. It does not use an LLM, does not expose a port, does not mount the Docker socket, does not apply fixes, and does not provide a raw SQL endpoint.

The Compose overlay must not pass the bot `.env` into the container. Only explicit `OPS_AGENT_*` variables are allowed.

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

Preferred production access is through a root-owned wrapper:

```bash
sudo tee /usr/local/bin/ccwbot-ops-agent-collect >/dev/null <<'EOF'
#!/bin/sh
set -eu
cd /opt/CCWBot
exec docker compose -f docker-compose.yml -f ops-agent/docker-compose.ops-agent.yml run --rm ops-agent collect --period auto "$@"
EOF
sudo chown root:root /usr/local/bin/ccwbot-ops-agent-collect
sudo chmod 755 /usr/local/bin/ccwbot-ops-agent-collect
```

Allow only that wrapper through sudoers:

```bash
sudo visudo -f /etc/sudoers.d/ccwbot_ops
```

Use this entry:

```text
ccwbot_ops ALL=(root) NOPASSWD: /usr/local/bin/ccwbot-ops-agent-collect
```

Filesystem permission checks:

```bash
sudo -u ccwbot_ops test ! -r /opt/CCWBot/.env
sudo -u ccwbot_ops test ! -w /opt/CCWBot/main.py
sudo -u ccwbot_ops test ! -w /opt/CCWBot/docker-compose.yml
sudo install -d -m 770 -o root -g ccwbot_ops /opt/CCWBot/reports/ops-agent
sudo -u ccwbot_ops test -w /opt/CCWBot/reports/ops-agent
```

Verify `ccwbot_ops` can write only under `/opt/CCWBot/reports/ops-agent` and cannot write tracked files. If any check fails, stop and fix permissions before collecting.

Normal production collection:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect
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
sudo /usr/local/bin/ccwbot-ops-agent-collect
```

Do not print, paste, or publish `docker compose config` output from production. Compose may interpolate `OPS_AGENT_DATABASE_URL` or other environment-local values into that output.

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

To disable shell collection access immediately:

```bash
sudo rm -f /etc/sudoers.d/ccwbot_ops
sudo chmod 000 /usr/local/bin/ccwbot-ops-agent-collect
```

To revoke the read-only database role:

```sql
REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM ccwbot_ops_reader;
REVOKE USAGE ON SCHEMA public FROM ccwbot_ops_reader;
REVOKE CONNECT ON DATABASE ccwbot FROM ccwbot_ops_reader;
ALTER ROLE ccwbot_ops_reader NOLOGIN;
```

## Credential Rotation

Rotate the `ccwbot_ops_reader` password in PostgreSQL, update only `OPS_AGENT_DATABASE_URL` in the environment-local production `.env`, and run a no-state smoke test. Never copy the bot `DATABASE_URL`, Telegram token, Groq key, or production `.env` into reports or chat.

Rotate SSH access by replacing `/home/ccwbot_ops/.ssh/authorized_keys`, preserving owner `ccwbot_ops:ccwbot_ops` and mode `600`.

## Cleanup

Use `retention` for normal cleanup. If manual cleanup is required, remove only old files under `/opt/CCWBot/reports/ops-agent/bundles/` and `/opt/CCWBot/reports/ops-agent/reports/`. Do not remove `.env`, database volumes, tracked project files, or live logs needed for incident analysis.
