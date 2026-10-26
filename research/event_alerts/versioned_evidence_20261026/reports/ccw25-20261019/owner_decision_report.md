# CCW-25 — Owner decision

**NO-GO for production self-hosting now. Keep the current cloud routing; do not buy a VPS upgrade or GPU server for this workload.** Research dated 19 October 2026. Development reference: `e0b47e4`.

## Evidence behind the decision

The existing host has **2 vCPU, 3.73 GiB RAM, no swap, no observed compute GPU and 7.63 GiB disk free**. Historical sampled available memory fell to **2.60 GiB**. The live status check listed PostgreSQL without the bot and reported failed health, so current free memory cannot establish normal bot-plus-DB headroom. No repair or production change was attempted.

The latest actual invoice, issued 15 October for **September**, is **€4.49 net / €5.61 with 25% Danish VAT**: CX23 €3.99 plus IPv4 €0.50. That is approximately **DKK 33.56 / 41.93**. October accrual and the account-specific resize price are unverified.

Read-only investigator queries for **12–19 October UTC** found **1,913 logical LLM operations, 2,076 attempted requests and 1,497 zero-request skips**. Average operations/day: significance **192**, Render **30.86**, News **28.43**, Heartbeat **13.86**, daily reports **6.86**, weekly reports **1.29**. Recorded tokens total **1,548,644 input / 549,419 output**; 134 attempts lack token counts. Fallback recovered 150 operations; 17 had no successful attempt. There were 39 timeouts and 52 schema-error rows.

Peak timestamped telemetry buckets contained six attempted rows or eight logical operations/minute. **True concurrency, production p50/p95 latency, cache-hit rates and actual API spending remain unknown.** Telemetry lacks duration fields; absent invoice emails do not prove zero spending. Cached market-wide work already serves many recipients. The window spans configuration changes; these averages are not a steady-state forecast.

## Models actually screened

CPU **llama.cpp `b11734`**, **GGUF Q4_K_M**, context **8192**, **four threads**, **one slot**, temperature 0. All weight revisions and SHA-256 hashes are preserved.

