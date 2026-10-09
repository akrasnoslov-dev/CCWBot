# Dev Ops Guide

Production runs from `main` on the Hetzner VPS at `/opt/CCWBot`. Local development runs from
`dev` or a focused branch based on `dev`.

## Environment Rules

- Local and production `.env` files are environment-local and must never be committed.
- Local development uses a development Telegram bot token.
- Production uses a separate production Telegram bot token.
- Never use the production bot token locally.
- Never overwrite production `.env`.
- PostgreSQL and the bot health endpoint are bound to localhost by Compose.

For local setup and verification, use `docs/development.md`.

## PostgreSQL Backups

Production database backups live under `/opt/backups`. Existing backups may already be present
there; do not delete or move them unless the operator has verified they are obsolete.

The repo-managed manual backup command is:

```bash
cd /opt/CCWBot
sudo scripts/backup_postgres.sh
```

The script writes compressed SQL backups named:

```text
/opt/backups/ccwbot-postgres-YYYYMMDDTHHMMSSZ.sql.gz
```

It keeps the newest 14 matching `ccwbot-postgres-*.sql.gz` files by default, never deletes
unrelated files in `/opt/backups`, creates files with owner-only permissions, and does not print
`.env` values or connection strings. Override retention only when needed:

```bash
sudo CCWBOT_BACKUP_RETENTION_COUNT=14 scripts/backup_postgres.sh
```

Verify the latest backup exists:

```bash
sudo find /opt/backups -maxdepth 1 -type f -name 'ccwbot-postgres-*.sql.gz' -printf '%TY-%Tm-%Td %TH:%TM %p\n' | sort | tail -n 1
```

Verify a backup file is readable:

```bash
gzip -t /opt/backups/ccwbot-postgres-YYYYMMDDTHHMMSSZ.sql.gz
```

Test a restore only on an isolated local PostgreSQL instance, never a shared or production
cluster. Run this as one fail-fast shell block; it creates a unique disposable database and removes
it only after the restore check succeeds:

```bash
set -euo pipefail
restore_db="ccwbot_restore_test_$(date +%Y%m%dT%H%M%S)"
createdb "$restore_db"
gzip -dc /opt/backups/ccwbot-postgres-YYYYMMDDTHHMMSSZ.sql.gz | psql --set ON_ERROR_STOP=1 "$restore_db"
psql "$restore_db" -c "select count(*) from users;"
dropdb "$restore_db"
```

Before production migrations, verify a recent backup exists or create a fresh one. If the VPS is
lost but `/opt/backups` is available from server storage or an external copy, provision a new VPS,
clone the repository, restore the latest verified backup into PostgreSQL, recreate the production
`.env` manually, run any required migrations, then start the bot and verify `/health` and Telegram.

Scheduling is a manual operator step. Example crontab:

```cron
15 2 * * * cd /opt/CCWBot && /usr/bin/sudo /opt/CCWBot/scripts/backup_postgres.sh >> /var/log/ccwbot-backup.log 2>&1
```

Example systemd service template:

```ini
[Unit]
Description=CCWBot PostgreSQL backup

[Service]
Type=oneshot
WorkingDirectory=/opt/CCWBot
ExecStart=/opt/CCWBot/scripts/backup_postgres.sh
```

Example systemd timer template:

```ini
[Unit]
Description=Run CCWBot PostgreSQL backup daily

[Timer]
OnCalendar=*-*-* 02:15:00
Persistent=true

[Install]
WantedBy=timers.target
```

Install either cron or systemd on the VPS manually; this repository does not auto-install a backup
schedule.

## Read-Only Forensic Database Access

Interactive production investigations by Codex or an operator should use the dedicated
`ccwbot_investigator` PostgreSQL role through the existing SSH tunnel to
`127.0.0.1:15433`. Do not use the application owner role or a PostgreSQL superuser for normal
forensics.

Verify every new investigation session before evidence queries:

```sql
SELECT current_user;
SHOW transaction_read_only;
SHOW default_transaction_read_only;
```

