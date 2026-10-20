"""Prepare cost-conscious Event Alert significance candidates; OFFLINE ONLY.

Run: python scripts/event_significance_candidates.py --benchmark <private-frozen.json>
No API calls, prompt/response dumps, production changes or inferred accuracy scores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.alerting.event_identity import _json_dumps  # noqa: E402
from bot.services.ai_agent_groq import (  # noqa: E402
    _EVENT_SIGNIFICANCE_INSTRUCTIONS,
    _event_significance_prompt_payload,
    build_event_significance_prompt,
)

# Additions are hypotheses to compare with the current production prompt.
# Neither changes the schema, model, facts, or the LLM's exclusive authority.
CANDIDATE_ADDITIONS = {
    "materiality_first": (
        "Calibration focus: before considering news, c24, prev or cnt, explain to "
        "yourself whether the present cw over w merits a notification for this "
        "specific asset. Inspect same-window pw and actual s path for evidence "
        "of unusual size, persistence or acceleration. A short-lived wobble or "
        "a counter-move inside a larger c24 direction is not automatically "
        "a reversal. Missing c30/c60 or sparse s never proves rapid motion. "
        "Do not transform these observations into fixed cutoffs."
    ),
    "trajectory_evidence": (
        "Calibration: decide market significance using confirmed movement, "
        "not headlines or raw event counts. Compare the observed full-window "
        "change cw and the actual sampled path s with the same-asset percentile "
        "pw. A genuinely substantial current decline, surge or sustained "
        "acceleration can be material even if the 24h move is older, recent "
        "notifications exist, or a partial bounce softens the last 30 minutes. "
        "Do not reject significant full-window evidence merely because c30/c60 "
        "are absent; do not invent missing path details either. Conversely "
        "a minor wiggle, a sign flip versus c24, or a news headline is never "
        "itself a reversal or major event. Require demonstrated size and "
        "coherent path for reversal or fast_move, considering the asset's "
        "usual movement. Only after judging materiality consider novelty; "
        "recent count cnt may reduce novelty but does not erase a fresh, "
        "separately supported price event. No price, speed, or percentile cutoffs."
    ),
    "relative_displacement": (
        "Calibration protocol: begin with observed cw over w and pw, assessing "
        "the CURRENT displacement relative to normal moves for this coin. "
        "Do not demand an extraordinary headline, an invented catalyst or "
        "continuous directional motion when the supplied current displacement "
        "is itself clearly notable for this asset. A strong same-asset "
        "percentile with a coherent sampled path supports materiality; the "
        "direction of c24 cannot cancel it. Equally, an unremarkable tiny "
        "current displacement cannot become material merely because c24 "
        "points the other way, a short segment moves faster, or news arrived. "
        "Examine actual s timestamps/prices before claiming a reversal, "
        "speed-up or persistence; absent short-window measures do not "
        "establish those patterns. Q2 novelty: prev may describe a specific "
        "comparable earlier move; cnt only counts past events and does not "
        "prove this move repeats them. Do not infer repetition from counts "
        "alone. Accept new when the current material displacement is "
        "distinct from any evidenced prior event; reject a mere extension "
        "or replay of the same evidenced move. Lack of evidence for novelty "
        "is not proof of new. Choose the reason only after these judgments. "
        "No numeric cutoffs, automatic percentile gates or headline triggers."
    ),
    "balanced_novelty": (
        "Calibration focus: keep Q1 materiality and Q2 novelty strictly separate. "
        "A demonstrably noteworthy present move may be material even if recent "
        "market events were frequent; cnt and prev reduce novelty only when "
        "the present path merely continues or repeats their described move. "
        "A genuinely changed current path may be new despite earlier alerts. "
        "But a fresh timestamp, headline or counter-move alone is not a new "
        "market event. Use pw and s as supporting evidence, never thresholds."
    ),
}

# Unlike additive pilots, this is a full, shorter replacement of the
# over-conservative significance instructions. Still OFFLINE; never live.
CANDIDATE_REPLACEMENTS = {
    "rebalanced_core": "\n".join((
        "Decide if the CURRENT price event deserves an interruption now. "
        "Produce exactly one JSON object. Assess meaningful moves positively "
        "when their evidence is strong; do not default to rejecting everything. "
        "No fixed numeric cutoff or automatic percentile threshold.",
        "Step 1 materiality: start from CURRENT cw over w and same-asset "
        "30-day absolute-move percentile pw. Ask whether this net displacement "
        "is genuinely noteworthy for this particular asset. A clearly unusual "
        "current movement with a grounded sampled path can be material without "
        "fresh news, proven acceleration, or perfect directional persistence. "
        "Do not discard current-window evidence because c24 is old, c30/c60 "
        "are missing or a partial bounce follows. Conversely, a small ordinary "
        "cw stays routine even if the price direction flips against c24, "
        "a headline is new, or a snapshot interval looks fast.",
        "Step 2 novelty: if Q1 is material, compare the present path/move with "
        "prev when comparable. cnt merely counts previous events, not their "
        "contents: it cannot prove the current move is a duplicate. Label new "
        "when a separately meaningful current displacement or demonstrated "
        "change is not merely an evidenced continuation of the previous "
        "event. If the same evidenced market path simply persists with no "
        "new substantive development, label continuation/repeated. Unknown "
        "prior evidence does not justify asserting a specific repetition. "
        "If Q1 is not material, set novelty=unclear.",
        "Step 3 should_alert=true only when materiality=material AND novelty=new. Choose "
        "reason_code AFTER the decision. Positive reasons: unusual_move, "
        "fast_move, reversal, trend_acceleration, market_news_alignment. "
        "Negative reasons: routine_move, news_only, unclear. A news headline "
        "cannot by itself trigger an alert or prove causality. No invented "
        "speed, reversal, duration, price trend or market catalyst.",
        "Input:sym;m={s,w,c30,c60,cw,c24,cl,pw,p24};"
        "s=[[min,USD],...],0=now,<0=older;cw=% over w;"
        "pw,p24=30d same-asset abs-move percentiles,context not thresholds;"
        "prev={min,f,cw};cnt={h6,h24};n<=2 {t,r,mat,h};"
        ".042=.042%,not 4.2%; null=unknown.",
        "Return exactly symbol,materiality,novelty,should_alert,"
        "reason_code,confidence. symbol=sym. "
        "materiality=material|routine|unclear;"
        "novelty=new|continuation|repeated|unclear;"
        "confidence=low|medium|high. "
        "For true use material+new and a positive reason; for false "
        "use routine/unclear or continuation/repeated and a negative reason. "
        "sole-news=>false+news_only.",
    )),
}

# The last sent Event Alert is queried by symbol, across ALL recipients; it is
# not evidence that any particular recipient already saw this market event.
# Only the downstream per-recipient cooldown can make that determination.
CANDIDATE_REPLACEMENTS["global_prior_no_family"] = (
    CANDIDATE_REPLACEMENTS["rebalanced_core"].replace(
        "prev={min,f,cw}", "prev={min,cw}",
    )
    + "\nThe previous alert metadata is global to the asset, not proof of "
    "a repeat for any individual user. The only comparable prior facts "
    "provided are age and net analysed-window displacement: an old "
    "directional event-family label is deliberately withheld because "
    "it cannot identify the present trajectory. Do not invent a shared "
    "event identity from similar movement signs. A new noteworthy "
    "current displacement may be significant without being an entirely "
    "different directional family. Classify continuation only when "
    "the supplied present market path and compared prior displacement "
    "genuinely establish the same unchanged movement, not merely the "
    "previous notification or recent event count. Reject ordinary "
    "small movements, unsupported reversals and news-only stories. "
    "User-specific four-hour repeat suppression remains downstream."
)

CANDIDATE_REPLACEMENTS["global_prior_safe"] = (
    CANDIDATE_REPLACEMENTS["rebalanced_core"]
    + "\nSpecific novelty calibration: prev is the latest sent alert for this "
    "asset across ANY recipient, not a recipient-specific notification "
    "history or a proof of duplicate market analysis. Matching prev.f or "
    "the direction alone is insufficient to claim repetition. A substantial "
    "fresh movement of this coin can count as new even when it shares the "
    "direction or broad semantic family of the earlier alert, as long as "
    "the present observed market displacement is independently noteworthy "
    "rather than merely the same unchanged path. The backend, not this "
    "global snapshot, enforces the strict four-hour per-user event-family "
    "cooldown. This does not excuse small routine moves or unsupported "
    "reversal claims. Never invent missing evidence or numerical cutoffs."
)

CANDIDATE_REPLACEMENTS["path_facts"] = (
    CANDIDATE_REPLACEMENTS["global_prior_no_family"]
    + "\nAdditional observed path evidence path={eff,up,down,from_hi,from_lo}: "
    "eff is abs sampled net displacement divided by total abs travel (0 to 1), "
    "up is largest positive sampled adjacent-interval % change, down is "
    "largest negative, from_hi/from_lo are current price percent from "
    "the largest/smallest sampled price. These are verified descriptors, "
    "not extra alert thresholds. Judge the FULL current path and asset "
    "percentile first, checking whether the sampled trend is persistent "
    "or whipsawing and whether a true reversal or fresh move exists. "
    "A change in direction versus c24 or one fast segment is not "
    "by itself enough for a material market event. If path is absent, "
    "do not pretend these statistics are known."
)

# New hypothesis: the earlier pilots alternated between calling medium-sized
# movements "unusual" and suppressing large moves because of partial bounces or
# cross-recipient prior notifications. Evaluate evidence in that order, without
# ever turning sampled percentiles into hard numeric alert gates.
CANDIDATE_REPLACEMENTS["market_event_evidence"] = "\n".join((
    "Judge whether this exact current price movement is genuinely alert-worthy "
    "for this asset. Do not default to silence or to treating every directional "
    "change as important. No fixed numeric cutoff or automatic percentile gate.",
    "FIRST: examine the observed current analysed window cw, its magnitude "
    "relative to this coin's own 30-day move distribution pw, and the actual "
    "timestamped sample path s. pw is supporting context, not an alarm rule. "
    "For a modest ordinary displacement, require separately demonstrated "
    "substantial intra-window movement; a routine drift, a change of sign "
    "versus c24, or a brief wiggle is NOT a significant event. A meaningful "
    "displacement that is clearly exceptional in this asset's historical "
    "context IS material even without news or monotonically directional "
    "snapshots. If latest 30/60min movement partially counters a major "
    "full-window displacement, do not misclassify the major net movement "
    "as routine solely because of that small bounce.",
    "For trajectory descriptions, path={eff,up,down,from_hi,from_lo} "
    "is factual sampled evidence, NOT automatic cutoffs; eff measures net "
    "travel relative to all sampled travel; up/down are the greatest "
    "adjacent percentage moves; from_hi/from_lo the final distance from "
    "sample extremes. Consider whether the path independently corroborates "
    "movement rather than inventing reversal, speed or persistence.",
    "SECOND: evaluate novelty only after materiality. A global previous alert "
    "prev and aggregate counts cnt can provide evidence of a continuing "
    "unchanged event, but do not tell whether THIS subscriber was notified. "
    "Previous direction family, matching sign or recent high counts alone "
    "cannot veto a new independently material market event. Do not inflate "
    "routine moves to new just because earlier alert data are absent. "
    "Subscriber-specific four-hour cooldown occurs downstream.",
    "THIRD: should_alert=true only when materiality=material AND novelty=new. "
    "News headlines and 24h context never substitute for a noteworthy "
    "current-window price event. For true select unusual_move,fast_move,"
    "reversal,trend_acceleration or market_news_alignment ONLY when proven. "
    "For false choose routine_move,news_only or unclear. No invented cause.",
    "Input:sym;m={s,w,c30,c60,cw,c24,cl,pw,p24}; "
    "s=[[min,USD],...],0=now,<0=older; cw=% over w; "
    "pw,p24=30d same-asset abs-move percentiles; "
    "prev={min,cw};cnt={h6,h24};n<=2 {t,r,mat,h};"
    "path={eff,up,down,from_hi,from_lo};null=unknown;"
    ".042=.042%,not 4.2%. This is evidence, not a fixed policy.",
    "Output JSON exactly: symbol,materiality,novelty,should_alert,"
    "reason_code,confidence. symbol=sym;"
    "materiality=material|routine|unclear;"
    "novelty=new|continuation|repeated|unclear;"
    "confidence=low|medium|high. Positive must be material+new and "
    "positive reason. Negative must have compatible negative reason.",
))


# Test whether requiring a specific affirmative materiality argument suppresses
# routine-move false positives without hiding genuinely noteworthy paths.
CANDIDATE_REPLACEMENTS["contextual_materiality"] = (
    CANDIDATE_REPLACEMENTS["market_event_evidence"]
    + "\nDecision calibration: before selecting material, actively test the "
    "ordinary-market explanation. If the analysed-window displacement is "
    "typical for this asset in its supplied 30-day same-window context "
    "AND sampled prices show no independently substantial excursion, "
    "choose routine, even when there are headlines, a short reversal, "
    "or a new timestamp. Ordinary relative displacement is NOT a positive "
    "reason by itself. If the net movement looks ordinary but sampled "
    "path independently shows a genuinely major swing or strong turn, "
    "assess that evidence rather than suppressing it mechanically. "
    "Conversely a material, independently new full-window displacement "
    "remains material after a small partial bounce or a previous alert "
    "to another recipient. Explicitly distinguish a large path swing "
    "from a small noisy zigzag. Use the whole verified window and the "
    "asset's own context, never a universal number or hard percentile "
    "cutoff. If the evidence does not establish an interrupt-worthy "
    "market event, choose should_alert=false with routine_move or unclear."
)


# Test a structural alternative: evaluate the market event independently,
# leaving subscriber-specific repeat suppression to the delivery backend.
CANDIDATE_REPLACEMENTS["market_signal_path"] = "\n".join((
    "Decide whether the CURRENT asset price event is worthy of an alert. "
    "No fixed numeric cutoff or deterministic percentile threshold.",
    "Q1 materiality: judge actual current cw over w, same-asset pw, "
    "sampled price path s, and verified path evidence. "
    "path={eff,up,down,from_hi,from_lo}; eff is absolute net displacement "
    "over total abs sampled travel, up/down are the largest positive/negative "
    "adjacent sampled-interval percentage changes, from_hi/from_lo give "
    "current distance from sample extrema. This evidence is descriptive, "
    "not an automatic threshold or a guarantee of any trajectory. "
    "A substantial fresh downswing/upswing can be material without news. "
    "For a low net move, look for a genuine substantial intra-window "
    "swing before calling it material; a small wobble is still routine. "
    "A mere change against c24 or one fast sample is not a reversal.",
    "Q2 novelty: whether THIS current observed window contains an "
    "independently noteworthy movement or meaningful intra-window shift, "
    "not whether some other recipient previously received an alert. "
    "Previous delivered alerts and event counts are deliberately absent: "
    "they are global snapshots and cannot prove a specific recipient "
    "has already been informed. The backend separately enforces strict "
    "per-recipient semantic cooldown. When Q1 is material and this "
    "observed market window supports a noteworthy current event, "
    "set novelty=new; a verified insignificant wobble or merely stale "
    "context does not qualify. Do not infer prior alert identity.",
    "Q3 should_alert=true only when materiality=material AND novelty=new. "
    "Choose the positive reason AFTER Q1/Q2; use unusual_move,fast_move,"
    "reversal,trend_acceleration,market_news_alignment. If false use "
    "routine_move,news_only,unclear; sole-news cannot create materiality.",
    "Input:sym;m={s,w,c30,c60,cw,c24,cl,pw,p24};"
    "s=[[min,USD],...],0=now,<0=older;cw=% over w;"
    "pw,p24=30d same-asset abs-move percentiles; null=unknown;"
    "n<=2 {t,r,mat,h};path={eff,up,down,from_hi,from_lo};"
    ".042=.042%,not 4.2%. No prev or cnt.",
    "Return exactly symbol,materiality,novelty,should_alert,reason_code,"
    "confidence. symbol=sym; materiality=material|routine|unclear;"
    "novelty=new|continuation|repeated|unclear;"
    "confidence=low|medium|high. "
    "true requires material+new; false requires routine/unclear "
    "or continuation/repeated and a negative reason_code.",
))


def verified_path_facts(compact_market: dict) -> dict:
    """Independent price-path descriptors; no significance policy or cutoffs."""
    snapshots = compact_market.get("s")
    if not isinstance(snapshots, list) or len(snapshots) < 2:
        return {}
    try:
        values = [Decimal(str(item[1])) for item in snapshots]
    except (ValueError, TypeError, IndexError, InvalidOperation):
        return {}
    if any(not value.is_finite() or value <= 0 for value in values):
        return {}
    deltas = [
        (values[i] / values[i - 1] - 1) * Decimal("100")
        for i in range(1, len(values))
    ]
    distance = sum(
        (abs(values[i] - values[i - 1]) for i in range(1, len(values))),
        Decimal(0),
    )
    efficiency = (
        abs(values[-1] - values[0]) / distance if distance else Decimal(0)
    )
    high, low = max(values), min(values)
    return {
        "eff": round(float(efficiency), 4),
        "up": round(float(max([Decimal(0), *deltas])), 4),
        "down": round(float(min([Decimal(0), *deltas])), 4),
        "from_hi": round(float((values[-1] / high - 1) * 100), 4),
        "from_lo": round(float((values[-1] / low - 1) * 100), 4),
    }


def candidate_prompt(input_payload: dict, candidate: str) -> str:
    if candidate == "production":
        return build_event_significance_prompt(input_payload)
    if candidate not in CANDIDATE_ADDITIONS and candidate not in CANDIDATE_REPLACEMENTS:
        raise ValueError(f"Unknown candidate: {candidate}")
    # Existing candidates preserve the compact production data shape.
    # One new hypothesis removes the coarse global prior semantic family,
    # which does not establish whether the present market path is a repeat.
    # The frozen input and the strict response schema remain unchanged.
    instructions = (
        CANDIDATE_REPLACEMENTS[candidate]
        if candidate in CANDIDATE_REPLACEMENTS
        else _EVENT_SIGNIFICANCE_INSTRUCTIONS + "\n" + CANDIDATE_ADDITIONS[candidate]
    )
    payload = _event_significance_prompt_payload(input_payload)
    if candidate in ("global_prior_no_family", "path_facts", "market_event_evidence",
                      "contextual_materiality"):
        if isinstance(payload.get("prev"), dict):
            payload["prev"].pop("f", None)
    if candidate == "market_signal_path":
        payload.pop("prev", None)
        payload.pop("cnt", None)
    if candidate in ("path_facts", "market_signal_path", "market_event_evidence",
                      "contextual_materiality"):
        facts = verified_path_facts(payload["m"])
        if facts:
            payload["path"] = facts
    payload_json = _json_dumps(payload)
    return f"{instructions}\nInput JSON:\n{payload_json}"


def offline_inventory(dataset: dict) -> dict:
    from scripts.event_alert_benchmark import digest

    cases = dataset["cases"]
    variants = ("production", *CANDIDATE_ADDITIONS, *CANDIDATE_REPLACEMENTS)
    results = {}
    for variant in variants:
        size = []
        fingerprints = []
        for case in cases:
            # Don't print or persist private model inputs.
            if case["input_sha256"] != digest(case["input"]):
                raise ValueError("Frozen case input changed")
            prompt = candidate_prompt(case["input"], variant)
            size.append(len(prompt))
            fingerprints.append(hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        results[variant] = {
            "min_prompt_characters": min(size) if size else None,
            "max_prompt_characters": max(size) if size else None,
            "aggregate_prompt_fingerprint": hashlib.sha256(
                "\n".join(fingerprints).encode("ascii")
            ).hexdigest(),
            "measured_significance_precision": None,
            "measured_significance_recall": None,
            "provider_requests": 0,
        }
    return {
        "provenance": "OFFLINE_PREPARATION_ONLY",
        "dataset_sha256": dataset["dataset_sha256"],
        "cases": len(cases),
        "by_symbol": dict(sorted(Counter(c["symbol"] for c in cases).items())),
        "candidates": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    arguments = parser.parse_args()
    from scripts.event_alert_benchmark import load_frozen

    dataset = load_frozen(arguments.benchmark)
    print(json.dumps(offline_inventory(dataset), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
