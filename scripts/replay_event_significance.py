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
REAL_CASES_PATH = ROOT / "tests" / "fixtures" / "event_alert_benchmark" / "v1.json"


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


def groq_significance_response_format() -> dict | None:
    """Match strict-schema production for the replay's *pinned* GPT-OSS model."""
    from bot.services import ai_agent_groq

    if not ai_agent_groq._groq_json_mode_enabled():
        return None
    # The replay pins GPT-OSS 120B independently of production env overrides.
    # Do not derive its format from an unrelated configured provider chain.
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "event_significance",
            "strict": True,
            "schema": ai_agent_groq._EVENT_SIGNIFICANCE_JSON_SCHEMA,
        },
    }


class NonObjectSignificanceError(ValueError):
    """Provider returned valid JSON, but not the required object structure."""


def parse_significance_response(raw_content: str) -> dict:
    """Malformed or non-object JSON is unusable output, not a provider outage."""
    result = json.loads(raw_content)
    if not isinstance(result, dict):
        raise NonObjectSignificanceError("event significance output must be a JSON object")
    return result


def classify_replay_error(error: Exception) -> str:
    """Never report pre-answer SDK errors as invalid model output."""
    if isinstance(error, json.JSONDecodeError):
        return "invalid_json"
    if isinstance(error, NonObjectSignificanceError) or type(error).__name__ in {
        "EventAnalysisValidationError", "AISchemaValidationError", "AIInvalidJsonError",
    }:
        return "schema_error"
    return "provider_error"


def summarize_rows(rows: list[dict]) -> dict:
    """Score only adjudicated, validated model answers; never count failures as no-alert."""
    scores = {}
    for effort in ("low", "medium"):
        adjudicated = [r for r in rows if r["expected"] is not None]
        valid = [r for r in adjudicated if r[effort]["status"] == "valid"]
        positives = [r for r in valid if r["expected"] is True]
        negatives = [r for r in valid if r["expected"] is False]
        all_valid = [r for r in rows if r[effort]["status"] == "valid"]
        tokens = [r[effort] for r in rows]  # Include billed invalid responses.
        observed = [r for r in tokens if r.get("total_tokens") is not None]
        fp = sum(r[effort]["decision"] is True for r in negatives)
        fn = sum(r[effort]["decision"] is False for r in positives)
        tp = len(positives) - fn
        tn = len(negatives) - fp
        scores[effort] = {
            "adjudicated": len(adjudicated),
            "scored": len(valid),
            "failed_or_invalid": len(adjudicated) - len(valid),
            "schema_valid_calls": len(all_valid),
            "schema_invalid_calls": sum(
                r[effort]["status"] in {"schema_error", "invalid_json"} for r in rows
            ),
            "provider_error_calls": sum(
                r[effort]["status"] == "provider_error" for r in rows
            ),
            "true_positive": tp,
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
            "positive_recall": tp / len(positives) if positives else None,
            "negative_specificity": tn / len(negatives) if negatives else None,
            "accuracy_valid_adjudicated": (tp + tn) / len(valid) if valid else None,
            "token_usage_measured_calls": len(observed),
            "actual_total_tokens": sum(r["total_tokens"] for r in observed) if observed else None,
            "actual_prompt_tokens": sum(
                r["prompt_tokens"] for r in tokens if r.get("prompt_tokens") is not None
            ) if any(r.get("prompt_tokens") is not None for r in tokens) else None,
            "actual_completion_tokens": sum(
                r["completion_tokens"] for r in tokens
                if r.get("completion_tokens") is not None
            ) if any(r.get("completion_tokens") is not None for r in tokens) else None,
            "mean_total_tokens": (
                sum(r["total_tokens"] for r in observed) / len(observed) if observed else None
            ),
        }
    paired = [
        r for r in rows
        if r["low"]["status"] == "valid" and r["medium"]["status"] == "valid"
    ]
    return {
        "scores": scores,
        "paired_valid_cases": len(paired),
        "paired_decision_disagreements": sum(
            r["low"]["decision"] != r["medium"]["decision"] for r in paired
        ),
        "unadjudicated_case_ids": [r["case"] for r in rows if r["expected"] is None],
    }


