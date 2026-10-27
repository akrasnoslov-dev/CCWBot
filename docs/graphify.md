# Repository-backed Graphify

This document owns CCWBot's shared Graphify data, refresh workflow, and retention policy.
The canonical product and workflow documents and current source code remain the authority.
Graphify is a derived index, not a separate policy source.

## Shared state in dev

Only current, portable, approved knowledge-base outputs are tracked:

- `graphify-out/graph.json` — full queryable graph.
- `graphify-out/GRAPH_REPORT.md` — compact report usable via GitHub/ChatGPT.
- `graphify-out/graph.html` — browser visualization.
- `graphify-out/manifest.json` — portable incremental metadata.
- `graphify-out/.graphify_labels.json`, `.graphify_labels.json.sig`,
  `.graphify_learning.json` — existing curated annotations where present.
- `graphify-out/reflections/` — durable Graphify lessons where present.
- `graphify-out/SOURCE_COMMIT` — commit used as input for the most recent automated AST refresh.

No other generated files from `graphify-out/` may be committed. In particular,
dated backup directories (`YYYY-MM-DD/`), `cache/`, `logs/`, extraction
intermediates, `.graphify_python`, `.graphify_root`, and `.vocab.txt` are
device-specific or disposable. These are not repository data. Do not commit
secrets, sensitive credentials, database dumps, or personal notes.

Git checkouts necessarily contain local working copies of tracked artifacts.
"Repository-backed" means Git is authoritative; it cannot mean literally
zero bytes of local checkout data.

## Clones and local development

The portable graph, current labels, manifest, report and durable reflections are
tracked in `graphify-out/` on `dev`. The directory itself is **not ignored** by Git.
A clean clone restores the nine current shared artifacts. Only known disposable
dated backups, caches, logs and extraction intermediates are ignored.

Use `git ls-files graphify-out/` to see exactly what is versioned. Avoid
maintaining a separate local-only authoritative graph.

## Updates after migration

`.github/workflows/graphify.yml` runs after pushes to `dev` and can also be
started with `workflow_dispatch`. It installs the explicitly approved pinned
`graphifyy[sql]==0.9.66` only on an ephemeral GitHub-hosted runner, with
`PYTHONHASHSEED=0`. It refreshes the existing graph via
`python -m graphify update .` (deterministic code AST, **no LLM provider**),
commits allowlisted updated artifacts back to `dev`, and records the code
source commit in `SOURCE_COMMIT`. Missing initial graph is a deliberate
no-op: never replace the locally curated seed with a blank one.

A bot commit made using the default `GITHUB_TOKEN` does not cause a recursive
workflow run. If concurrent dev commits race, the job retries from latest dev
(up to three times) instead of force-pushing. Do not deploy or modify `main`.

This workflow **does not** perform document, image, or paper semantic
extraction. Updating those relationships requires an explicitly approved
semantic run and subsequent review and commit of the resulting graph.
Never enable external semantic-extraction providers without direct approval.
If a code push has not yet finished its Graphify job, the published graph may
lag the source. Verify the latest workflow and `SOURCE_COMMIT` before treating
its graph as fresh.

Use the GitHub-published `GRAPH_REPORT.md` for remote overview, and
`graph.json` for tools that can process its size. The ChatGPT GitHub connector
does not automatically execute `graphify query`; code inspection is still
necessary when graph traversal is unavailable.

## Retention

Keep only current tracked graph data. Archive snapshots and caches are not
migrated. The historical publisher removed dated local backups after publishing. The shared graph is now already versioned; temporary local backups are disposable.
Subsequent Graphify CI jobs use disposable runners: backups they generate
are discarded with the runner, not committed or stored on the workstation.

Do not add a Graphify merge driver or global Git hooks. The repo workflow
replaces local update hooks. Existing local hooks are disabled as part of
one-time migration once the push succeeds.
