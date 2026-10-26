# Context Audit Report

Measured 2026-09-21 for the current repository. The user did not specify a separate product task;
this audit therefore treats context-audit itself as the task and evaluates the setup for ordinary
development in this project. No configuration or tool changes were applied.

## 1) Environment

- Python: 3.14.4; requirement is Python 3.11+.
- Node.js: 24.16.0; meets the codeburn requirement of 22.13+.
- codeburn: 0.9.24, installed via CLI.
- caveman: 1.3.4, installed; not enabled as a proxy.
- graphify: 0.9.65, installed via CLI.
- Claude retention: effective 30 days; not explicitly configured in
  `C:\Users\Loki\.claude\settings.json`.
- CLI presence: `git`, `gh`, `python3`, `uv`, `npm`, and `npx` present; `codex` and `claude`
  executables were not found by the audit environment check.

`codeburn doctor` found history for `claude`, `codex`, and `copilot` (three providers with data).
Other probed providers were `empty`, with `vercel-gateway` reported as `network`. Empty means
history was not found, not that those providers had no usage. The codeburn scan was read-only.

## 2) Measurement

- Period: Last 7 Days, 2026-09-13T22:00:00Z through 2026-09-21T21:59:59Z.
- Health: `C` (score 60).
- Sessions: 17. Calls: 2,695. Findings: 4.
- Classes: `fix` 2, `nudge` 1, `keep` 1.
- codeburn's aggregate potential is 139,453,471 tokens / 33.7%, but this is an estimate and
  is not a promise. No currency totals are included here.

## 3) Plan by gradation

The normal limit is three A steps and one B step per pass. No step was applied.

| Tier | Finding | Action | Effect / basis | Command | Rollback |
|---|---|---|---|---|---|
| A | `bash-output-cap` | Add a bounded shell-output marker block | 3,750 tokens, `estimated` | `codeburn optimize --apply --only bash-output-cap` | `codeburn act undo --last` |
| A | `unused-skills` | Archive one candidate, not delete it | 80 tokens, `estimated`; verify freshness first | `codeburn optimize --apply --only unused-skills` | `codeburn act undo --last` |
| B | `mcp-inventory` | Decide whether `node_repl` and `pencil` should remain deferred/configured for the task | No token estimate; inventory only | No command until user approves a specific server action | Restore the server entry from a backup |

`graphify` is not archived despite the codeburn candidate: the recent installation/version check
means the freshness rule requires manual confirmation before any archive action. The scan's
`unused-skills` result is limited to its measured history and is not proof of global non-use.

### Habits

- `low-worth-sessions` (B, `nudge`): codeburn identified five possibly low-worth expensive
  sessions. Its 138,560,365-token figure is `estimated`, not measured savings. For the next
  expensive thread, name the deliverable in one sentence; stop for review after ten minutes
  without an edit or after two failed approaches. This is a one-time working habit, not a config
  change.

### Information / not done

- `context-heavy-sessions`: six sessions, 889,276 tokens, `measured`; kept as information because
  the context may have been justified.
- No C experiment was installed. No D action was attempted. `sync`, `share`, `devices`, mass
  `--apply --yes`, destructive deletion, and disabling a task-needed MCP remain prohibited.

## 4) Startup load

- Skill descriptions visible to the agent: 3,358 bytes across 16 inventory entries. These are
  description bytes, not model tokens.
- Memory/bootstrap files: project `CLAUDE.md` 794 bytes, `AGENTS.md` 1,170 bytes, and user
  `~/.claude/CLAUDE.md` 228 bytes; no imports were reported. Total: 2,192 bytes.
- Configured MCP servers: 2. Their live connection and authorization were not checked.

All byte sizes above are text volume, not token counts or subscription billing.

## 5) Skill inventory

Codeburn did not provide per-skill call counts in this report. An absent count is `no data`, not
zero usage. The two scopes below intentionally contain duplicate skill names.

| Skill | Description | Description bytes | Body bytes | Calls | Tier |
|---|---|---:|---:|---|---|
| graphify | Project knowledge graph and navigation | 355 | 43,789 | no data | review freshness |
| agents-md | Maintain concise agent instruction files | 276 | 3,188 | no data | review |
| caveman | Compressed communication and memory text | 1 | 3,916 | no data | C, optional |
| context-audit | Measure and rank context usage | 353 | 16,081 | current audit | keep |
| documentation-writer | Diátaxis technical documentation | 221 | 2,748 | no data | review |
| find-skills | Discover installable skills | 303 | 5,446 | no data | review |
| playwright | Browser automation and UI checks | 209 | 3,771 | no data | review |
| requesting-code-review | Request review before merge | 107 | 2,808 | no data | review |
| supabase-postgres-best-practices | PostgreSQL performance guidance | 183 | 2,576 | no data | review |
| agents-md (Codex) | Maintain concise agent instruction files | 276 | 3,188 | no data | review |
| caveman (Codex) | Compressed communication and memory text | 1 | 3,916 | no data | C, optional |
| context-audit (Codex) | Measure and rank context usage | 353 | 16,081 | no data | keep |
| documentation-writer (Codex) | Diátaxis technical documentation | 221 | 2,748 | no data | review |
| playwright (Codex) | Browser automation and UI checks | 209 | 3,771 | no data | review |
| requesting-code-review (Codex) | Request review before merge | 107 | 2,808 | no data | review |
| supabase-postgres-best-practices (Codex) | PostgreSQL performance guidance | 183 | 2,576 | no data | review |

No entry crosses the report's heavy thresholds of roughly 500 description bytes or 200 KB package
bytes. `graphify` package size is 88,101 bytes; the other package sizes are also below 200 KB.

## 6) MCP inventory

| Server | Scope | Enabled flag | Live connection | Recommendation for this audit task |
|---|---|---|---|---|
| `node_repl` | `~/.codex/config.toml` | not set | not checked | Defer; not needed for this Python/repository audit |
| `pencil` | `~/.codex/config.toml` | not set | not checked | Defer; not needed for this Python/repository audit |

The project has no `.codex/config.toml` and no `.mcp.json`; `~/.claude.json` contained no servers.
Configuration does not prove connection or authorization, and organization/application-level MCP
connections may be outside this inventory.

## 7) Tools

| Tool | Status | Role | Choice in this audit |
|---|---|---|---|
| codeburn | installed, 0.9.24 | Usage measurement and optimization findings | used read-only |
| caveman | installed, 1.3.4 | Optional shorter responses and compression | not enabled |
| graphify | installed, 0.9.65 | Project graph/navigation | retained; no archive action |

Caveman is not being proposed as an applied change because the current plan has no CLAUDE.md or
output-compression fix. If later requested, the small skill should be considered before the proxy.
Proxy caveats: default anonymous telemetry can be disabled with `caveman telemetry off` or
`DO_NOT_TRACK=1`; runtime license is BSL-1.1, and Codex compression hooks are not equivalent.

## 8) What was not done

- No A or B finding was applied because each requires the user's explicit approval for that exact
  step; this report is diagnostic only.
- No C experiment, proxy, `caveman learn implement`, or `codeburn guard install` was run.
- No D action was run. No files outside this report, home configuration, or project configuration
  were changed.
- Recheck after at least three days with `codeburn act report`, then run a new read-only audit.

