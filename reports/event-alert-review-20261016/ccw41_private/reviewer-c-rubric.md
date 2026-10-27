# CCW-41 Reviewer C significance rubric v1

Assess each case independently. Decide only whether the supplied market situation warrants an
automatic Event Alert. Do not assess final-message writing quality and do not infer any prior bot,
provider, or human decision.

Use only evidence present in the case:

1. Decide whether the current market movement is materially noteworthy for this asset in its
   supplied context. Market movement is primary; news is supporting context only.
2. If material, decide whether it is meaningfully new relative to the supplied prior-alert and
   recent-event context. A continuation or near-duplicate is not automatically new.
3. Use `alert` only when the available market evidence supports both materiality and novelty.
4. Use `no_alert` for routine movement, news-only situations, or non-novel continuation.
5. Use `ambiguous` when materiality or novelty cannot be decided from the supplied evidence. State
   exactly what is missing or conflicting.

Percentages and other numbers are evidence, never fixed decision thresholds. Do not invent market
facts, causal explanations, volume, liquidity, sentiment, or events not present in the case. Cite
the case field paths that support the decision. Confidence expresses confidence in applying this
rubric to the supplied evidence; it is not confidence that the judgment is ground truth.

Return one result for every supplied opaque case ID using the required JSON schema. Never summarize
multiple cases into one decision, compare cases with one another, or seek labels and predictions in
other files.