Expected values are `ccwbot_investigator`, `on`, and `on`. For an explicit transaction,
use `BEGIN READ ONLY;` and finish with `ROLLBACK;`.

The minimum current forensic evidence set requires `SELECT` access to:

- `market_events`
- `event_ai_analyses`
- `llm_usage_logs`
- `market_heartbeats`
- `alerts`
- `alert_delivery_outcomes`
- `market_reports`

If a required query returns `permission denied`, treat that as an access-provisioning gap.
Do not switch to a more privileged role. An operator/admin must apply any required `GRANT SELECT`
outside the investigator session, after which the investigator reconnects and reruns the
read-only verification above. Additional tables should receive explicit `SELECT` only when an
investigation actually requires them.

Never print or commit the investigator password, connection string, SSH private key, or expanded
environment values.

## Deploying Ops-Agent Changes

Ops-agent code does not reach production the way bot code does. Two steps are easy to miss, and
both have caused real deployment gaps where an operator believed a fix was live and it was not.

**1. The `ops-agent` image must be rebuilt explicitly.** The ops-agent is not declared in the
root `docker-compose.yml` at all — it lives in the `ops_agent/docker-compose.ops-agent.yml`
overlay under the `ops` profile. A plain `docker compose up -d --build`, which is what the deploy
checklist runs, therefore never sees the service and never rebuilds it. After any change under
`ops_agent/`, rebuild it explicitly with the overlay:

```bash
cd /opt/CCWBot
docker compose -f docker-compose.yml -f ops_agent/docker-compose.ops-agent.yml build ops-agent
```

Until that runs, collection keeps using the previously built image: old queries, old collectors,
old detectors. The bundle will look healthy and current, because nothing reports which image
version produced it.

**2. The host wrapper is not updated by Git.** `/usr/local/bin/ccwbot-ops-agent-collect` is an
installed copy. `git pull` updates only `ops_agent/scripts/ccwbot-ops-agent-collect` in the repo,
and `docker compose up -d --build` never touches `/usr/local/bin` at all. Reinstall it manually
whenever that script changes:

```bash
sudo install -m 755 /opt/CCWBot/ops_agent/scripts/ccwbot-ops-agent-collect /usr/local/bin/ccwbot-ops-agent-collect
```

A stale installed wrapper was the root cause of the July 2026 partial-bundle streak.

Checklist after deploying an ops-agent change:

1. Rebuild the image with the overlay (command above).
2. Reinstall the host wrapper if `ops_agent/scripts/ccwbot-ops-agent-collect` changed.
3. Collect a short no-state bundle and confirm the expected new collectors or detectors appear.
4. Confirm `Collector Status` lists no failures.

## Ops-Agent Diagnostics

