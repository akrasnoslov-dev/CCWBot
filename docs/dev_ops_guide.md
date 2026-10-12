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

## Production access and privileges

**Verified production state as of 2026-10-11.** The operator's Windows workstation
uses exactly two working SSH aliases: `ccwbot-prod` (root emergency administrator)
and `ccwbot-prod-ops` (routine operator). The former
`ccwbot-prod-deploy` alias and login have been disabled.

| Principal | Realm | Verified current access | Status |
| --- | --- | --- | --- |
| `root` / `ccwbot-prod` | Linux/SSH | Full server administration and emergency recovery; root SSH key works with the SSH agent | **Active, break-glass only** |
| `ccwbot_ops` / `ccwbot-prod-ops` | Linux/SSH | Root-owned `ccwbot-ops-agent-collect` and the four exact `ccwbot-deploy-safe` actions: `status`, `backup`, `deploy`, `rollback`. No raw Docker, arbitrary sudo, secret reads or repository writes | **Active, only daily operator** |
| `ccwbot_deploy` | Linux | Old deployment account: SSH authorized keys removed from its home, login shell `/usr/sbin/nologin`, password locked, old `/etc/sudoers.d/ccwbot-deploy` removed | **Disabled, OS record retained for rollback** |
| `ccwbot` | PostgreSQL | Runtime DB login, **superuser** in the observed production `pg_roles` metadata; not an SSH account | Active; high privilege deserves a separate DB-hardening review |
| `ccwbot_investigator` | PostgreSQL | Separate forensic DB login, not superuser, no CREATE ROLE/DB in production role metadata; intended read-only access through a controlled tunnel | Retained; verify session read-only/grants before SQL |
| `ccwbot_ops_reader` | PostgreSQL | Separate collector DB login, not superuser, no CREATE ROLE/DB in production role metadata | Retained; use only for ops-agent |

**Account count:** two active human-operable SSH logins (root and
`ccwbot_ops`), one disabled historical Linux account retained for rollback,
and three separate PostgreSQL identities. SSH aliases are connection names, not
additional server roles; the Docker ops-agent service is not a human login.
The PostgreSQL `rolsuper`, `rolcreatedb` and `rolcreaterole` attributes were
checked on the VPS, but the complete live SQL grant matrix was **not** audited.

**Completed and verified on 2026-10-11:** root inventory confirmed only root,
`ccwbot_ops` and `ccwbot_deploy` as local non-system Linux users.
Root-owned `/etc/sudoers.d/ccwbot-operator-deploy` (mode 0440)
was installed from the reviewed four-action policy and passed `visudo`
validation. The existing `ccwbot_ops` collector rule remains.
The operator's safe status command succeeds; unauthorized `sudo /usr/bin/id`,
raw Docker sudo and extra deploy arguments fail; `ccwbot_ops` has only
the ordinary `users` supplementary group. The legacy login and sudo rule
were disabled only after those positive and negative tests. Follow-up SSH
probes confirmed root and ops logins succeed, while the old deploy SSH login
fails. No app image was deployed, no migrations were run, and runtime
`main` was not changed. Live policy installation was a separately
owner-authorized access-control change, not a bot-code release.

Rollback artifacts (legacy sudoers, authorized keys, original shell information
and password-lock state) are stored **only on the VPS under**
`/root/ccwbot-operator-migration-20261011/` (root-owned 0700), not in
Git or chat. Do not delete these until the migration has been stable and
separately reviewed.

### Two-login cutover procedure and rollback (completed 2026-10-11)

This is an explicit **security tradeoff**: the operator will be able to invoke
both diagnostics and fixed deploy/rollback commands. Separation between
diagnostics and deployment is reduced, while per-command sudo, root-owned
wrappers, no Docker group and no source-write privileges remain mandatory.
Do **not** replace them with `NOPASSWD: ALL`, unrestricted shell or Docker
group membership.

1. **Inventory first, under a working root SSH session.** Inspect `getent
   passwd` for the two limited OS users, `id -nG`, `sudo -l -U`, installed
   `/etc/sudoers.d/` entries, account shell/authorized-key status, trusted
   path ownership, installed wrapper hashes, cron jobs and systemd service
   owners. Verify production backup and root break-glass login before proceeding.
   Do not display secrets or SSH private keys. Separately inspect PostgreSQL
   `pg_roles` and read-only grants; do not drop or merge DB accounts.
