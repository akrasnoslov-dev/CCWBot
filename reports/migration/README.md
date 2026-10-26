# Historical migration provenance — 2026-10-26

Original research was temporarily committed below
`research/event_alerts/versioned_evidence_20261026/reports/` before all Git
blobs were moved into the correct repository-root `reports/` directory.

- [`IMPORT_MANIFEST_20261026.json`](IMPORT_MANIFEST_20261026.json): immutable
  original 426-file audit, 331 copied and 95 excluded. The recorded
  `source_tree` and `imported_tree` are **historical staging locations**,
  not current Git paths.
- [`UTF16_RECOVERY_MANIFEST.json`](UTF16_RECOVERY_MANIFEST.json): original
  SHA-256 and decoded JSON equivalence for two formerly UTF-16 scoring files,
  now stored under `reports/event-alert-review-20261016/` at the original
  relative paths.
- 90 excluded `ccw25-20261019/dev-source/` files are existing source-code
  snapshots at Git commit `e0b47e4c95399f930a6a63554ecfe058b58d8cd5`.
  Source file hashes remain at `reports/ccw25-20261019/dev_source_manifest.json`.
- 3 host-specific metrics files were deliberately not published:
  `host_evidence.json`, `resource_samples.jsonl`, `workstation.json`.

No duplicate copy of the research archive remains under `research/` on `dev`.

