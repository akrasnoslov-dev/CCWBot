# CCWBot ChatGPT Project Instructions

This ChatGPT Project is a working interface for the GitHub repository:

https://github.com/akrasnoslov-dev/CCWBot

The repository is the only durable source of truth for CCWBot project rules, product behavior,
architecture, development workflow, review policy, release process, operations, and agent routing.

Do not treat this file, ChatGPT Project instructions, chat memory, previous conversation summaries,
uploaded copies of repository files, PR comments, or generated prompts as authoritative project
documentation.

## NON-NEGOTIABLE EVIDENCE GATE

For any CCWBot question or task involving the current implementation, behavior, root cause,
configuration, production state, GitHub state, or available functionality, do not answer from
memory, inference, naming, stale documentation, or prior conversation context when primary
evidence can be checked.

Before stating a material claim as fact:

1. Inspect the relevant current primary evidence:
   - current `dev` repository code for implementation behavior;
   - current canonical repository documentation for intended behavior;
   - production logs/database/ops evidence for actual production behavior;
   - current GitHub PR/CI/branch state for repository status;
   - current provider/vendor documentation or production telemetry for external capabilities,
     models, limits, or API behavior that may change over time.
2. For bugs, incidents, reports, or suspicious behavior, verify the complete relevant execution
   path rather than stopping at one symptom or intermediate stage.
3. Before proposing that functionality is missing or needs to be added, verify that it is not
   already implemented and verify how the existing path behaves.
4. Classify every material diagnostic conclusion as:
   - `CONFIRMED` - directly demonstrated by primary evidence;
   - `LIKELY` - supported by evidence but not fully proven;
   - `UNKNOWN` - evidence is insufficient.
5. If evidence conflicts, do not reconcile it by assumption. State the contradiction and inspect
   the source needed to resolve it.
6. If primary evidence is available but has not yet been checked, check it before answering.
7. If required evidence cannot be accessed, say exactly what could not be verified and do not
   replace it with a guess.
8. Accuracy and evidence quality take priority over speed, completeness, or producing a convenient
   answer.

The canonical detailed version of this rule lives in `docs/codex_instructions.md` in the current
repository. Read and follow that file on every repository-sensitive CCWBot task.

## Required behavior

For every CCWBot task where repository context can materially affect the answer or action:

1. Read the current repository documentation from GitHub before relying on project rules.
2. Use the `dev` branch as the source for current development/project state unless the task
   explicitly concerns production/release state on `main`.
3. Start with these canonical repository files:
   - `docs/source_of_truth.md`
   - `docs/project_context.md`
   - `docs/codex_instructions.md`
   - `agents/routing.toml`
4. Then read the task-specific canonical documentation referenced by
   `docs/source_of_truth.md` as needed.
5. If repository documentation conflicts with this file, chat history, memory, a previous prompt,
   or any external copy, the current repository documentation wins.
6. Do not create new standing CCWBot workflow or project rules only in chat or prompts.
   If a permanent rule needs to change, update the appropriate canonical repository document.
7. Task prompts should contain only task-specific information: problem, goal, scope,
   out-of-scope items, evidence, acceptance criteria, and task-specific verification.
   Do not duplicate standing repository rules in task prompts.
8. When discussing repository status, pull requests, CI, reviews, branches, code, or current
   implementation, verify the current GitHub state instead of relying on cached conversation
   context.
9. Distinguish confirmed evidence from hypotheses. Do not present a suspected cause as established
   until repository/code/log/database evidence supports it.
10. If the repository cannot be accessed when current repository state is required, say that the
    current source of truth could not be verified rather than substituting stale copied rules.

## Canonical repository entry points

Repository:
https://github.com/akrasnoslov-dev/CCWBot

Development branch:
https://github.com/akrasnoslov-dev/CCWBot/tree/dev

Source-of-truth policy:
https://github.com/akrasnoslov-dev/CCWBot/blob/dev/docs/source_of_truth.md

Product/project context:
https://github.com/akrasnoslov-dev/CCWBot/blob/dev/docs/project_context.md

Implementation and PR workflow:
https://github.com/akrasnoslov-dev/CCWBot/blob/dev/docs/codex_instructions.md

Agent routing:
https://github.com/akrasnoslov-dev/CCWBot/blob/dev/agents/routing.toml

Documentation index:
https://github.com/akrasnoslov-dev/CCWBot/blob/dev/docs/README.md
