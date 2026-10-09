# Release Checklist

Use this checklist for explicit `dev` -> `main` production release PRs.

## Before Opening The PR

1. Confirm the working tree is clean.
2. Confirm `dev` is up to date with `origin/dev`.
3. Review `origin/main...origin/dev` with name/status and stat output.
4. Confirm no `.env`, local state, cache, log, report, DB dump, or secret file is tracked.
5. Run required agents from `agents/routing.toml` for the release payload.
6. Delete only branches that are clearly merged or obsolete. Keep unclear branches.

## Required Verification

Run the default verification from `docs/development.md`. Use `.env.example` for Compose validation
when possible; do not paste expanded Compose output. `docker compose config` is not migration
verification.

For PRs that include Alembic migrations, also confirm:

```bash
python -m pytest tests/test_alembic_migrations.py -v
docker compose up -d postgres
docker compose run --rm migrate
```

CI also applies Alembic head to a temporary PostgreSQL service. That confirms basic migration
application and runs the ops-agent query-contract test against it, but it does not replace a fresh
production backup before real migrations.

## PR Description Must Include

Follow the PR-readiness and `Self-review / risk check` requirements in
`docs/codex_instructions.md`. This release checklist adds release-specific confirmation:

- Summary
- Files changed
- Behavior confirmation
- Database/schema confirmation
- Migration compatibility confirmation, when migrations are included
- Verification performed
- Manual verification status
- Protected files changed and why
- Agents used or not used
- Branch cleanup summary
- Known limitations and follow-ups

For sensitive releases, also confirm alert scope, recipient delivery behavior, LLM call
placement, payment/subscription impact, and no secrets exposed.

## Before Production Deploy

1. Confirm CI is green.
2. Confirm `/opt/backups` has a current backup, or create one with `sudo scripts/backup_postgres.sh`.
3. Merge `dev` into `main` through the release PR.
4. Deploy from Git on the VPS; do not edit tracked files manually.
5. Do not overwrite production `.env`.
6. Run `docker compose run --rm migrate` only when the release includes migrations.
7. Start or restart the bot with `docker compose up -d --build`.
8. After deploy, check containers, logs, health, and basic Telegram behavior.

## Secure deployment-wrapper release gate (PR #301)

1. Complete PR #301 review/CI/negative contract tests. Merge first into dev,
   then use a separately approved dev-to-main release. Git-tracked wrapper
   changes do not update the installed root-owned wrapper or sudoers.
2. Check the live installed checksum, ownership, mode, fixed sudo allowlist
   and production drift through read-only access. Treat inaccessible evidence
   as UNKNOWN, not PASS.
3. Require clean main, fast-forward history, verified backup, valid JSON
   health and preserved rollback state. Do not accept HTTP 200 alone.
4. Source promotion, wrapper installation, sudoers change, deploy and
   rollback are separate approvals. Do not chain them automatically.
5. The deployment account must lack Docker-group membership, repo writes,
   arbitrary sudo/shell and extra-argument privileges. Negative tests fail.

## Future release-specific checklist

### PR #296: Event Analysis medium reasoning

- Confirm PR SHA/base/CI and reasoning/default/override tests.
- Confirm no new schema/migration and no deterministic Event Alert cutoff.
- Before release, examine production env overrides without exposing secrets;
  pinned reasoning effort may override the shipped default.
- After explicit approval and deployment, verify sanitized LLM startup config,
  Event Analysis outcomes, false positives, coverage and cost/rate changes.
- Roll back code/config only via an authorized compatible release.

### Render changes

- Identify actual PR number and SHA before proposing a release. Run prompt
  and schema validation, rendering tests, provider usage/rate guards,
  recipient-safety and privacy checks. Require architecture, market pipeline,
  product-policy and relevant security reviewers from agents/routing.toml.
- Verify complete Telegram rendering and delivery, not just LLM success.
  Examine sanitized delivery outcomes and use a private smoke test.
- Document rollback compatibility with any schema changes.

### Observability changes

- Identify exact PR/SHA and distinguish bot-runtime from ops_agent changes.
- Require ops_observability_agent, security_review_agent and test_ci_agent
  for ops-agent code; verify redaction, no sensitive data in bundles,
  investigator SELECT-only access, collector isolation and freshness.
- Review the full changed-file list and migrations before selecting the
  deployment path. A green bot health check cannot prove fresh telemetry.
- Confirm fresh sanitized no-state bundle, complete Collector Status and
  expected new collectors/detectors, not only a green container.

### Mandatory ops-agent image and host-wrapper steps

The restricted deploy wrapper rejects changes under ops_agent/ or
alembic/versions/. For these use separately authorized manual release:

1. Verify backups and migration compatibility; migrations are explicit.
2. Rebuild ops-agent overlay after ops_agent sources change:

       docker compose -f docker-compose.yml -f ops_agent/docker-compose.ops-agent.yml build ops-agent

   Plain docker compose up -d --build does not rebuild that overlay.
3. If ops_agent/scripts/ccwbot-ops-agent-collect changes, explicitly
   reinstall /usr/local/bin/ccwbot-ops-agent-collect as root with separate
   operator authorization. Git checkout alone never replaces it.
4. Record built image identity, source revision and installed wrapper checksum.
5. Run a short sanitized no-state collection, verify status/freshness, and
   treat partial bundles as a release failure.

See docs/dev_ops_guide.md for detailed approved operator commands.
