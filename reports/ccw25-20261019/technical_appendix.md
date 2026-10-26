# CCW-25 — Self-hosted LLM owner decision

Research date: **19 October 2026**. Reference development commit: `e0b47e4c95399f930a6a63554ecfe058b58d8cd5`.

**Decision: NO-GO for production self-hosting now. Keep the existing cloud routing.** The current host has insufficient safe memory for the tested configuration, and the local screen exposes both deadline misses and semantic errors. A VPS/GPU purchase is not justified by the observed token demand. No production configuration, provider routing, subscription, or server was changed; no paid API or hosting service was purchased.

## What is measured

- **Host:** 2 vCPU, 3.73 GiB RAM, no swap or recognized compute GPU; root disk approximately 37.2 GiB, 79% used, 7.63 GiB free. Historical whole-host samples on 17–18 October show 2.61/2.60 GiB minimum available memory, CPU average 2.75/3.39% and sampled peaks 24.61/48.92%. These are approximately ten-minute samples, not continuous maxima or container attribution. At the live observation only PostgreSQL was listed and health failed; current free memory therefore does not establish normal bot headroom. No remediation was attempted.
- **Latest actual invoice:** issued 15 October for **September**, CX23 €3.99 + IPv4 €0.50 = **€4.49 net / €5.61 including 25% Danish VAT**, approximately **DKK 33.56 / 41.93**. This verifies a historical monthly bill and legacy plan, not October accrual or the price after resizing. Current guest resource shape is consistent with that billed plan.
- **Workload, 12–19 October UTC:** 1,913 correlated logical operations, 2,076 attempted-provider rows and 1,497 zero-request skip rows. Reported tokens: 1,548,644 input / 549,419 output; **134 attempts lack token counts**. No raw production prompt, output, or user identity was exported. Investigator role and both read-only settings were verified before bounded queries.

| Feature | Logical operations/day | Provider attempts/day | Input/output tokens over 7 days |
|---|---:|---:|---:|
| Event significance | 192.00 | 210.00 | 1,169,354 / 433,294 |
| Event Render | 30.86 | 36.29 | 119,512 / 32,705 |
| News Intelligence | 28.43 | 28.29 | 121,743 / 33,937 |
| Market Heartbeat | 13.86 | 13.86 | 62,104 / 15,461 |
| Daily reports | 6.86 | 6.86 | 62,347 / 28,756 |
| Weekly reports | 1.29 | 1.29 | 13,584 / 5,266 |

The window spans configuration/behavior transitions and includes historical retired-Mistral attempts. Render logical operations ranged from 79 on 12 October to 8 on 17 October; Heartbeat from 52 to 1. These observed averages are not a steady-state forecast.

| Feature | Logged input characters p50 / p95 | Recorded input tokens p50 / p95 | Recorded output tokens p95 |
|---|---:|---:|---:|
| Significance | 2718 / 2863 | 801 / 1052 | 963 |
| Render | 1680 / 2528 | 450 / 722 | 241 |
| News | 1493 / 1657 | 657 / 685 | 216 |
| Heartbeat | 1213 / 2689 | 524 / 899 | 202 |
| Daily | 3029 / 4063 | 1309 / 1602 | 770 |
| Weekly | 4318 / 6513 | 1778 / 2471 | 836 |

Rounded continuous percentiles describe available telemetry fields. Provider tokenizers/reasoning differ. Diagnostic output caps were 300 for significance/Render, 350 for News/Heartbeat and 800 for reports; they do not reproduce historical completion-length distributions, especially significance. The truncated 7B weekly response shows a limit of this fixed-cap screen, not proof that it could never complete with another budget.

There were 39 timeout rows and 52 schema-error rows; 150 of 159 multi-attempt operations recovered. Seventeen correlated operations had no successful attempt. Peak timestamped telemetry buckets contained six attempted rows or eight logical operations per minute; **these are not start-rate or concurrency measurements**. Production request latency, true concurrency, cache-hit rate and actual API spending remain **UNKNOWN**. The telemetry has no duration fields; no matching invoice emails does not establish zero spending. No cache/reuse matches in the selected outcome query does not establish zero reuse. The architecture reuses global analyses/reports, so recipient growth must not be multiplied into LLM demand.

## Specific candidates and serving stack

