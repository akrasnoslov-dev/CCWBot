"""Replay published CCW-20 final-copy candidates offline through actual assembly.

No providers, credentials, network calls, or Telegram delivery.
Published paired messages were already assembled once; this replay tests the
new deterministic final action guard against all 20 frozen market contexts.
It is not a new LLM benchmark or an independent human quality review.
"""

import json
import re
from pathlib import Path

from bot import alerts

_ROOT = Path(__file__).resolve().parents[1]
_PAIRS = (
    _ROOT / "research" / "event_alerts" / "ccw20_final_render_ab_20261026"
    / "CCW20_PAIRED_MESSAGES.md"
)
_SOURCE = (
    _ROOT / "reports" / "event-alert-review-20261016"
    / "v2_private_sanitized.json"
)
_BAD_IDS = {"ev_0ab71234c9080ecc", "ev_4bba21dd01bc8372"}
_EXPECTED_SAFE_ACTION = (
    "Watch the next observed interval for further reversal toward the decline "
    "or a return to the analysed-window rise."
)


def _recorded_candidate_pairs():
    text = _PAIRS.read_text(encoding="utf-8")
    header = re.compile(r"(?m)^## \d+\. (ev_[a-z0-9]+) — (BTC|ETH|GRAM|SOL)\s*$")
    matches = list(header.finditer(text))
    assert len(matches) == 20, "Frozen cohort must remain exactly 20 pairs"
    result = []
    for i, matched in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[matched.end():end]
        situation = re.search(r"(?m)^\*\*B Situation:\*\* (.+)$", body)
        action = re.search(r"(?m)^\*\*B Possible Action:\*\* (.+)$", body)
        assert situation and action, f"Missing recorded final pair for {matched.group(1)}"
        result.append((
            matched.group(1),
            matched.group(2),
            situation.group(1).strip(),
            action.group(1).strip(),
        ))
    assert len({item[0] for item in result}) == 20
    return result


def test_ccw20_replay_all_20_recorded_candidate_final_pairs_without_llm_calls():
    # The old frozen cohort contains some unsupported claims. Reject those
    # before delivery; preserve accepted LLM prose without a Python fallback.
    data = json.loads(_SOURCE.read_text(encoding="utf-8"))
    by_id = {case["id"]: case for case in data["cases"]}
    checked, invalid = [], set()
    for event_id, symbol, situation, action in _recorded_candidate_pairs():
        market = by_id[event_id]["input"]["market"]
        decision = alerts.EventAnalysisDecision(
            symbol=symbol, should_alert=True, event_key=None, title=None,
            message_body=situation, possible_action=action,
            related_news_ids=[], urgency="normal", confidence="high",
            reason_for_no_alert=None,
        )
        checked.append(event_id)
        try:
            result = alerts._build_event_alert_payload(
                decision=decision, input_payload={"market": market}, related_news=[]
            )["plain_text"]
        except alerts.EventAnalysisValidationError:
            invalid.add(event_id)
            continue
        assert result.count("Situation:\n") == 1
        assert result.count("Possible action:\n") == 1
        assert result.endswith("Not financial advice.")
        final_situation = result.split("Situation:\n", 1)[1].split("\n\n", 1)[0]
        final_action = result.split("Possible action:\n", 1)[1].split("\n\n", 1)[0]
        assert final_situation == situation
        assert final_action == action
    assert len(checked) == 20
    assert _BAD_IDS <= invalid
