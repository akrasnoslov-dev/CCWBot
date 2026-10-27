from pathlib import Path
p = Path(r"D:\Projects\CCWBot\scripts\ccw41_reviewer_c_audit.py")
s = p.read_text(encoding="utf-8")
start = s.index("def _aggregate_markdown(aggregate: dict) -> str:\n")
end = s.index("\n\ndef _narrative_findings(", start)
f = '''def _aggregate_markdown(aggregate: dict) -> str:
    """Publishable, aggregate-only exploratory report; never include case identity."""
    lines = [
        "# CCW-41 exploratory Reviewer-C agreement/disagreement",
        "",
        "Reviewer A remains the authoritative reference for CCW-16/29. Reviewer C is an "
        "independent AI audit, not an adjudicator or majority vote.",
        "",
        f"Dataset: {aggregate['case_count']} frozen cases. "
        f"Original A/B conflicts: {aggregate['a_b_conflict_subset']['count']}.",
        "",
        "## Overall distributions",
        "",
        "| Reviewer | alert | no_alert | ambiguous |",
        "|---|---:|---:|---:|",
    ]
    for reviewer, counts in aggregate["distributions"].items():
        lines.append(
            f"| {reviewer} | {counts['alert']} | {counts['no_alert']} | "
            f"{counts['ambiguous']} |"
        )
    lines += [
        "",
        "## Pairwise agreement (all 200 cases)",
        "",
        "| Pair | Agreed | Disagreed | Rate |",
        "|---|---:|---:|---:|",
    ]
    for name, values in aggregate["pairwise"].items():
        lines.append(
            f"| {name} | {values['agreement']}/{values['total']} | "
            f"{values['disagreement']} | {values['agreement_rate']:.1%} |"
        )
    conflicts = aggregate["a_b_conflict_subset"]
    lines += [
        "",
        "## Original A/B disagreement subset",
        "",
        f"Of {conflicts['count']} original disagreements: "
        f"C agrees with A in {conflicts.get('c_agrees_a', 0)}, "
        f"with B in {conflicts.get('c_agrees_b', 0)}, "
        f"with neither in {conflicts.get('c_agrees_neither', 0)}, "
        f"and selected ambiguous in {conflicts.get('c_ambiguous', 0)}.",
        "These are descriptive categories, not votes or corrections to human labels.",
        "",
        "## Reviewer A decisive vs ambiguous",
        "",
    ]
    for name, key in (("A decisive", "a_decisive"), ("A ambiguous", "a_ambiguous")):
        values = aggregate[key]["A-C"]
        lines.append(
            f"- {name}: A/C agreement {values['agreement']}/{values['total']}; "
            f"disagreement {values['disagreement']}/{values['total']}"
        )
    lines += [
        "",
        "## Differences by symbol (A vs C)",
        "",
        "| Symbol | Disagreements | Denominator |",
        "|---|---:|---:|",
    ]
    for symbol in ("BTC", "ETH", "GRAM", "SOL"):
        values = aggregate["breakdowns"][f"symbol:{symbol}"]["A-C"]
        lines.append(f"| {symbol} | {values['disagreement']} | {values['total']} |")
    lines += ["", "## Observed scenario and tag splits (A vs C)", ""]
    for group, metrics in aggregate["breakdowns"].items():
        if not group.startswith(("scenario_type:", "tag:")):
            continue
        values = metrics["A-C"]
        lines.append(
            f"- {group}: {values['disagreement']}/{values['total']} disagreements"
        )
    impact = aggregate["high_impact_counts"]
    lines += [
        "",
        "## High-impact disagreement counts",
        "",
        f"- A=alert, C=no_alert: {impact['a_alert_c_no_alert']}",
        f"- A=no_alert, C=alert: {impact['a_no_alert_c_alert']}",
        f"- A=ambiguous, C=decisive: {impact['a_ambiguous_c_decisive']}",
        "",
        "## Confirmed observations",
        "",
    ]
    lines += [f"- {item}" for item in aggregate["confirmed_patterns"]]
    lines += ["", "## Hypotheses requiring owner judgment", ""]
    lines += [f"- {item}" for item in aggregate["hypotheses_for_owner_review"]]
    lines += ["", "## Limitations and decisions", ""]
    lines += [f"- {item}" for item in aggregate["limitations"]]
    lines += [
        "- Review the restricted private shortlist against original market evidence and "
        "the independent rationales before deciding whether labels need a new protocol.",
        "- Any benchmark relabeling, evaluation-policy change, or CCW-16/29 acceptance "
        "change requires separate owner approval and versioning.",
        "- Cohen's kappa and all subgroup rates in the aggregate JSON are descriptive "
        "only; small groups and three-class ambiguity limit inference.",
        "",
    ]
    return "\\\\n".join(lines).replace("\\\\n", "\\n")
'''
# Fix literal backslash n expression in generated Python exactly
f=f.replace('return "\\\\n".join(lines).replace("\\\\n", "\\n")','return "\\n".join(lines)')
s=s[:start]+f+s[end:]
p.write_text(s,encoding="utf-8",newline="\n")
t=Path(r"D:\Projects\CCWBot\tests\test_ccw41_reviewer_c_audit.py")
x=t.read_text(encoding="utf-8")
x=x.replace(
'def test_frozen_protocol_rejects_edited_rubric(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:',
'def test_frozen_protocol_rejects_edited_rubric(\\n    tmp_path: Path, monkeypatch: pytest.MonkeyPatch\\n) -> None:'
)
t.write_text(x,encoding="utf-8",newline="\n")
print("Expanded aggregate report and fixed Ruff width.")
