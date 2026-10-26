# CCWBot Event Alert: two independent human reviewers

Private real-market sample, 200 contexts (50 each BTC/ETH/GRAM/SOL).
Never commit or publicly post this folder.
Reviewers must NOT see each other's answers or discuss cases until both finish.

Phase 1: each reviewer opens their own reviewer_A/B_phase1_significance.csv.
Fill the column warrant (alert/no_alert/ambiguous) for all 200 rows:
alert = one new alert deserved, no_alert = noise, ambiguous = insufficient or unclear.
Base decisions on actual market snapshots, 24h context and selected news.
News alone must not cause alert; do not apply any fixed percentage threshold.
Write a short warrant_reason for ambiguous or interesting cases.
No original bot decisions are displayed in the phase 1 file.

Both phase-1 files must be saved and locked BEFORE phase-2 work.

Phase 2: each reviewer opens their own reviewer_A/B_phase2_final_message.csv.
Only actually delivered alerts appear; inspect their final Telegram text.
For each message mark useful (yes/no), factual (yes/no).
Useful = adds a grounded market relationship or useful next market observation.
Factual = no invented number, direction, period, catalyst or trajectory.
Explain any no in reason_if_no.

Return your two completed CSVs privately to project owner, in UTF-8.
Keep case_id and all evidence columns unchanged.
Do not share the unblinded v2_private_sanitized.json with evaluators.

Sampling is intentionally stratified: 18 delivered, 7 positive/undelivered,
25 no-alert cases per symbol. It is NOT a natural-frequency population sample.
The sampled baseline decision and any delivered message remain hidden until evaluation.
No correctness/quality metrics can be computed until two humans independently label.
Full significance-stage inputs retain exactly 11 whitelisted original market fields;
positive stored inputs have subsequent render-stage output stripped.
