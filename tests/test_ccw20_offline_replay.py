"""Replay published CCW-20 final-copy candidates offline through actual assembly.

No providers, credentials, network calls, or Telegram delivery.
Published paired messages were already assembled once; this replay tests the
new deterministic final action guard against all 20 frozen market contexts.
It is not a new LLM benchmark or an independent human quality review.
"""

import json
import re
from pathlib import Path

import bot.alerts as alerts
from bot.alerting.event_analysis import EventAnalysisDecision


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
    data = json.loads(_SOURCE.read_text(encoding="utf-8"))
    by_id = {case["id"]: case for case in data["cases"]}
    checked = []
    corrected = []

    for event_id, symbol, situation, action in _recorded_candidate_pairs():
        case = by_id[event_id]
        assert case["symbol"] == symbol
        market = case["input"]["market"]
        decision = EventAnalysisDecision(
            symbol=symbol, should_alert=True, event_key=None, title=None,
            message_body=situation, possible_action=action,
            related_news_ids=[], urgency="normal", confidence="high",
            reason_for_no_alert=None,
        )
        text = alerts._build_event_alert_payload(
            decision=decision,
            input_payload={"market": market},
            related_news=[],
        )["plain_text"]
        assert text.count("Situation:\n") == 1
        assert text.count("Possible action:\n") == 1
        assert text.endswith("Not financial advice.")
        final_situation = text.split("Situation:\n", 1)[1].split("\n\n", 1)[0]
        final_action = text.split("Possible action:\n", 1)[1].split("\n\n", 1)[0]
        assert final_situation.strip() and final_action.strip()
        assert not re.search(
            r"(?i)\b(?:if|when)\b[^.!?]{0,160}"
            r"\b(?:extend\w*|continu\w*|sustain\w*)\b[^.!?]{0,180}"
            r"\b(?:diverg\w*|converg\w*|align\w*)\b",
            final_action,
        )
        if event_id in _BAD_IDS:
            assert final_action == _EXPECTED_SAFE_ACTION
            assert "latest decline" in final_situation
            assert "analysed-window rise" in final_situation
            assert final_action != action
            corrected.append(event_id)
        checked.append(event_id)

    assert len(checked) == 20
    assert set(corrected) == _BAD_IDS
