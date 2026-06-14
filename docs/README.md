# Documentation

All project and process documentation belongs in `docs/`, except:

- root `README.md`, which is the public project entry point;
- root `AGENTS.md`, which stays at the repository root because Codex/agent tooling reads it
  from there.

Do not add new standalone project documentation at the repository root. Add it here and link it
from this index or from `README.md` when it is useful for users.

## Project Context

- `project_context.md`: product, stack, invariants, and primary context map.
- `codex_instructions.md`: short Codex operating rules for this repository.
- `codex_agent_workflow.md`: task-review agent routing and review workflow.
- `codex_skills.md`: locally installed Codex skills and when to use them.

## Development And Release

- `development.md`: local development notes, runtime behavior, and verification.
- `release_checklist.md`: `dev` -> `main` release checklist.
- `dev_ops_guide.md`: environment and production deployment guide.

## Operations

- `observability.md`: read-only SQL and operational diagnostics.
- `llm_usage.md`: LLM usage and rate-limit reporting snippets.
- `ops_agent_service.md`: current ops-agent service contract and report flow.
- `ops-agent-report-codex-prompt.md`: reusable Codex prompt for ops-agent bundle analysis.
