# Event Alert research archive

This directory tracks verified, versioned market-significance experiments from the CCWBot project.

## Existing evidence
- Frozen source cohort: 200 BTC/ETH/GRAM/SOL observations (50 per symbol)
- Frozen dataset SHA-256: `ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d`
- Six GPT-6 Luna prompt variants: production, balanced, refined v2, refined v3, quality-first, economical
- 1,200 saved decisions (200 per variant) and 66 owner blind disagreement labels (24 alert, 34 no_alert, 8 ambiguous)
- 58 decisive cases suitable for conditional error counting; eight ambiguous excluded
- Aggregate evaluation: [Owner blind disagreement findings](../../docs/event_alert_owner_disagreement_20261026.md)

## Data handling
Only publish verified data without credentials, personal identifiers, private bot messages, raw production logs or database exports. The original user-provided archive also contains sensitive forensic material and duplicated test output, and is NOT suitable for a wholesale public commit. Treat the published evidence as a documented subset until a file-level audit confirms complete reproducibility.

## Status
Original evidence snapshot: 26 October 2026. Detailed per-case files are not in this directory yet. Do not claim that the historical research archive has been entirely migrated.
