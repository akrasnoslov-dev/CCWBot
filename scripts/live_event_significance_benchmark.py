"""Explicitly approved Groq A/B replay of frozen events (never sends alerts).

Requires --approve-provider-requests; bounded by max 600 calls across this run directory.
Writes only opaque case IDs, response decisions, statuses, usage, and hashes to ignored reports/.
The external Groq provider receives the same sanitized frozen market input as the bot.
This script deliberately avoids bot telemetry/DB state, the LLM router, and fallbacks.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

from bot.alerting.event_analysis import validate_event_significance_output  # noqa: E402
from bot.services import ai_agent_groq  # noqa: E402
from bot.services.llm import config  # noqa: E402
from scripts.event_alert_benchmark import load_frozen  # noqa: E402
from scripts.event_significance_candidates import candidate_prompt  # noqa: E402

VARIANTS = ("production", "materiality_first", "balanced_novelty")
MAX_APPROVED_CALLS = 600


def fingerprint(variant: str, model: str, max_tokens: int, effort: str | None) -> str:
    context = {
        "provider": "groq",
        "model": model,
        "max_tokens": max_tokens,
        "reasoning_effort": effort,
        "temperature": 0.0,
        "system_prompt": ai_agent_groq.SYSTEM_PROMPT,
        "response_format": ai_agent_groq._EVENT_SIGNIFICANCE_JSON_SCHEMA,
        "variant": variant,
        "prompt_instructions": (
            ai_agent_groq._EVENT_SIGNIFICANCE_INSTRUCTIONS
            if variant == "production"
            else candidate_prompt({"symbol": None}, variant).split("\nInput JSON:\n")[0]
        ),
    }
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode("utf-8")).hexdigest()


def ordering(dataset: dict, a_labels: dict) -> list[dict]:
    # Every 3 requests replay the SAME case against all variants. Alternate
    # coin and historic error class to avoid a first-BTC/all-negative pilot.
    symbols = ("BTC", "ETH", "GRAM", "SOL")
    buckets = {}
    for case in dataset["cases"]:
        label = a_labels[case["id"]]
        predicted = case.get("observed", {}).get("should_alert")
        if label == "ambiguous":
            category = "ambiguous"
        elif predicted is True:
            category = "tp" if label == "alert" else "fp"
        else:
            category = "fn" if label == "alert" else "tn"
        buckets.setdefault((case["symbol"], category), []).append(case)
    sequence = []
    for index in range(50):
        for category in ("fp", "fn", "tp", "tn", "ambiguous"):
            for symbol in symbols:
                group = buckets.get((symbol, category), [])
                if index < len(group):
                    sequence.append(group[index])
    return sequence


def load_reviewer_a(path: Path, dataset: dict) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("dataset_sha256") != dataset["dataset_sha256"]:
        raise ValueError("Evaluator A labels do not match frozen input")
    labels = {row["id"]: row["warrant"] for row in record["labels"]}
    if len(labels) != len(dataset["cases"]) or any(
        labels.get(c["id"]) not in ("alert", "no_alert", "ambiguous")
        for c in dataset["cases"]
    ):
        raise ValueError("Incomplete evaluator A reference")
    return labels


def load_state(path: Path, dataset_sha: str, model: str, configs: dict) -> dict:
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if (state.get("dataset_sha256") != dataset_sha or state.get("model") != model
                or state.get("fingerprints") != configs):
            raise ValueError("Replay run configuration mismatch; refuse to mix results")
        return state
    return {
        "dataset_sha256": dataset_sha,
        "model": model,
        "fingerprints": configs,
        "attempted_requests": 0,
        "runs": {v: [] for v in VARIANTS},
    }


def estimated_spent_tokens(state: dict, max_tokens: int) -> int:
    """Account for every request, including uncertain transport/usage outcomes."""
    rows = [row for variant in VARIANTS for row in state["runs"].get(variant, [])]
    observed = sum(
        row["total_tokens"]
        if type(row.get("total_tokens")) is int
        else max_tokens + 2000
        for row in rows
    )
    lost_attempts = max(0, state["attempted_requests"] - len(rows))
    return observed + lost_attempts * (max_tokens + 2000)


def save_state(path: Path, state: dict) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def export_recorded_runs(directory: Path, state: dict) -> None:
    for variant in VARIANTS:
        path = directory / f"recorded_{variant}.json"
        payload = {
            "dataset_sha256": state["dataset_sha256"],
            "run_name": variant,
            "model": state["model"],
            "config_fingerprint": state["fingerprints"][variant],
            "results": [
                {k: value for k, value in row.items() if k not in ("error_type",)}
                for row in state["runs"][variant]
            ],
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


async def replay(
    dataset: dict, a_labels: dict, out: Path, *,
    max_requests: int, delay: float, max_total_tokens: int,
) -> dict:
    load_dotenv(ROOT / ".env")
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing (no requests made)")
    model = config.model_for("groq", "event_analysis")
    effort = config.reasoning_effort_for(model, "event_analysis")
    max_tokens = config.effective_max_tokens_for(
        call_type="event_analysis", provider="groq", model=model,
    )
    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "event_significance",
            "strict": True,
            "schema": ai_agent_groq._EVENT_SIGNIFICANCE_JSON_SCHEMA,
        },
    }
    configs = {v: fingerprint(v, model, max_tokens, effort) for v in VARIANTS}
    out.mkdir(parents=True, exist_ok=True)
    ledger = out / "replay_state.json"
    state = load_state(ledger, dataset["dataset_sha256"], model, configs)
    already = {(variant, item["id"]) for variant, rows in state["runs"].items()
               for item in rows}
    client = AsyncOpenAI(
        api_key=key, base_url=config.base_url("groq"), max_retries=0, timeout=30,
    )
    issued = 0
    stopped_reason = "requested_limit"
    try:
        for case in ordering(dataset, a_labels):
            for variant in VARIANTS:
                if (variant, case["id"]) in already:
                    continue
                if issued >= max_requests:
                    break
                if state["attempted_requests"] >= MAX_APPROVED_CALLS:
                    stopped_reason = "approved_request_ceiling"
                    break
                if estimated_spent_tokens(state, max_tokens) + max_tokens + 2000 > max_total_tokens:
                    stopped_reason = "replay_token_safety_limit"
                    break
                if issued:
                    await asyncio.sleep(delay)
                messages = [
                    {"role": "system", "content": ai_agent_groq.SYSTEM_PROMPT},
                    {"role": "user", "content": candidate_prompt(case["input"], variant)},
                ]
                result = {"id": case["id"], "input_sha256": case["input_sha256"]}
                # Increment and persist before HTTP; ambiguous transport outcomes count.
                state["attempted_requests"] += 1
                issued += 1
                save_state(ledger, state)
                try:
                    opts = {
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.0,
                        "response_format": schema,
                        "timeout": 30,
                    }
                    if effort is not None:
                        opts["reasoning_effort"] = effort
                    raw = await client.chat.completions.with_raw_response.create(**opts)
                    answer = raw.parse()
                    result["provider_attempts"] = 1
                    usage = answer.usage
                    if usage is not None:
                        if usage.total_tokens is not None:
                            result["total_tokens"] = int(usage.total_tokens)
                        if usage.prompt_tokens is not None:
                            result["prompt_tokens"] = int(usage.prompt_tokens)
                        if usage.completion_tokens is not None:
                            result["completion_tokens"] = int(usage.completion_tokens)
                    content = answer.choices[0].message.content
                    try:
                        parsed = json.loads(content or "")
                        valid = validate_event_significance_output(
                            parsed, expected_symbol=case["symbol"],
                        )
                        result["status"] = "valid"
                        result["should_alert"] = valid.should_alert
                        result["materiality"] = valid.materiality
                        result["novelty"] = valid.novelty
                        result["reason_code"] = valid.reason_code
                    except json.JSONDecodeError:
                        result["status"] = "invalid_json"
                    except Exception as exc:
                        result["status"] = "schema_error"
                        result["error_type"] = type(exc).__name__
                except Exception as exc:
                    result["status"] = "provider_error"
                    result["error_type"] = type(exc).__name__
                    result["provider_attempts"] = 1
                    http_status = getattr(exc, "status_code", None)
                    if http_status is not None:
                        result["http_status"] = int(http_status)
                    if http_status in (401, 402, 403, 404, 429):
                        stopped_reason = f"provider_http_{http_status}"
                state["runs"][variant].append(result)
                save_state(ledger, state)
                export_recorded_runs(out, state)
                n = state["attempted_requests"]
                counts = {v: Counter(x["status"] for x in state["runs"][v])
                          for v in VARIANTS}
                print(
                    f"request={n}/{MAX_APPROVED_CALLS} variant={variant} "
                    f"symbol={case['symbol']} status={result['status']} "
                    f"tokens={result.get('total_tokens', 'unknown')} "
                    f"valid_counts={[(v, counts[v]['valid']) for v in VARIANTS]}",
                    flush=True,
                )
                if stopped_reason.startswith("provider_http_"):
                    break
            if issued >= max_requests or stopped_reason != "requested_limit":
                break
    finally:
        await client.close()
        export_recorded_runs(out, state)
    return {
        "attempts_this_invocation": issued,
        "attempts_total": state["attempted_requests"],
        "stop": stopped_reason,
        "variant_statuses": {
            name: dict(Counter(row["status"] for row in rows))
            for name, rows in state["runs"].items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--approve-provider-requests", action="store_true")
    parser.add_argument("--max-requests", type=int, default=12)
    parser.add_argument("--delay-seconds", type=float, default=12)
    parser.add_argument("--max-total-tokens", type=int, default=125000)
    args = parser.parse_args()
    if not args.approve_provider_requests:
        parser.error("Groq replay requires explicit --approve-provider-requests")
    if args.max_requests < 1 or args.max_requests > MAX_APPROVED_CALLS:
        parser.error("Maximum approved Groq API calls is 600")
    if args.delay_seconds < 0:
        parser.error("Delay must be nonnegative")
    if args.max_total_tokens < 1:
        parser.error("Total replay token safety limit must be positive")
    dataset = load_frozen(args.benchmark)
    a_labels = load_reviewer_a(args.reviewer_a, dataset)
    print(json.dumps(asyncio.run(
        replay(
            dataset, a_labels, args.out,
            max_requests=args.max_requests, delay=args.delay_seconds,
            max_total_tokens=args.max_total_tokens,
        )
    ), indent=2))


if __name__ == "__main__":
    main()
