"""Reproducible Event Significance A/B harness. Offline by default.

Fixture labels are synthetic hypotheses, not production ground truth.
Live mode makes external Groq requests only after an explicit second opt-in.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASES_PATH = ROOT / "tests" / "event_significance_replay_cases.json"


def load_cases(case_id: str | None = None) -> list[dict]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    assert data["provenance"].startswith("Synthetic")
    cases = data["cases"]
    return [case for case in cases if case_id is None or case["id"] == case_id]


def prompt_for(case: dict) -> str:
    from bot.services.ai_agent_groq import build_event_significance_prompt
    return build_event_significance_prompt(case["input"])


def effort_budget(effort: str) -> int:
    from bot.services.llm.config import effective_max_tokens_for

    env_name = "LLM_EVENT_ANALYSIS_REASONING_EFFORT"
    previous = os.environ.get(env_name)
    try:
        os.environ[env_name] = effort
        return effective_max_tokens_for(
            call_type="event_analysis", provider="groq",
            model="openai/gpt-oss-120b", requested_max_tokens=300,
        )
    finally:
        if previous is None:
            os.environ.pop(env_name, None)
        else:
            os.environ[env_name] = previous


def offline_report(cases: list[dict]) -> dict:
    return {
        "provenance": "SYNTHETIC; no provider requests; no quality measurement",
        "cases": len(cases),
        "symbols": dict(Counter(c["input"]["symbol"] for c in cases)),
        "groups": dict(Counter(c["group"] for c in cases)),
        "expected_positive": sum(c["expected_should_alert"] is True for c in cases),
        "expected_negative": sum(c["expected_should_alert"] is False for c in cases),
        "unadjudicated": sum(c["expected_should_alert"] is None for c in cases),
        "efforts": {
            effort: {
                "max_tokens_requested": effort_budget(effort),
                "decision_metrics": "NOT MEASURED",
            }
            for effort in ("low", "medium")
        },
        "prompt_character_range": [
            min((len(prompt_for(c)) for c in cases), default=0),
            max((len(prompt_for(c)) for c in cases), default=0),
        ],
    }


async def live_report(cases: list[dict], *, delay_seconds: int) -> dict:
    from bot.alerting.event_analysis import validate_event_significance_output
    from bot.services import ai_agent_groq
    from bot.services.llm import config
    from bot.services.llm.groq_provider import GroqProvider

    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY must be set in the process environment")
    provider = GroqProvider()
    response_format, _ = ai_agent_groq._structured_response_formats(
        call_type="event_analysis",
        schema_name="event_significance",
        schema=ai_agent_groq._EVENT_SIGNIFICANCE_JSON_SCHEMA,
    )
    rows = []
    attempted = 0
    for case in cases:
        row = {"case": case["id"], "symbol": case["input"]["symbol"],
               "group": case["group"], "expected": case["expected_should_alert"]}
        messages = [
            {"role": "system", "content": ai_agent_groq.SYSTEM_PROMPT},
            {"role": "user", "content": prompt_for(case)},
        ]
        for effort in ("low", "medium"):
            if attempted:
                await asyncio.sleep(delay_seconds)
            attempted += 1
            os.environ["LLM_EVENT_ANALYSIS_REASONING_EFFORT"] = effort
            budget = config.effective_max_tokens_for(
                call_type="event_analysis", provider="groq",
                model="openai/gpt-oss-120b", requested_max_tokens=300,
            )
            try:
                answer = await provider.chat_completion(
                    call_type="event_analysis", symbol=case["input"]["symbol"],
                    model="openai/gpt-oss-120b", messages=messages,
                    max_tokens=budget, response_format=response_format,
                    reasoning_effort=effort,
                )
                parsed = json.loads(answer.raw_content)
                decision = validate_event_significance_output(
                    parsed, expected_symbol=case["input"]["symbol"]
                )
                row[effort] = {
                    "decision": decision.should_alert,
                    "materiality": decision.materiality,
                    "novelty": decision.novelty,
                    "reason_code": decision.reason_code,
                    "prompt_tokens": answer.prompt_tokens,
                    "completion_tokens": answer.completion_tokens,
                    "total_tokens": answer.total_tokens,
                    "requested_max_tokens": budget,
                    "status": "valid",
                }
            except Exception as exc:
                # Never print provider payloads, prompts, raw LLM output or credentials.
                row[effort] = {"status": "error", "error_type": type(exc).__name__,
                               "requested_max_tokens": budget}
        rows.append(row)

    scores = {}
    for effort in ("low", "medium"):
        adjudicated = [r for r in rows if r["expected"] is not None]
        valid = [r for r in adjudicated if r[effort]["status"] == "valid"]
        observed_tokens = [
            r[effort]["total_tokens"] for r in rows
            if r[effort]["status"] == "valid" and r[effort]["total_tokens"] is not None
        ]
        scores[effort] = {
            "scored": len(valid),
            "failed_or_invalid": len(adjudicated) - len(valid),
            "false_positive": sum(
                r["expected"] is False and r[effort]["decision"] is True
                for r in valid
            ),
            "false_negative": sum(
                r["expected"] is True and r[effort]["decision"] is False
                for r in valid
            ),
            "correct": sum(r["expected"] is r[effort]["decision"] for r in valid),
            "token_usage_measured_calls": len(observed_tokens),
            "actual_total_tokens": sum(observed_tokens) if observed_tokens else None,
        }
    return {"provenance": "SYNTHETIC; live Groq model answers (not production ground truth)",
            "scores": scores, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="Optional single synthetic case ID")
    parser.add_argument("--live", action="store_true", help="Use the external Groq API")
    parser.add_argument("--approve-provider-requests", action="store_true",
                        help="Required explicit opt-in for external API calls")
    parser.add_argument("--delay-seconds", type=int, default=65,
                        help="Pause between live requests to reduce free-tier pressure")
    args = parser.parse_args()
    if args.live and not args.approve_provider_requests:
        parser.error("--live requires --approve-provider-requests")
    if args.delay_seconds < 60:
        parser.error("Delay must be >=60 seconds for conservative free-tier replay")
    cases = load_cases(args.case)
    if not cases:
        parser.error("No matching case")
    if args.live:
        report = asyncio.run(live_report(cases, delay_seconds=args.delay_seconds))
    else:
        report = offline_report(cases)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
