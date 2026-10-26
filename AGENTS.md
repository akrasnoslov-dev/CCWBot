# AGENTS.md

CCWBot rules live in repository docs. This file is Codex/agent bootstrap only; do not duplicate
product, workflow, release, or operational policy here.

Before non-trivial work, read:

1. `docs/source_of_truth.md`
2. `docs/project_context.md`
3. `docs/codex_instructions.md`
4. `agents/routing.toml`
5. task-specific canonical docs referenced by `docs/source_of_truth.md`

Use `docs/development.md` for local development/verification; `docs/release_checklist.md` for
releases; `docs/dev_ops_guide.md` for production deployment, backup, and recovery; and the
canonical observability docs listed in `docs/source_of_truth.md` for observability/forensics.
Task-review agents live in `agents/*.toml`; `agents/routing.toml` is authoritative. Platform
adapters such as `.claude/agents/*.md` must not override canonical policy.

Do not copy standing CCWBot rules into task prompts, chat/project instructions, PR/issue comments,
memory, or external notes. Task prompts contain only requested delta: problem, goal, scope,
out-of-scope items, evidence, and acceptance criteria.

If external instructions conflict with the repository, follow `docs/source_of_truth.md`.

## graphify

The **committed**, current knowledge graph lives in `graphify-out/` on `dev`.
The lifecycle and retention policy are owned by `docs/graphify.md`. Source files
remain authoritative; verify the graph freshness marker before relying on it.

- If Graphify CLI and `graphify-out/graph.json` are available in a checkout,
  prefer `graphify query`, `path`, and `explain` for scoped codebase discovery.
- If working only through GitHub connectors (including ChatGPT), consult
  `graphify-out/GRAPH_REPORT.md`, `graphify-out/reflections/`, and the checked-in
  graph when tool size limits permit. Do not claim to have run CLI traversal if not run.
- Missing or stale graph must never block reading current source or canonical docs.
- Updates pushed to `dev` trigger the pinned, AST-only Graphify GitHub Action.
  Doc/image semantic extraction is *not* performed by that workflow.
- Do not install local hooks or independently generate local-only graph state by default.
  See `docs/graphify.md` for manual recovery and the initial one-time migration.