| Specific model | Commercial-use license | Weight download |
|---|---|---:|
| [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) | Apache-2.0 | 2.50 GB |
| [Microsoft Phi-4-mini-instruct, 3.8B](https://huggingface.co/microsoft/Phi-4-mini-instruct) | MIT | 2.49 GB |
| [Qwen2.5-7B-Instruct, 7.61B](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | Apache-2.0 | 4.68 GB |

| Model | Requests | JSON / backend-valid | Within feature deadline | Peak working set GiB |
|---|---:|---:|---:|---:|
| Qwen3-4B | 36 | 36/36 / 34/36 | 18/36 | 5.24 |
| Phi-4-mini | 19 | 19/19 / 17/19 | 12/19 | 4.80 |
| Qwen2.5-7B | 19 | 17/19 / 17/19 | 0/19 | 6.93 |


Qwen3-4B fabricated report catalysts/timelines, misstated a Render period, and described stable conditions without sufficient evidence. Phi-4-mini returned generic/unsupported report content and an empty required Heartbeat action. All three missed at least one significance fixture; Qwen2.5-7B incorrectly alerted on the news-only fixture. Some Render rejections appear to be guard false positives rather than proven model factual errors. These are manually inspected fixture findings, not measured real-world quality rates.

**Feature decision: keep significance, Render, News Intelligence, Heartbeat and daily/weekly reports external. No tested model is recommended for production.** This is a synthetic compatibility/performance screen on a Windows i5-12400F workstation, not a Hetzner/Linux capacity benchmark or independently labelled product-quality evaluation. Small-sample p95 and repeated deterministic outputs do not establish reliability.

## What each option costs

Hosting-only estimates, EU region and one IPv4, full-month cap. DKK uses ECB 16 October **7.4748/EUR**. Baseline is the latest historical invoice. Paid API fallback and operator labour are additional.

| Option | Net EUR / DKK monthly | With 25% VAT EUR / DKK | Incremental net EUR / DKK | Vendor setup |
|---|---:|---:|---:|---:|
| A. Existing CX23 | 4.49 / 33.56 | 5.61 / 41.93 | 0 / 0 | €0; local inference NO-GO |
| B. CX33, 4 vCPU / 8 GB / 80 GB | 8.99 / 67.20 | 11.24 / 84.00 | 4.50 / 33.64 | €0 |
| B. CX43, 8 vCPU / 16 GB / 160 GB | 16.49 / 123.26 | 20.61 / 154.07 | 12.00 / 89.70 | €0 |
| C. Separate GEX45, 24 GB VRAM / 64 GB RAM, retain bot VPS | 218.49 / 1,633.17 | 273.11 / 2,041.46 | 214.00 / 1,599.61 | €209 net / DKK 1,562.23; €261.25 / DKK 1,952.79 with VAT |
| D. Existing cloud chain | 4.49 / 33.56 **+ unknown API bill** | 5.61 / 41.93 plus unknown API spending and applicable tax | €0 hosting | €0 |

Prices checked 19 October: [Hetzner cloud](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/), [IPv4](https://docs.hetzner.com/cloud/servers/primary-ips/overview/), [GPU order list](https://robot.hetzner.com/order). GPU prices are normalized from the displayed German-VAT price. Availability and resize quote need account confirmation. On resized/separate options, included storage is sufficient for one selected model; no extra model backup/storage purchase is assumed. Optional CX43 Cloud backups add approximately **€3.20 net / DKK 23.90 monthly**. Rented-host electricity is included. Planning effort: 6–12 hours setup plus 1–2 hours/month; at an illustrative €50/hour, €300–600 once plus €50–100/month. Workstation benchmark energy was not metered.

## Economics and next step

At [published Groq token prices](https://console.groq.com/docs/models), an illustrative paid substitute for recorded tokens costs **€1.97 / DKK 14.73 net per 30 days**; **3× = €5.91 / DKK 44.19**, **10× = €19.71 / DKK 147.30**. This is **not the actual multi-provider bill**: missing failure tokens, tokenizer/reasoning differences and account billing remain unknown. With illustrative 25% VAT those amounts are €2.46, €7.39 and €24.63. Fixed hosting at 3×/10× does not prove capacity. Free quotas are finite and already cause skips; [Groq limits](https://console.groq.com/docs/rate-limits) and [Cloudflare's 10,000 neurons/day](https://developers.cloudflare.com/workers-ai/platform/pricing/) cannot be treated as unlimited.

Positive hosting cost never pays back against a genuinely €0 API baseline. Against the illustrative paid workload, CX43 hosting alone breaks even around **6.1×** perfect full replacement; GPU around **108.6×**, before setup/labour. A hybrid keeping significance external can displace only about **€0.31/month** in this scenario, so CX43 needs approximately **38.4×** that simpler-task volume before labour/fallback.

If capacity later justifies another experiment, use isolated already-approved hardware: **8 GB / 4 vCPU minimum planning envelope for 4B, 16 GB / 8 vCPU safer for co-location**, subject to Linux measurements. Prefer pinned llama.cpp for explicit memory/context/slot controls; Ollama does not solve quality or latency. A local provider needs code registration, schema/capability handling, resource/queue limits and private access. It must replace an existing attempt, preserve bounded fallback, operation telemetry and shared analyses, and stay outside recipient loops. Replacing a slot alone does not guarantee unchanged actual call volume; worse local success rates can increase fallback attempts.

Before any implementation: run a burst/soak test and independent baseline-versus-candidate evaluation on frozen privacy-safe real contexts, including final Telegram text. Disable the local route to roll back; no schema migration is proposed. **Production changes, upgrades and paid services require a separate owner decision.**

No production changes or paid services were made. The approved downloads and benchmarks were local and used synthetic inputs. Detailed measurements, source links, limitations, inputs, outputs and reproduction commands are in the accompanying technical appendix and evidence pack.