All three candidates were screened at **GGUF Q4_K_M**, with pinned **llama.cpp `b11734` / CPU `llama-server`**, one slot, 8,192-token context and four CPU threads. Original model cards, weight repositories/revisions and SHA-256 hashes are recorded in the accompanying manifests. Commercial deployment remains subject to the actual license terms; quantization does not remove factual errors.

| Candidate | License; advertised context | Downloaded weights | Assessment |
|---|---|---:|---|
| [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) | Apache-2.0; 262,144; non-thinking | 2.50 GB | Multilingual/instruction-following candidate; screened English output and one German-source news item. No CCW market-quality guarantee. |
| [Phi-4-mini-instruct, 3.8B](https://huggingface.co/microsoft/Phi-4-mini-instruct) | MIT; 131,072 | 2.49 GB | Broad multilingual/math/logic positioning; Microsoft explicitly notes limited factual knowledge. |
| [Qwen2.5-7B-Instruct, 7.61B](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | Apache-2.0; 32,768 configured, 131,072 with YaRN | 4.68 GB, two shards | Larger structured-output/multilingual comparator; greater memory cost. No long-context extrapolation used. |

A smaller desk-only alternative is [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B) (Apache-2.0) with [Q4_K_M weights about 1.28 GB](https://huggingface.co/bartowski/Qwen_Qwen3-1.7B-GGUF/tree/dcb19155b962dbb6389f4691a982043a8e651022). A reduced-context, non-thinking configuration might fit current memory for simple tasks; this was **not downloaded or benchmarked**, and memory fit alone establishes neither CCW quality nor latency. The NO-GO is for current production adoption on the tested evidence, not a claim that no smaller model could ever launch. A future zero-cash exploration should test such a model offline under a realistic memory cap before considering any production co-location.

**No model is recommended for production.** For a later isolated 4B experiment, budget at least an 8 GB / 4-vCPU machine; 16 GB / 8-vCPU is the safer co-location planning envelope, reserving capacity for bot/DB/OS. These are unvalidated sizing estimates, not deployment approval. For the 7B comparator, plan 16 GB total RAM. A compute GPU is optional for execution; GPU VRAM must cover weights, KV cache and runtime buffers. None was benchmarked. Vendor maximum context lengths are unsuitable memory-sizing defaults for this host. For Qwen3-4B with FP16 KV at 8192 tokens, architectural sizing alone gives about 1.125 GiB KV cache (36 layers × 2 K/V × 8 KV heads × 128 head dimensions × 2 bytes × 8192). Approximately 2.33 GiB weights plus KV already exceed the historical 2.60 GiB available, before runtime buffers. Shorter/quantized KV or more aggressive weight quantization were not tested and cannot inherit these quality/performance results.

### Actual local screen

| Model / feature | N | JSON / contract valid | Within deadline | p50 / p95 seconds | Median generation tokens/s | Peak working set GiB |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-4B / Significance | 10 | 10/10 / 10/10 | 3/10 | 16.1 / 17.3 | 9.6 | 4.80 |
| Qwen3-4B / Render | 6 | 6/6 / 4/6 | 6/6 | 11.6 / 14.2 | 10.5 | 4.80 |
| Qwen3-4B / News | 6 | 6/6 / 6/6 | 5/6 | 15.4 / 21.3 | 10.8 | 4.80 |
| Qwen3-4B / Heartbeat | 4 | 4/4 / 4/4 | 4/4 | 13.3 / 14.6 | 10.9 | 4.80 |
| Qwen3-4B / Daily | 5 | 5/5 / 5/5 | 0/5 | 82.0 / 94.0 | 8.6 | 5.18 |
| Qwen3-4B / Weekly | 5 | 5/5 / 5/5 | 0/5 | 90.0 / 118.9 | 8.7 | 5.24 |
| Phi-4-mini / Significance | 5 | 5/5 / 5/5 | 4/5 | 14.1 / 15.7 | 11.6 | 4.63 |
| Phi-4-mini / Render | 3 | 3/3 / 2/3 | 3/3 | 11.6 / 13.3 | 10.9 | 4.71 |
| Phi-4-mini / News | 3 | 3/3 / 3/3 | 3/3 | 14.6 / 15.5 | 11.4 | 4.80 |
| Phi-4-mini / Heartbeat | 2 | 2/2 / 1/2 | 2/2 | 11.1 / 12.2 | 11.3 | 4.80 |
| Phi-4-mini / Daily | 3 | 3/3 / 3/3 | 0/3 | 41.9 / 45.6 | 10.3 | 4.80 |
| Phi-4-mini / Weekly | 3 | 3/3 / 3/3 | 0/3 | 43.6 / 65.8 | 10.1 | 4.80 |
| Qwen2.5-7B / Significance | 5 | 5/5 / 5/5 | 0/5 | 28.8 / 29.6 | 6.4 | 6.93 |
| Qwen2.5-7B / Render | 3 | 3/3 / 3/3 | 0/3 | 20.3 / 20.4 | 6.6 | 6.93 |
| Qwen2.5-7B / News | 3 | 3/3 / 3/3 | 0/3 | 25.9 / 28.5 | 7.1 | 6.93 |
| Qwen2.5-7B / Heartbeat | 2 | 2/2 / 2/2 | 0/2 | 26.9 / 28.9 | 7.5 | 6.93 |
| Qwen2.5-7B / Daily | 3 | 3/3 / 3/3 | 0/3 | 118.7 / 133.4 | 6.7 | 6.93 |
| Qwen2.5-7B / Weekly | 3 | 1/3 / 1/3 | 0/3 | 163.3 / ≥180.0 (timeout) | 5.9 | 6.93 |

Qwen2.5-7B long weekly timed out after 180.03 seconds: completion latency is right-censored. Its weekly p95 is a lower bound. The other failed weekly response reached the 800-token limit and was invalid JSON. Percentiles describe all request attempts, not successful completions only.

Approximately one-second Windows process samples show median active CPU equivalents of 3.95–3.96 logical CPUs, with sampled peaks 4.03–4.05. These describe the four-thread workstation process, not spare target-VPS capacity. Qwen4 monitoring covers only its long-report process; Phi and Qwen7 have broader run coverage. Raw samples and timing caveats are retained in `resource_samples.jsonl` and `resource_summary.json`.


The results are **Windows i5-12400F, 16 GB RAM workstation measurements**, not Hetzner/Linux benchmarks. Nineteen synthetic input cases use the real pinned development prompt builders, JSON schemas and feature validators; repeated deterministic cases improve timing observations but are not independent quality labels. JSON/schema validity is reported separately from factuality. The two long report probes approach observed input-character p95. Nearest-rank sample p95 at this sample size is exploratory. No queue/arrival replay, sustained soak, GPU test, cloud A/B or final Telegram rendering was performed. Report fixtures use uniform coin moves and omit asset names/rich weekly history: they test underspecified/missing-context behavior as well as size, and are not exact copies of full runtime report payloads. In particular, an invented asset-name expansion in a symbol-only fixture must not be generalized to runtime inputs that supply the name. These three version-pinned models are a feasibility shortlist, not an exhaustive or latest-model leaderboard.

Qwen3-4B fabricated report catalysts/timelines, misstated a Render period, and described stable conditions without sufficient evidence. Phi-4-mini returned generic/unsupported report content and an empty required Heartbeat action. All three missed at least one significance fixture; Qwen2.5-7B incorrectly alerted on the news-only fixture. Some Render rejections appear to be guard false positives rather than proven model factual errors. These are manually inspected fixture findings, not measured real-world quality rates.

| Feature | What the screen supports | Production suitability now |
|---|---|---|
| Event significance | All three fail at least one intended disposition; Qwen2.5-7B alerts on the news-only fixture. Structured fields can be internally plausible but unsupported. | NO-GO; retain current route and independent release evaluation. |
| Event Render | Period/reversal wording errors occur; some guard rejections appear false-positive. Final assembly/news/recipient-specific context not exercised. | NO-GO; not validated as a replacement. |
| News Intelligence | Injection/noise and equal-multi-asset primary-symbol failures vary by model. One German item is not a multilingual quality benchmark. | NO-GO for adoption; only a future narrow classification experiment is supported. |
| Market Heartbeat | Unsupported stability/range claims, an empty required action, and raw numeric errors occur. Numeric sanitization can strip text or use a generic fallback. | NO-GO; raw-model and post-validator usefulness differ. |
| Daily reports | Unsupported catalysts or generic placeholders; current 20-second deadline is missed in report probes. | NO-GO on tested CPU settings. |
| Weekly reports | Invented/generic timelines and weak missing-history handling; deadline misses. | NO-GO on tested CPU settings. |

Passing a schema does not prove rendered text useful or factual. Backend sanitization may remove bad raw wording; `heartbeat_post_validation.json` shows this intermediate stage, not final Telegram assembly. A validator rejection is not automatically a proven model factual error. Existing validators/fallback remain necessary even with grammar-constrained JSON. This screen does not satisfy independent evaluation/release gates in [the alert contract](https://github.com/akrasnoslov-dev/CCWBot/blob/e0b47e4c95399f930a6a63554ecfe058b58d8cd5/docs/alert_logic.md#event-alert-acceptance-criteria-approved-2026-10-16).

## Monthly EUR / DKK comparison

Public prices checked **19 October 2026**; EU locations, full-month cap, one IPv4. DKK conversions use **1 EUR = 7.4748 DKK**, and USD comparisons **1 EUR = 1.1253 USD**, both ECB 16 October reference observations. DKK amounts are conversions, not card settlement rates. Net prices and Danish-VAT scenarios are separate. Latest billed existing-host baseline is assumed unchanged for comparison; October billing is unverified.

| Option | Hosting net EUR / DKK monthly | Hosting with 25% VAT EUR / DKK | Increment vs latest baseline, net EUR / DKK | Vendor one-time net |
|---|---:|---:|---:|---:|
| A. Existing CX23 + local inference | 4.49 / 33.56 | 5.61 / 41.93 | 0 / 0 | €0; **capacity NO-GO** |
| B. Resize to CX33, 4 vCPU / 8 GB / 80 GB | 8.99 / 67.20 | 11.24 / 84.00 | 4.50 / 33.64 | €0; minimum experiment envelope only |
| B. Resize to CX43, 8 vCPU / 16 GB / 160 GB | 16.49 / 123.26 | 20.61 / 154.07 | 12.00 / 89.70 | €0; performance/quality unproved |
| C. Separate GEX45, 24 GB VRAM / 64 GB RAM, retain bot VPS | 218.49 / 1,633.17 | 273.11 / 2,041.46 | 214.00 / 1,599.61 | €209 / DKK 1,562.23; with VAT €261.25 / DKK 1,952.79 |
| D. Current cloud/free-tier chain | 4.49 / 33.56 **plus unknown actual API spending** | 5.61 / 41.93 plus unknown API spending and applicable tax | €0 hosting | €0 |

Sources: [current Hetzner cloud price adjustment](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/), [IPv4 price](https://docs.hetzner.com/cloud/servers/primary-ips/overview/), [GPU order list](https://robot.hetzner.com/order), [GEX45 specification](https://www.hetzner.com/dedicated-rootserver/gex45/), [ECB DKK](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/eurofxref-graph-dkk.en.html), [ECB USD](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/eurofxref-graph-usd.en.html). GPU order-list €254.66/month and €248.71 setup include 19% German VAT: dividing by 1.19 gives €214 and €209 net. Do not use obsolete GEX44 launch pricing. Resizing can replace legacy pricing; obtain the account-specific quote before purchase.

On resized/separate options, included disks suffice for one selected model; extra model storage is **€0 assumed**, not purchased. Model files can be re-downloaded; no separate model backup is budgeted. Existing DB backup costs remain unchanged/unknown. Optional Hetzner Cloud backups add [20% of the server price](https://docs.hetzner.com/cloud/billing/faq/): CX43 approximately €3.20 net / DKK 23.90 extra monthly (€4.00 / DKK 29.88 with VAT). Electricity is included in rented-host pricing; workstation benchmark energy was not metered. Operator effort is excluded from cash prices: planning assumption 6–12 hours setup plus 1–2 hours/month; at €50/hour this is €300–600 one-time and €50–100/month, not a quote or incurred charge.

### Volume sensitivity and break-even

An **illustrative paid replacement**, not the actual provider-chain bill, prices recorded significance/Render tokens at Groq GPT-OSS-120B ($0.15/$0.60 per million input/output), other features at GPT-OSS-20B ($0.075/$0.30). Thirty-day extrapolation uses the seven measured days, no prompt-cache discount, excludes unknown failed-attempt tokens and changes in reasoning usage. [Groq price source](https://console.groq.com/docs/models).

| Demand | Logical operations/day | Illustrative paid API EUR / DKK net per 30 days | With illustrative 25% VAT EUR / DKK | Additional CX43 / GPU hosting net |
|---|---:|---:|---:|---:|
| Current | 273 | 1.97 / 14.73 | 2.46 / 18.41 | €12 / €214 |
| 3× | 820 | 5.91 / 44.19 | 7.39 / 55.24 | €12 / €214 |
| 10× | 2,733 | 19.71 / 147.30 | 24.63 / 184.13 | €12 / €214 |

Fixed hosting costs do not establish capacity at 3×/10×; fallback load, queueing and quality remain unmeasured. Free capacity cannot be extrapolated linearly. Groq's published GPT-OSS planning limits include 8K TPM / 200K TPD per model; actual organization limits may differ. Cloudflare provides 10,000 neurons/day, then requires paid capacity; its pinned Llama price is $0.293/$2.253 per million input/output. [Groq limits](https://console.groq.com/docs/rate-limits), [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/). Observed budget skips and quota errors already show finite capacity; Gemini account limits and API billing dashboards were not inspected; no matching invoice email was found in the bounded billing search.

Against a genuinely €0 API baseline, positive infrastructure/operations cost has **no cost-saving break-even**. Against the illustrative paid workload, CX43 hosting alone breaks even at approximately **6.1×** volume if it replaces everything perfectly; the separate GPU at **108.6×**, excluding setup and labour. Keeping significance external leaves only **€0.31/month** of illustrative replaceable simpler-task cost: CX43 then needs approximately **38.4×** that volume before labour/fallback. At €50/month operating effort, the full-replacement CX43 threshold rises to approximately **31.5×**. These are scenario arithmetic, not measured savings or a reason to buy a server.

## Low-risk next decision

Keep cloud/hybrid production unchanged. If self-hosting is revisited for capacity rather than savings, first finish an isolated Linux benchmark on already-approved hardware, including measured peak RSS, queueing at the observed bursts and 3×/10× demand, CPU steal/iowait, cancellations and bot/DB headroom. Freeze a privacy-safe real-context evaluation set, obtain independent blinded labels and compare the existing baseline and candidate on the same cases; review final Telegram text for facts/usefulness. No release gate is inferred from this small synthetic screen.

llama.cpp is preferred for a controlled experiment because it directly exposes context, slots, threads, GGUF and schema-constrained OpenAI-compatible serving. [Ollama](https://docs.ollama.com/api/openai-compatibility) is convenient but adds model lifecycle/default management; its OpenAI API is a subset and its API key is ignored locally. [Both require backend validation](https://docs.ollama.com/capabilities/structured-outputs). GPU-oriented vLLM would add driver/runtime/memory complexity without a tested need on this host. Pin the eventual engine build and model checksum; never size memory from the compressed weights alone.

A later local-provider design needs a new explicit provider registration/capability adapter: current `KNOWN_PROVIDERS` accepts only Groq, Gemini and Cloudflare, so an env-only Ollama URL is not supported. Any local slot must replace an existing attempt rather than add an extra one, retain bounded fallback and the logical operation's telemetry, and stay outside recipient loops. Hard decisions remain on the existing cloud path. Replacing a configured slot preserves only the attempt ceiling, not actual call volume: a less reliable local model could increase fallback attempts. The same-workload evaluation must show no increase in actual LLM attempts before any adoption claim. Prototype isolation should include CPU/RAM/PID and queue limits, private endpoint/authentication, no bot/DB secrets or Docker socket, and minimal egress. Monitor deadline/validation failures, queue age, memory/OOM and bot health. Roll back by disabling the local route and returning to the prior provider configuration; no schema migration is proposed. **Any production implementation, resize or paid capacity remains a separate owner decision.**

Evidence: `workload.json`, `workload_queries.json`, `host_evidence.json`, `cost_model.json`, `corpus.json`, candidate results/summary, artifact/source manifests and reproducible local runner accompany this report. The corpus includes repository prompt templates populated exclusively with synthetic data, enabling reproduction. Raw production request payloads, private user content, invoice personal details, raw server logs, model weights and credentials are excluded from the shareable evidence pack. Task-owned process resource counters are intentionally included as benchmark evidence.

In the backend-accepted Qwen2.5-7B normal weekly fixture, 0.042% hourly changes become 0.42%, null market-cap/volume fields become invented dollar figures, and GRAM/SOL 24-hour moves are described as increases despite supplied -0.5%. It also invents weekday history and gives strategy wording. These raw/backend-accepted errors were not tested through final Telegram assembly.