async def live_report(cases: list[dict], *, delay_seconds: int) -> dict:
    from bot.alerting.event_analysis import validate_event_significance_output
    from bot.services import ai_agent_groq
    from bot.services.llm import config
    from bot.services.llm.groq_provider import GroqProvider

    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY must be set in the process environment")
    provider = GroqProvider()
    response_format = groq_significance_response_format()
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
            answer = None
            try:
                answer = await provider.chat_completion(
                    call_type="event_analysis", symbol=case["input"]["symbol"],
                    model="openai/gpt-oss-120b", messages=messages,
                    max_tokens=budget, response_format=response_format,
                    reasoning_effort=effort,
                )
                parsed = parse_significance_response(answer.raw_content)
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
                error_type = type(exc).__name__
                status = classify_replay_error(exc)
                failed_answer = {
                    "status": status, "error_type": error_type,
                    "requested_max_tokens": budget,
                }
                # Provider answered and billed tokens even if validation failed.
                if answer is not None:
                    failed_answer.update({
                        "prompt_tokens": answer.prompt_tokens,
                        "completion_tokens": answer.completion_tokens,
                        "total_tokens": answer.total_tokens,
                    })
                row[effort] = failed_answer
        rows.append(row)

    report = summarize_rows(rows)
    return {
        "provenance": "SYNTHETIC; live Groq model answers (not production ground truth)",
        **report,
        "rows": rows,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="Optional single synthetic case ID")
    parser.add_argument("--live", action="store_true", help="Use the external Groq API")
    parser.add_argument("--approve-provider-requests", action="store_true",
                        help="Required explicit opt-in for external API calls")
    parser.add_argument("--delay-seconds", type=int, default=65,
                        help="Pause between live requests to reduce free-tier pressure")
    parser.add_argument(
        "--benchmark", nargs="?", const=str(REAL_CASES_PATH),
        help="Score frozen real-market evidence; defaults to the versioned v1 manifest",
    )
    parser.add_argument("--blind-export", help="Export decision-blind evaluator packet JSON")
    parser.add_argument(
        "--review-phase", choices=("significance", "message"), default="significance"
    )
    parser.add_argument("--evaluator-one", help="First independent human labels JSON")
    parser.add_argument("--evaluator-two", help="Second independent human labels JSON")
    parser.add_argument("--reconciled", help="Explicit adjudicator labels for disagreements")
    parser.add_argument(
        "--recorded-run", help="Pinned candidate results JSON; never calls provider"
    )
    args = parser.parse_args()
    if args.benchmark is not None:
        if args.live or args.approve_provider_requests or args.case:
            parser.error("Frozen benchmark mode is offline and separate from synthetic live replay")
        from scripts.event_alert_benchmark import (
            blind_packet,
            compare_recorded_run,
            load_frozen,
            reconcile,
            report,
        )

        dataset = load_frozen(args.benchmark)
        if args.blind_export:
            packet = blind_packet(dataset, args.review_phase)
            Path(args.blind_export).write_text(
                json.dumps(packet, indent=2, sort_keys=True) + "\\n", encoding="utf-8"
            )
            print(json.dumps({
                "dataset_sha256": dataset["dataset_sha256"],
                "phase": args.review_phase,
                "exported_cases": len(packet["cases"]),
            }, indent=2))
            return
        labels, agreement = reconcile(
            dataset, args.evaluator_one, args.evaluator_two, args.reconciled,
        )
        result = (
            compare_recorded_run(dataset, args.recorded_run, labels, agreement)
            if args.recorded_run else report(dataset, labels, agreement)
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return
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
