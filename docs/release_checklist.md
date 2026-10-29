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

Run the default verification from `docs/development.md` for changed code. Use `.env.example`
for Compose validation when possible; never paste expanded Compose output.
For the release PR, verify green CI against the exact combined `dev` revision; do not rerun
an unchanged, already-green full local test suite or repeatedly poll completed CI just because
the same code is being promoted. If verification is missing, stale, or the release payload
has changed, rerun the applicable checks. `docker compose config` is not migration verification.

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

## Production Release: Minimal Safe Path

Classify the **exact** `main...dev` diff before choosing a deployment path.

- **Ordinary bot-only release:** no Alembic migrations, `ops_agent/` changes, installed
  wrapper/sudoers changes, or other infrastructure changes requiring manual work. Use the
  restricted `ccwbot-deploy-safe` path below.
- **Exception:** migrations, ops-agent, security/access-control, deployment infrastructure,
  or a confirmed runtime incident. Follow the applicable specialized sections here and in
  `docs/dev_ops_guide.md` with separate authorization. Do not force these changes through
  the restricted wrapper or omit their mandatory checks.

For an ordinary bot-only release:

1. Confirm reviewed diff, release PR readiness, and green CI for the exact release SHA.
   Merge `dev -> main` through the explicit release PR; merging and deploying are separate
   actions requiring their own authorization.
2. Read the current production state through the approved `status` command. If the running
   production revision already equals `origin/main` **and** health is OK, stop: no rebuild,
   restart, or duplicate backup.
3. After explicit deploy approval, use the current `ccwbot_ops` SSH identity and the
   installed restricted wrapper (not raw Docker or root commands):

   ```bash
   ssh -o BatchMode=yes ccwbot-prod-ops 'sudo -n /usr/local/bin/ccwbot-deploy-safe deploy'
   ```

   The wrapper enforces clean/fast-forward Git state, backup, build, health, and recovery
   checks. Do not separately repeat its backup, migration, Compose, or wrapper-permission
   workflow for a normal bot-only release. Never overwrite production `.env`.
4. Verify via read-only `status` that production HEAD matches `origin/main`, the bot
   and database are healthy, and `/health` returns valid JSON `status=ok`. Perform a
   small private Telegram smoke test of the changed path when possible. Read only targeted,
   sanitized logs/outcomes if a check fails or the particular changed behavior requires them.
5. Report the deployed SHA, CI result, health/smoke results, and any unverified checks.
   Do not infer functional quality from a green health endpoint alone.

**Do not automatically** launch an ops-agent collection, wait for unrelated News Intelligence
cycles, rebuild the ops-agent overlay, create a full diagnostics report, or poll multiple
collectors after an ordinary release. Escalate to a **targeted** check, then to a deploy-scoped
sanitized ops-agent report only when an observed anomaly, high-risk release-specific validation
requirement, observability change, or explicit owner request justifies it. Keep collection
separate from deployment to avoid Compose orphan conflicts.

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

### LLM routing v2 free-only rollout

- This release includes migration `0033_openai_budget`; take the required backup and verify the
  PostgreSQL migration before bot startup.
- Require separate production approval. Deploy with `OPENAI_ENABLED=false`; a stray key must not
  activate paid calls. Do not set pricing or purchase credits as part of the free-only rollout.
- Inspect sanitized `ops_event=llm_config` output for Event Analysis (Groq 120B -> disabled OpenAI
  -> Cloudflare), Render/News/Heartbeat (Groq 20B -> disabled OpenAI -> Cloudflare), and Reports
  (Groq 20B -> disabled OpenAI -> data-only). Reject stale Gemini/Qwen overrides.
- Smoke all six feature families, confirm provider/model attribution and application validators,
  and confirm zero OpenAI attempt rows. Observe timeout/rate-limit/budget skips for the agreed
  window; do not infer delivery success from provider HTTP success.
- Roll back application code and migration together if required. The immediate configuration kill
  switch for any later paid activation is `OPENAI_ENABLED=false`; free routes remain available.
- For a separately approved paid activation, verify the exact `gpt-6-luna` model identifier,
  current official Standard pricing and context limit against the values pinned in
  `bot/services/llm/openai_budget.py`; configure only `OPENAI_ENABLED`, `OPENAI_API_KEY`,
  `OPENAI_MODEL`, and `OPENAI_MONTHLY_BUDGET_USD`. Confirm Admin -> LLM diagnostics
  shows readiness and remaining cap. No Fast/regional processing or extra billed tools.

### PR #296: Event Analysis medium reasoning

- Confirm PR SHA/base/CI and reasoning/default/override tests.
- Confirm no new schema/migration and no deterministic Event Alert cutoff.
- Before release, examine production env overrides without exposing secrets;
  pinned reasoning effort may override the shipped default.
- After explicit approval and deployment, verify sanitized LLM startup config,
  Event Analysis outcomes, false positives, coverage and cost/rate changes.
- Roll back code/config only via an authorized compatible release.

### Event Alert Luna-only release (owner-approved 2026-10-29)

For the Event Alert copy/news/chart release (#393 and #394), source promotion
alone is insufficient to activate the owner-selected Luna-only provider.
Before the bot is restarted on production, an authorized administrator must
check the actual, uncommitted `/opt/CCWBot/.env` and set, if necessary,
`OPENAI_ENABLED=true`, `OPENAI_MODEL=gpt-6-luna`,
`LLM_EVENT_PROVIDERS=openai` and `LLM_EVENT_RENDER_PROVIDERS=openai`.
Preserve the existing API key, budget guard and all unrelated settings; never
copy the template over `.env` or print the key. Make a protected root-only
backup of the existing `.env` **outside** the production Git checkout before
editing. If the key, budget or model readiness cannot be confirmed, do not
restart under a claim of Luna-only readiness.

Then use the ordinary read-only `ccwbot-deploy-safe status` followed by the
separately approved `ccwbot-deploy-safe deploy` through `ccwbot-prod-ops`.
Do not run migrations or raw Compose for this bot-only release. Inspect the
sanitized startup routing configuration and the actual Stage-1
`event_analysis` **and separate Stage-2** `event_alert_render` attribution
before claiming both use Luna; no Groq or Cloudflare Event Alert fallback.
Verify the revised sections and PNG on a naturally occurring private Telegram
Event Alert. If no such event occurs during verification, record client-smoke
status as pending rather than forcing a market alert. Health-only success is
not proof that AI text or news relevance is correct. Back out via the
approved protected environment backup and the restricted rollback workflow
only after review of the observed failure.

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