The production ops-agent wrapper should point at the repo-managed `ops_agent/` source. Use only the
safe wrapper for collection:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since <UTC> --until now
```

Do not run raw deployment, restart, migration, environment-printing, or secret-reading commands as
part of diagnostics. A partial bundle means at least one collector failed; inspect the collector
status table and rerun after the named collector is fixed.

Both deployment steps that ops-agent changes require — the explicit image rebuild and the manual
host-wrapper reinstall — are documented above under **Deploying Ops-Agent Changes**.

For post-deploy Event Alert verification, record the UTC deploy start, run the backup and migration
before starting the new bot image, explicitly rebuild the `ops-agent` overlay image, and wait for at
least one fresh News Intelligence operation to finish. Then collect a deploy-scoped no-state bundle:

```bash
sudo /usr/local/bin/ccwbot-ops-agent-collect --since <deploy-start-UTC> --until now --no-state-update
```

Review only the sanitized report context and detector summary. Confirm `/health` is OK,
`market_events_without_alert_deliveries` is clear or has only explicit expected skip reasons, no
new critical/high unexplained Event Alert detector is triggered, Collector Status is complete, and
LLM reconciliation/coverage evidence is present with correlated operations greater than zero,
missing operation IDs equal to zero, and reconciliation gaps equal to zero. Confirm basic Telegram
functionality in a private smoke check without recording user ids or private text. If rollback is
required, roll back the application while leaving the additive outcome table in place; do not
downgrade migration 0029 while code may still write to it.

## Production Deploy

Deploy tracked-file changes only through Git:

```bash
cd /opt/CCWBot
git status --short
git fetch origin
git branch --show-current
git checkout main
git pull --ff-only
sudo scripts/backup_postgres.sh
docker compose run --rm migrate  # only when migrations are needed
docker compose up -d --build
docker compose ps
docker compose logs -f
```

Stop before `git checkout main` if `git status --short` prints anything, the current branch is not
the expected deployment branch, or fetching/pulling reports a conflict. Resolve that state outside
the deploy runbook; do not overwrite tracked or environment-local changes on the VPS.

After every deploy:

1. Check container status.
2. Check bot logs.
3. Check `/health` from the VPS.
4. Verify basic Telegram functionality.

When a release changes LLM model defaults, inspect the existing production `.env` before
restarting. A pinned value overrides the code default. Edit only the affected variables in place;
never copy `.env.example` over production `.env`. Use `llm_usage.md` for current model and
telemetry guidance, then inspect the sanitized `ops_event=llm_config` startup lines after restart.

Normal bot restarts do not run migrations. For migrations, test locally first, confirm CI migration
validation passed, verify a current backup, run `docker compose run --rm migrate` explicitly, then
start or restart the bot.

## Non-interactive, least-privilege bot deploys

The ccwbot_deploy SSH account uses its own dedicated key and must not belong
to the Docker group or write to /opt/CCWBot. Its private key stays with the
operator. The installed root-owned /usr/local/bin/ccwbot-deploy-safe accepts
exactly four actions: status, backup, deploy, rollback. No extra arguments.
scripts/ccwbot-deploy.sudoers allowlists only these four exact commands. Never
grant shell/root sudo, Docker access, repository write access, or NOPASSWD: ALL.

The tracked scripts/ccwbot-deploy-safe.sh is NOT the installed wrapper.
Git checkout, merge and ordinary deploy do not replace /usr/local/bin or sudoers.
Always check installed checksum and provenance before separately approved
installation; never assume the live script matches the GitHub PR.

### Security contract

- Requires root, fixed origin, clean main checkout, and root-owned,
  non-group/other-writable, non-symlink trusted paths: /opt, repository,
  .git and its config, scripts/backup_postgres.sh, Dockerfile and Compose.
  Keep all ancestors and descendants inaccessible for writes by the deploy user.
- Root-controlled /run and a root-owned 0700 directory
  /run/ccwbot-deploy-safe.lock hold the flock on a directory descriptor.
  No predictable writable /run/lock file is created or truncated.
- /var/lib/ccwbot-deploy is root-owned 0700. The last-deploy record is 0600,
  rejects symlinks and is atomically updated only after successful health.
- The effective published port comes from docker compose config --format json.
  The binding must be exactly 127.0.0.1. The JSON is piped to a parser and
  must never be logged or printed: it can contain expanded credentials.
  Only HTTP success AND JSON with top-level status == "ok" pass the health
  check; HTTP 200 with degraded, malformed JSON or wrong port must fail.
- Deploy requires origin/main to be a descendant, rejects migrations and
  ops_agent changes, and verifies a fresh gzip backup before Git advance.
  When HEAD already equals origin/main, it performs only health verification,
  does not backup/rebuild/restart, and preserves the last good rollback record.
- After a failed build, Compose configuration, restart or health check,
  the wrapper tries to restore the previous checkout AND service, keeps old
  rollback state, and still exits with failure. Recovery can also fail:
  stop automated retries and escalate to manual operator recovery.
- Rollback validates a two-SHA ancestor record, exact current deployed HEAD
  and fresh backup. It clears the record only after successful service health.
  On failed rollback recovery, the record remains for manual inspection.
- Status only reads runtime state; backup/deploy/rollback change production.
  All state-changing commands require a separate explicit approval.

### Installation (requires separate production authorization)

After the fixed code has reached an approved, reviewed main release,
an authorized root operator must verify the correct Git HEAD, filesystem
ownership/modes and installed/source drift before running the following.
PR #301 does not grant approval to execute these commands.

    cd /opt/CCWBot
    git status --short
    git rev-parse HEAD
    bash -n scripts/ccwbot-deploy-safe.sh
    sha256sum scripts/ccwbot-deploy-safe.sh /usr/local/bin/ccwbot-deploy-safe
    stat -c '%u %a %n' /opt /opt/CCWBot /opt/CCWBot/.git /opt/CCWBot/.git/config /opt/CCWBot/scripts /opt/CCWBot/scripts/backup_postgres.sh /opt/CCWBot/docker-compose.yml /opt/CCWBot/Dockerfile /run
    install -o root -g root -m 755 scripts/ccwbot-deploy-safe.sh /usr/local/bin/ccwbot-deploy-safe
    install -o root -g root -m 440 scripts/ccwbot-deploy.sudoers /etc/sudoers.d/ccwbot-deploy.tmp
    visudo -cf /etc/sudoers.d/ccwbot-deploy.tmp
    mv /etc/sudoers.d/ccwbot-deploy.tmp /etc/sudoers.d/ccwbot-deploy
    visudo -cf /etc/sudoers.d/ccwbot-deploy

Before install: confirm /run is protected and the root-owned checkout is
not writable by other users. Never overwrite a production .env or modify
rollback state during installation.

### Read-only permission verification

    ssh -o BatchMode=yes ccwbot-prod-deploy 'sudo -n -l'
    ssh -o BatchMode=yes ccwbot-prod-deploy 'sha256sum /usr/local/bin/ccwbot-deploy-safe'
    ssh -o BatchMode=yes ccwbot-prod-deploy 'sudo -n /usr/local/bin/ccwbot-deploy-safe status'
    ssh -o BatchMode=yes ccwbot-prod-deploy 'sudo -n /usr/bin/id' # MUST FAIL
    ssh -o BatchMode=yes ccwbot-prod-deploy 'sudo -n /usr/local/bin/ccwbot-deploy-safe deploy extra' # MUST FAIL
    ssh -o BatchMode=yes ccwbot-prod-deploy 'id -nG' # MUST NOT include docker

Never test this by triggering backup, deploy or rollback. A failed SSH
connection is UNKNOWN, not proof that production is least privileged.

### Future approved deployment and incident recovery

Only for an approved main release with no migrations or ops_agent files:

    ssh -o BatchMode=yes ccwbot-prod-deploy 'sudo -n /usr/local/bin/ccwbot-deploy-safe deploy'

The command above is a production change; do not run it during diagnostics.
On failure, inspect branch/HEAD, Docker status, the JSON /health status,
and backup evidence through approved read-only means. If automatic recovery
reports success, the attempted deploy STILL FAILED. If it reports recovery
failure, stop retrying and hand off to a separately authorized manual
operator recovery. Never force-reset, reinstall, change sudoers, or run
migrations as part of read-only diagnosis. Rollback also requires approval.

After an authorized release, run a private Telegram smoke test and sanitized
ops-agent report checks. See docs/release_checklist.md for release gates and
the distinct ops-agent overlay image/host-wrapper procedure.

## Dependency updates

Scheduled Dependabot version-update PRs are disabled. In repository history they created mostly
unused update PRs, and grouped Python updates can also produce incompatible pin sets.

Handle dependency upgrades as explicit maintenance work:
1. choose a small compatible upgrade set;
2. review changelogs and compatibility risk;
3. update pins intentionally;
4. run the full repository verification before merge.

Dependabot security alerts/security-update settings are separate GitHub repository settings. This
repository documentation does not claim they are enabled or disabled; verify them in GitHub when
security maintenance is needed.