2. **Prepare, do not replace the existing deploy path.** After separate owner
   approval for a narrowly scoped access-policy rollout or a reviewed production
   release, install
   `scripts/ccwbot-operator-deploy.sudoers` as a root-owned 0440 file in
   `/etc/sudoers.d/ccwbot-operator-deploy.tmp`; validate it with
   `visudo -cf`, atomically rename it to
   `/etc/sudoers.d/ccwbot-operator-deploy`, and run `visudo -c`. Keep
   the existing `ccwbot_deploy` sudoers and login intact during tests.
   The existing `/etc/sudoers.d/ccwbot_ops` collector rules remain intact.
3. **Positive checks as `ccwbot_ops`:** `sudo -n
   /usr/local/bin/ccwbot-deploy-safe status` and `sudo -n
   /usr/local/bin/ccwbot-ops-agent-collect --status latest`. Verify
   corresponding SSH alias login using key-based authentication. Do not test
   `deploy`, `backup` or `rollback` merely to validate permissions.
4. **Negative checks as `ccwbot_ops`:** `sudo -n /usr/bin/id`,
   `sudo -n /usr/bin/docker ps`, and `sudo -n
   /usr/local/bin/ccwbot-deploy-safe deploy extra` must be rejected;
   `id -nG` must omit `docker` and unrestricted sudo groups; direct
   reads of `/opt/CCWBot/.env` and `.ops-agent.env`, writes to trusted
   repo/wrapper paths, and raw Docker use must all fail. Inspect `sudo -l`
   for unintended privileges and verify forensic database access remains
   read-only, as described below.
5. **Cut over only after all checks pass.** Use `ccwbot-prod-ops` as the
   normal operator SSH alias and `ccwbot-prod` for root recovery.
   Confirm no job or external automation still logs in as `ccwbot_deploy`.
   Then disable that account's SSH/login shell and key access (do not delete
   its home/keys immediately), retire the old deploy-only sudoers entry and
   remove the unused `ccwbot-prod-deploy` alias from the operator's local
   SSH config. Keep documented recovery steps and a root session available.
6. **Rollback:** use root access to restore the recorded prior deploy user
   shell, authorized-key access and root-owned original sudoers policy;
   remove only the new operator-deploy sudoers file, then re-run positive
   and negative checks. Never treat an SSH connection failure as permission
   proof; stop rather than guessing.

The separately installed root-owned safe wrappers and sudoers are **not**
automatically updated by a Git merge or normal Docker deployment. The
reviewed operator-deploy sudoers source was installed by a separately authorized
root administration action on 2026-10-11; future code or sudoers changes
still require separate installation and verification.
The canonical ops-agent permission model stays in
`ops_agent/README.md`, and DB investigation rules stay in
`docs/observability.md`.

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

**Current SSH deployment identity:** `ccwbot_ops` through
`ccwbot-prod-ops`. It can run exactly the four argument-matched, root-owned
`/usr/local/bin/ccwbot-deploy-safe` actions `status`, `backup`,
`deploy`, `rollback`, plus the existing ops-agent collection wrapper.
The live sudoers entries are `/etc/sudoers.d/ccwbot-operator-deploy` and
`/etc/sudoers.d/ccwbot_ops`. The old `ccwbot_deploy` login and sudoers
rule have been disabled; `scripts/ccwbot-deploy.sudoers` is retained as a
**historical rollback reference only**. Never grant unrestricted shell/root
sudo, Docker access, repository write access or `NOPASSWD: ALL`.

The tracked scripts/ccwbot-deploy-safe.sh is NOT the installed wrapper.
Git checkout, merge and ordinary deploy do not replace /usr/local/bin or sudoers.
Always check installed checksum and provenance before separately approved
installation; never assume the live script matches the GitHub PR.

### Security contract

- Requires root, fixed origin, clean main checkout, and root-owned,
  non-group/other-writable, non-symlink trusted paths: /opt, repository,
  .git and its config, scripts/backup_postgres.sh, Dockerfile, Compose,
  the installed /usr/local/bin/ccwbot-deploy-safe and its /usr ancestry.
  Keep all ancestors and descendants inaccessible for writes by the deploy user.
  /opt/backups must be root-owned, non-symlinked and not writable by others.
  Git's core.hooksPath is forced to /dev/null by wrapper-owned environment
  overrides: a repository post-merge hook must never execute as root.
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
- Compose uses the fixed /opt/CCWBot/docker-compose.yml and project name ccwbot.
  On failed deploy recovery and rollback, --remove-orphans removes obsolete
  candidate-only containers; never use this during concurrent ops-agent
  collection under the same Compose project because its overlay containers
  could be treated as orphans. Schedule operations separately.
