# CCW-25 research evidence

Generated research artifacts; intentionally ignored by Git. No runtime source changes.

## Reproduce

Use the existing CCWBot venv and a checkout containing commit
`e0b47e4c95399f930a6a63554ecfe058b58d8cd5`. Do not start the bot. Preserve local files.

1. Reconstruct `dev-source/` by extracting `git archive --format=zip
   e0b47e4c95399f930a6a63554ecfe058b58d8cd5 bot ops_agent` into that directory.
   This is a source archive used for imports, not another Git checkout.
2. The owner approved local downloads for this research run. `download.py` fetches
   the release/revision-pinned artifacts and verifies SHA-256. About 9.7 GB weights
   plus 20 MB runtime archive; no API key or paid inference is required.
3. From the repository root, run with the existing venv:

   ```powershell
   .venv/Scripts/python.exe reports/ccw25-20261019/benchmark.py prepare
   .venv/Scripts/python.exe reports/ccw25-20261019/benchmark.py run --model qwen4
   .venv/Scripts/python.exe reports/ccw25-20261019/benchmark.py run --model phi
   .venv/Scripts/python.exe reports/ccw25-20261019/benchmark.py run --model qwen7
   .venv/Scripts/python.exe reports/ccw25-20261019/benchmark.py summary
   ```

   The recorded Qwen4 base run used two passes of the original 17-case corpus. The two long probes, Phi and Qwen7 runs use one pass each. Reproduction of the latter uses --repeats 1. The recorded Qwen4 run began with the original 17-case corpus. Its two added
   long-report cases are a disjoint shard, run with `--case-filter long_`.
   For a fresh all-19 Qwen4 run, use an empty results directory; never combine
   it with the separate long-report shard. New runs record their explicit case
   names. `run_manifest.json` records exact coverage.

4. Each model runs alone, CPU only, four threads, one slot, context 8192, seed 25,
   temperature 0, grammar-constrained schema, and no prompt cache. The child
   environment excludes bot/provider/DB credentials. The server binds loopback
   only, has no web UI, and is stopped in `finally`. No cloud fallback is invoked.
5. The first 34 Qwen4 requests used a 120s diagnostic HTTP timeout; later runs used 180s. Their generation/context/worker settings and pinned prompt contracts match. The first process also used default CORS; later runs restrict CORS to loopback. Commands and disjoint coverage are recorded separately.

The benchmark allows diagnostic wall time above real request deadlines to
   distinguish slow output from invalid output. Actual deadline compliance is
   scored at 15s or 20s per feature. This is not an integrated-router budget test.

`collect_workload.py` is separate. It requires the approved SSH tunnel to local
port 15433 and the existing investigator passfile. It verifies the role and both
read-only settings, uses indexed created-at ranges and a 15s statement timeout,
rolls back all evidence transactions, and exports aggregate columns only.
It never exports provider messages, prompt/output text, operation IDs or user data.
The historical fixed window is 2026-10-12 00:00 through 2026-10-19 00:00 UTC.

## Interpretation limits

- All market/news input is fictional. The prompt templates and validators are
  production source from the pinned development commit.
- Sparse author-written expectations are smoke assertions, not independent gold
  labels or a precision/recall benchmark. Manual observations in the report do not
  replace the independent release evaluation.
- JSON, schema and selected backend guards do not establish factuality or usefulness.
  Heartbeat sanitization and report validation can accept unsupported claims.
- This is Windows workstation timing, not Linux/Hetzner or GPU timing. No production
  model was installed. Neither one-slot queueing nor burst capacity was load-tested.
- Two identical deterministic passes are dependent observations. Small-sample
  nearest-rank p95 often equals the maximum. No confidence interval is claimed.
- Resource counters are Windows process peak working set/private commit; Linux
  cgroup peak memory and resident weight sharing can differ.
- Endpoint authentication is absent for this brief synthetic-only run. A local
  process could access it. A deployment needs private networking/authentication.
- Shared ZIP evidence excludes weights, runtime binaries, source bodies/bytecode,
  server logs, personal invoice details, and all credentials.

## Billing assumptions

`cost_model.json` contains the arithmetic and fixed FX assumptions. The latest
invoice is an exact historical September bill, not a claim about October accrual.
The API token-price scenario is hypothetical and does not represent the actual
multi-provider invoice or establish that paid service use is approved.

Raw synthetic outputs are retained so a reviewer can independently inspect errors.
All query/result/script/source manifests should be checksum-verified against the
final evidence manifest before treating files as the reviewed run.
