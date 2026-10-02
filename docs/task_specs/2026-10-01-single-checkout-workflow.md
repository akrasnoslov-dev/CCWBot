# Single-checkout development workflow

## Goal
Keep one local CCWBot repository folder and stop creating Git worktrees by default.

## Clarified requirements
- Use a single local repository checkout for normal development.
- Use normal Git branches in that checkout for feature/fix work.
- Do not create `git worktree` checkouts unless the owner explicitly requests one for a specific task.
- Default to one implementation writer at a time; read-only review/analysis agents may still run in parallel.
- Remove obsolete local worktrees after confirming they are clean and their PRs are merged.

## Out of scope
- Product/runtime behavior changes.
- CI, deployment, database, or production changes.
- Rewriting historical task specifications that describe the old workflow.

## Acceptance criteria
- `git worktree list` shows only the main CCWBot checkout.
- Current workflow documentation describes a single-checkout branch workflow.
- Agent routing no longer declares `git_worktree` isolation.
- Workflow contract tests enforce the new policy.
- Release/ops docs do not use `worktree` when they mean the normal repository checkout/working tree.
- Focused workflow contract tests pass.

## Plan and validation
Update the workflow contract test first and confirm it fails against the old policy. Then update `docs/codex_instructions.md`, `agents/routing.toml`, and wording in supporting docs. Run the focused contract test, formatting/diff checks, and inspect the final Git/worktree state.
