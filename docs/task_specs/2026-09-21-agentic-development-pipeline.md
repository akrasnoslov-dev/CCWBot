# Task Spec: Agentic Development Pipeline

Lifecycle: active during implementation; retained as historical task context after completion. This file does not override canonical repository policy.

## Goal

Make the default non-trivial development workflow explicit and enforceable across CCWBot tooling:

1. Clarify requirements with the user before implementation.
2. Write a task-specific plan and specification before coding.
3. Define tests before implementation and require a green verification run before completion.
4. Isolate parallel implementation work with Git branches plus `git worktree`.
5. Use an adaptive orchestrator/worker model:
   - orchestrator and final acceptance: `gpt-5.6-sol`
   - normal workers: `gpt-5.6-terra`
   - simple low-risk workers: `gpt-5.6-luna`
   - Sol worker only for escalation when complexity or failed lower-tier attempts justify it
6. Treat token efficiency as a standing execution objective without sacrificing correctness.

## User decisions

- Every non-trivial task must begin with one compact clarification questionnaire, even when the task appears clear.
- Every non-trivial task gets its own specification file.
- Worker count is adaptive. The orchestrator decides how many workers are useful; no project-level fixed worker count is imposed.
- Workers operate in isolated worktrees/branches when work is parallelized.
- The same workflow should later be reusable for other repositories, including Gym Checklist.

## Scope

Expected changes:
- `docs/codex_instructions.md`
- `agents/routing.toml`
- `.codex/config.toml`
- `docs/source_of_truth.md`
- `docs/README.md` if needed
- `tests/test_agent_workflow_contract.py`

## Acceptance criteria

- Canonical workflow explicitly defines clarification, spec/plan, test-first, worktree isolation, orchestration, acceptance, and token-efficiency gates.
- Each task spec has a unique file under `docs/task_specs/`.
- Task specs are task records, not independent standing policy.
- Codex project config selects Sol for the primary/orchestrator model and Terra for default spawned agents.
- Routing defines Terra as normal worker, Luna as low-cost worker, Sol as escalation/orchestrator.
- No fixed project worker-count cap is introduced.
- Tests enforce the new workflow contract.
- A task cannot be declared complete without applicable verification passing.