- After a failed build, Compose configuration, restart or health check,
  the wrapper tries to restore the previous checkout AND service, keeps old
  rollback state, and still exits with failure. Recovery can also fail:
  stop automated retries and escalate to manual operator recovery.
- Rollback validates a two-SHA ancestor record, exact current deployed HEAD
  and fresh backup. It clears the record only after successful service health.
  On failed rollback recovery, the record remains for manual inspection.
- Status only reads runtime state; backup/deploy/rollback change production.
  All state-changing commands require a separate explicit approval.

### Legacy wrapper installation (historical, not routine after operator cutover)

The commands below document the **old deploy-user** installation, including
its retired sudoers file. **Do not run this block on current production**:
it would reinstall permissions for the disabled `ccwbot_deploy` account.
Only an explicitly approved rollback may restore that legacy rule.
For future wrapper updates, separately authorize the production release,
verify the correct Git HEAD and installed/source drift, and install only
the current `ccwbot_ops` operator policy, using the complete permission
checks above.

    cd /opt/CCWBot
    git status --short
    git rev-parse HEAD
    bash -n scripts/ccwbot-deploy-safe.sh
    sha256sum scripts/ccwbot-deploy-safe.sh /usr/local/bin/ccwbot-deploy-safe
    stat -c '%u %a %n' /usr /usr/local /usr/local/bin /usr/local/bin/ccwbot-deploy-safe /opt /opt/backups /opt/CCWBot /opt/CCWBot/.git /opt/CCWBot/.git/config /opt/CCWBot/scripts /opt/CCWBot/scripts/backup_postgres.sh /opt/CCWBot/docker-compose.yml /opt/CCWBot/Dockerfile /run
    install -o root -g root -m 755 scripts/ccwbot-deploy-safe.sh /usr/local/bin/ccwbot-deploy-safe
    install -o root -g root -m 440 scripts/ccwbot-deploy.sudoers /etc/sudoers.d/ccwbot-deploy.tmp
    visudo -cf /etc/sudoers.d/ccwbot-deploy.tmp
    mv /etc/sudoers.d/ccwbot-deploy.tmp /etc/sudoers.d/ccwbot-deploy
    visudo -cf /etc/sudoers.d/ccwbot-deploy

Before install: confirm /run is protected and the root-owned checkout is
not writable by other users. Never overwrite a production .env or modify
rollback state during installation.

### Read-only permission verification

The cutover is complete: use **`ccwbot-prod-ops`** for all normal
permission verification. The old alias appears below only as a pre-cutover
historical reference. Replace `<deploy-ssh-alias>` with `ccwbot-prod-ops`:

    # Current: ccwbot-prod-ops
    # Historical before cutover: ccwbot-prod-deploy
    ssh -o BatchMode=yes <deploy-ssh-alias> 'sudo -n -l'
    ssh -o BatchMode=yes <deploy-ssh-alias> 'sha256sum /usr/local/bin/ccwbot-deploy-safe'
    ssh -o BatchMode=yes <deploy-ssh-alias> 'sudo -n /usr/local/bin/ccwbot-deploy-safe status'
    ssh -o BatchMode=yes <deploy-ssh-alias> 'sudo -n /usr/bin/id' # MUST FAIL
    ssh -o BatchMode=yes <deploy-ssh-alias> 'sudo -n /usr/bin/docker ps' # MUST FAIL
    ssh -o BatchMode=yes <deploy-ssh-alias> 'sudo -n /usr/local/bin/ccwbot-deploy-safe deploy extra' # MUST FAIL
    ssh -o BatchMode=yes <deploy-ssh-alias> 'id -nG' # MUST NOT include docker

Never test this by triggering backup, deploy or rollback. A failed SSH
connection is UNKNOWN, not proof that production is least privileged.

### Future approved deployment and incident recovery

Only for an approved main release with no migrations or ops_agent files:

    # Current SSH alias: ccwbot-prod-ops (old ccwbot-prod-deploy disabled).
    ssh -o BatchMode=yes <deploy-ssh-alias> 'sudo -n /usr/local/bin/ccwbot-deploy-safe deploy'

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
