# Task Spec: Default ChatGPT Architect + L3 bridge mode

Date: 2026-10-02

## Goal

Make CCWBot use `CHATGPT_ARCHITECT` as the default codex-chatgpt-bridge operating mode and
`L3_WORKSPACE_WRITE` as the default permission level for bridge-assisted CCWBot work.

## Clarified requirements

- The user explicitly requested `CHATGPT_ARCHITECT + L3`.
- Make the setting durable in the repository source of truth rather than only in chat or a task prompt.
- Keep bridge access scoped to the existing narrow CCWBot workspace; do not broaden allowed roots.
- Keep Codex responsible for independent verification, git operations, and final claims.
- Keep existing L4/L5 approval gates and all L3 exclusions for secrets, installs, destructive actions,
  commit/push/history mutation, and access outside the approved workspace.

## Out of scope

- Changing product/runtime behavior.
- Changing the bridge controller, tunnel, OAuth, or Cloudflare configuration.
- Broadening filesystem roots.
- Changing model routing in `.codex/config.toml` or `agents/routing.toml`.
- Auto-merging the PR.

## Expected files

- `docs/codex_instructions.md` — canonical workflow owner.
- This task spec only.

## Risks

- `L3_WORKSPACE_WRITE` is a policy grant, not a technical sandbox; an authorized bridge exposes
  shell execution with local-user authority. Existing narrow-root and review discipline therefore
  remain mandatory.
- Making L3 the default increases the trust surface compared with read-only operation.

## Data / migration impact

None.

## Validation strategy

This is documentation/policy configuration, so a conventional regression test is not meaningful.
Validate by:
1. confirming the canonical owner contains the new default exactly once;
2. confirming `AGENTS.md`, `.codex/config.toml`, and `agents/routing.toml` are not duplicated or
   changed for this policy;
3. reviewing the branch diff and PR text for scope and security guardrails.

## Implementation plan

1. Add one concise bridge-default section to `docs/codex_instructions.md`.
2. Preserve all existing safety boundaries and final-verification ownership.
3. Fetch the changed files from the branch as verification.
4. Open a PR to `dev`; do not merge automatically.
