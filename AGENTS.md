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

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
