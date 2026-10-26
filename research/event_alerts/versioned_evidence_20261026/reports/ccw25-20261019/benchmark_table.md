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
