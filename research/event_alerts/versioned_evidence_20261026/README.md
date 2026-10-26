# Versioned Event Alert experiment evidence (2026-10-26)

This directory preserves CCWBot historical event-alert benchmark inputs, prompts, recorded decisions, owner/reviewer scores, reports, and supporting reproducibility metadata. These resources are versioned in **GitHub `dev`**, not dependent on an individual developer workstation. See the [research index](../README.md) for authoritative navigation.

## Provenance and counts

- `reports/`: **331** original, byte-for-byte research files.
- `IMPORT_MANIFEST.json`: original audit of **426** staged files, including **95** exclusions, with per-file SHA-256.
- `utf16_recovered/`: **2** previously excluded owner-scoring JSON files, transcoded from UTF-16LE to UTF-8, checked for JSON data equality and with original/converted SHA-256 preserved.
- **90** archived `ccw25-20261019/dev-source/` application files were duplicate source-code snapshots already tracked at [commit `e0b47e4`](https://github.com/akrasnoslov-dev/CCWBot/tree/e0b47e4c95399f930a6a63554ecfe058b58d8cd5); all 90 paths were verified in that Git tree.
- **3** machine-specific resource/host files remain deliberately uncommitted: `ccw25-20261019/host_evidence.json`, `resource_samples.jsonl`, and `workstation.json`. Their hashes and names remain in the audit manifest.

**The original manifest is immutable historical evidence.** It still states 95 exclusions from the first import even though 2 were subsequently recovered and 90 were proven redundant via Git history. Do not alter that original manifest or reclassify the original transfer as 426 physical files.

This material is research evidence, not production runtime configuration. Existing frozen scripts may contain old Windows paths, providers, and model binaries. Saved experiment cases, LLM outputs, and owner judgments are now accessible from the same GitHub repository, so historical conclusions do not require access to the Windows reports directory.

Never commit credentials, Telegram user identifiers, production logs, database backups, machine secrets or operational details. This was automated heuristic screening, not a security audit guaranteeing complete anonymization.
