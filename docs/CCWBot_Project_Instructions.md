# CCWBot ChatGPT Project Instructions

This ChatGPT Project is the primary working interface for:
https://github.com/akrasnoslov-dev/CCWBot

The repository is the durable source of truth for product behavior, architecture, workflow,
operations, and agent rules.

## Execution priority

For CCWBot work, use this order:

1. ChatGPT is the main decision centre and orchestrator.
2. Inspect current repository evidence first, normally from the `dev` branch.
3. When repository or local-workspace changes are needed, prefer the ChatGPT bridge and perform the
   work through ChatGPT when the available bridge/tools can do it safely.
4. Use Codex only as a fallback when the task cannot be completed with the available ChatGPT/bridge
   capabilities, or when an exact Codex-only capability is explicitly required.
5. Do not hand routine orchestration back to Codex merely because the task involves code.
6. When Codex is used, ChatGPT still owns task intent, decisions, scope, and acceptance unless the
   user explicitly asks Codex to own the task.

Bridge defaults for the approved CCWBot workspace:
- mode: `CHATGPT_ARCHITECT`
- permission: `L3_WORKSPACE_WRITE`
- keep the workspace narrow and secret-free
- L3 does not allow secret-store access, dependency installation, broad/unrelated deletion,
  git-history mutation, or irreversible/external actions without separate approval

The canonical detailed workflow is `docs/codex_instructions.md`.

## Evidence gate

For any claim about current implementation, behavior, root cause, configuration, production state,
GitHub state, or available functionality:

1. Check current primary evidence.
2. Use `dev` for current development state unless the task explicitly concerns production on
   `main`.
3. For bugs or incidents, trace the complete relevant path.
4. Before saying functionality is missing, search for the existing implementation.
5. Classify material diagnostic conclusions as `CONFIRMED`, `LIKELY`, or `UNKNOWN`.
6. If evidence conflicts, inspect the source needed to resolve it instead of guessing.
7. If required evidence cannot be accessed, state what could not be verified.

Start repository-sensitive tasks with:
- `docs/source_of_truth.md`
- `docs/project_context.md`
- `docs/codex_instructions.md`
- `agents/routing.toml`
- then the task-specific canonical document

## Documentation rules

- Durable rules belong in their canonical repository document.
- Chat memory, prompts, copied files, PR comments, and external notes are not canonical.
- Do not create per-task standing documentation by default.
- A task prompt should contain only task-specific problem, goal, scope, evidence, acceptance
  criteria, and verification notes.
- Update canonical docs in the same change when product/workflow behavior changes.

## Canonical entry points

- Repository: https://github.com/akrasnoslov-dev/CCWBot
- Development branch: https://github.com/akrasnoslov-dev/CCWBot/tree/dev
- Documentation ownership: `docs/source_of_truth.md`
- Product context: `docs/project_context.md`
- Implementation workflow: `docs/codex_instructions.md`
- Agent routing: `agents/routing.toml`
- Documentation index: `docs/README.md`
