"""Explicitly approved Groq A/B replay of frozen events (never sends alerts).

Requires --approve-provider-requests; uses a technical 5000-attempt safety ceiling.
Provider rate limits and local token budgets govern actual allowed volume.
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
import re
import sys
from collections import Counter
from datetime import datetime, timezone
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

VARIANTS = (
    "production", "materiality_first", "balanced_novelty",
    "trajectory_evidence", "relative_displacement", "rebalanced_core",
    "global_prior_safe", "global_prior_no_family", "path_facts",
    "market_signal_path", "market_event_evidence", "contextual_materiality",
)
DEFAULT_VARIANTS = ("production", "materiality_first", "balanced_novelty")
MAX_APPROVED_CALLS = 5_000  # Technical safety ceiling, not an approval quota.


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
    if variant == "global_prior_no_family":
        context["model_input_view"] = "omit_global_prev_family_v1"
    if variant == "path_facts":
        context["model_input_view"] = "verified_sampled_path_v1"
    if variant == "market_signal_path":
        context["model_input_view"] = "sampled_path_no_global_prior_or_counts_v1"
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


def eligible_replay_cases(
    dataset: dict,
    labels: dict,
    *,
    excluded_case_ids: frozenset[str],
    skip_ambiguous: bool,
    screen_positives_first: bool = False,
) -> list[dict]:
    cases = [
        case for case in ordering(dataset, labels)
        if case["id"] not in excluded_case_ids
        and not (skip_ambiguous and labels[case["id"]] == "ambiguous")
    ]
    if screen_positives_first:
        # Screening only. The score still uses real, full-cohort reference
        # labels; a positive-only prefix is never an unbiased precision test.
        cases.sort(key=lambda case: labels[case["id"]] != "alert")
    return cases


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


def load_state(
    path: Path, dataset_sha: str, model: str, configs: dict,
    *, refresh_unused_config: bool = False,
) -> dict:
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if (
            state.get("dataset_sha256") != dataset_sha
            or state.get("model") != model
        ):
            raise ValueError("Replay run configuration mismatch; refuse to mix results")
        # Existing recorded answers always pin their exact configuration.
        # Explicitly refreshing an unused candidate is safe only when it has
        # zero provider responses; never rewrite a measured variant fingerprint.
        for name, old_fingerprint in state.get("fingerprints", {}).items():
            if configs.get(name) == old_fingerprint:
                continue
            if (
                not refresh_unused_config
                or name not in configs
                or state["runs"].get(name)
            ):
                raise ValueError("Replay run configuration mismatch; refuse to mix results")
            state["fingerprints"][name] = configs[name]
        for name, value in configs.items():
            state["fingerprints"].setdefault(name, value)
            state["runs"].setdefault(name, [])
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


def maximum_possible_quality(
    dataset: dict, labels: dict, state: dict, variant: str,
) -> dict:
    """Mathematical best case for the *complete* decisive frozen reference.

    Treat provider errors and untested cases as unknown, never no-alert.
    """
    truth = {case["id"]: labels[case["id"]] for case in dataset["cases"]}
    positive_total = sum(label == "alert" for label in truth.values())
    false_negative = 0
    false_positive = 0
    for row in state["runs"].get(variant, []):
        if row.get("status") != "valid" or truth.get(row["id"]) == "ambiguous":
            continue
        actual = truth[row["id"]]
        if actual == "alert" and row["should_alert"] is False:
            false_negative += 1
        elif actual == "no_alert" and row["should_alert"] is True:
            false_positive += 1
    max_tp = positive_total - false_negative
    max_precision = max_tp / (max_tp + false_positive) if max_tp + false_positive else None
    max_recall = max_tp / positive_total if positive_total else None
    return {
        "false_negative": false_negative,
        "false_positive": false_positive,
        "max_precision": max_precision,
        "max_recall": max_recall,
        "can_meet_target": (
            max_precision is not None and max_precision >= 0.85
            and max_recall is not None and max_recall >= 0.90
        ),
    }


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


def classified_rate_limit_dimension(exc: Exception) -> str | None:
    """Classify the 429 body without ever persisting raw messages or organization IDs."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        detail = body.get("error", body)
        message = detail.get("message", "") if isinstance(detail, dict) else ""
    else:
        message = ""
    if not isinstance(message, str):
        return None
    patterns = (
        ("output_tokens_per_minute", r"\b(?:OTPM|output tokens per minute)\b"),
        ("input_tokens_per_minute", r"\b(?:ITPM|input tokens per minute)\b"),
        ("tokens_per_day", r"\b(?:TPD|tokens per day)\b"),
        ("tokens_per_minute", r"\b(?:TPM|tokens per minute)\b"),
        ("requests_per_day", r"\b(?:RPD|requests per day)\b"),
        ("requests_per_minute", r"\b(?:RPM|requests per minute)\b"),
    )
    for dimension, pattern in patterns:
        if re.search(pattern, message, flags=re.IGNORECASE):
            return dimension
    return None


def numeric_rate_limit_headers(headers: object) -> dict:
    """Only allowlisted quota counters; never store arbitrary provider headers."""
    if headers is None or not hasattr(headers, "get"):
        return {}
    mapping = {
        "x-ratelimit-limit-requests": "rate_limit_daily_requests",
        "x-ratelimit-remaining-requests": "rate_limit_remaining_requests",
        "x-ratelimit-limit-tokens": "rate_limit_minute_tokens",
        "x-ratelimit-remaining-tokens": "rate_limit_remaining_tokens",
    }
    counters = {}
    for http_name, field_name in mapping.items():
        raw = headers.get(http_name)
        if raw is None:
            continue
        value = str(raw).strip()
        if value.isascii() and value.isdecimal() and len(value) <= 12:
            counters[field_name] = int(value)
    return counters


def remaining_rate_limit_backoff(
    state: dict, *, now: datetime | None = None,
) -> float:
    """Wait for the strictest recorded HTTP 429 backoff before any provider call."""
    current = now or datetime.now(timezone.utc)
    remaining = 0.0
    for rows in state["runs"].values():
        for row in rows:
            if row.get("http_status") != 429:
                continue
            when = row.get("rate_limit_at_utc")
            interval = row.get("retry_after_seconds")
            if not when or not isinstance(interval, (int, float)) or interval < 0:
                continue
            try:
                observed = datetime.fromisoformat(when)
            except (TypeError, ValueError):
                continue
            if observed.tzinfo is None:
                continue
            remaining = max(remaining, (observed - current).total_seconds() + interval)
    return max(0.0, remaining)


def can_retry_rate_limit(row: dict | None, *, approved: bool) -> bool:
    """Only an explicitly approved retry of HTTP 429 may replace a recorded row."""
    return bool(
        approved and row is not None and row.get("status") == "provider_error"
        and row.get("http_status") == 429
    )


def record_replay_result(
    state: dict, variant: str, result: dict, *, retrying: bool,
) -> None:
    """Keep one scored row per case while preserving ALL provider attempts in the counter."""
    rows = state["runs"][variant]
    matches = [i for i, row in enumerate(rows) if row["id"] == result["id"]]
    if retrying:
        if len(matches) != 1 or not can_retry_rate_limit(rows[matches[0]], approved=True):
            raise ValueError("Only a recorded rate-limit failure can be retried")
        if rows[matches[0]]["input_sha256"] != result["input_sha256"]:
            raise ValueError("Retry must preserve frozen input")
        rows[matches[0]] = result
    elif matches:
        raise ValueError("Duplicate scored response")
    else:
        rows.append(result)


async def replay(
    dataset: dict, a_labels: dict, out: Path, *,
    max_requests: int, delay: float, max_total_tokens: int,
    selected_variants: tuple[str, ...] = DEFAULT_VARIANTS,
    skip_ambiguous: bool = False,
    excluded_case_ids: frozenset[str] = frozenset(),
    previous_attempts: int = 0,
    retry_rate_limited: bool = False,
    refresh_unused_config: bool = False,
    stop_on_impossible_gates: bool = False,
    screen_positives_first: bool = False,
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
    state = load_state(
        ledger, dataset["dataset_sha256"], model, configs,
        refresh_unused_config=refresh_unused_config,
    )
    backoff_remaining = remaining_rate_limit_backoff(state)
    if backoff_remaining > 0:
        return {
            "attempts_this_invocation": 0,
            "attempts_total": state["attempted_requests"],
            "stop": "recorded_provider_http_429_backoff",
            "retry_after_seconds": round(backoff_remaining),
            "variant_statuses": {
                name: dict(Counter(row["status"] for row in rows))
                for name, rows in state["runs"].items()
            },
        }
    already = {(variant, item["id"]): item for variant, rows in state["runs"].items()
               for item in rows}
    client = AsyncOpenAI(
        api_key=key, base_url=config.base_url("groq"), max_retries=0, timeout=30,
    )
    issued = 0
    stopped_reason = "requested_limit"
    try:
        for case in eligible_replay_cases(
            dataset, a_labels,
            excluded_case_ids=excluded_case_ids, skip_ambiguous=skip_ambiguous,
            screen_positives_first=screen_positives_first,
        ):
            for variant in selected_variants:
                retrying = can_retry_rate_limit(
                    already.get((variant, case["id"])), approved=retry_rate_limited,
                )
                if (variant, case["id"]) in already and not retrying:
                    continue
                if (
                    stop_on_impossible_gates
                    and variant != "production"
                    and not maximum_possible_quality(
                        dataset, a_labels, state, variant,
                    )["can_meet_target"]
                ):
                    stopped_reason = "candidate_cannot_reach_quality_gates"
                    break
                if issued >= max_requests:
                    break
                if previous_attempts + state["attempted_requests"] >= MAX_APPROVED_CALLS:
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
                    if http_status == 429:
                        result["rate_limit_at_utc"] = datetime.now(timezone.utc).isoformat()
                        headers = getattr(getattr(exc, "response", None), "headers", None)
                        result.update(numeric_rate_limit_headers(headers))
                        dimension = classified_rate_limit_dimension(exc)
                        if dimension:
                            result["rate_limit_dimension"] = dimension
                        retry_after = headers.get("retry-after") if headers else None
                        try:
                            if retry_after is not None:
                                value = float(retry_after)
                                if 0 <= value <= 86400:
                                    result["retry_after_seconds"] = value
                        except (TypeError, ValueError):
                            pass
                    if http_status in (401, 402, 403, 404, 429):
                        stopped_reason = f"provider_http_{http_status}"
                record_replay_result(state, variant, result, retrying=retrying)
                save_state(ledger, state)
                export_recorded_runs(out, state)
                n = state["attempted_requests"]
                counts = {v: Counter(x["status"] for x in state["runs"][v])
                          for v in VARIANTS}
                print(
                    f"request={previous_attempts + n}/{MAX_APPROVED_CALLS} variant={variant} "
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
    parser.add_argument("--variants", nargs="+", choices=VARIANTS, default=DEFAULT_VARIANTS)
    parser.add_argument("--skip-ambiguous", action="store_true")
    parser.add_argument("--exclude-state", type=Path)
    parser.add_argument("--retry-rate-limited", action="store_true")
    parser.add_argument("--refresh-unused-candidate-config", action="store_true")
    parser.add_argument("--stop-on-impossible-gates", action="store_true")
    parser.add_argument("--screen-positives-first", action="store_true")
    args = parser.parse_args()
    if not args.approve_provider_requests:
        parser.error("Groq replay requires explicit --approve-provider-requests")
    if args.max_requests < 1 or args.max_requests > MAX_APPROVED_CALLS:
        parser.error("Maximum request count exceeds technical replay safety ceiling")
    if args.delay_seconds < 0:
        parser.error("Delay must be nonnegative")
    if args.max_total_tokens < 1:
        parser.error("Total replay token safety limit must be positive")
    dataset = load_frozen(args.benchmark)
    a_labels = load_reviewer_a(args.reviewer_a, dataset)
    excluded = frozenset()
    previous_attempts = 0
    if args.exclude_state:
        prior = json.loads(args.exclude_state.read_text(encoding="utf-8"))
        if prior["dataset_sha256"] != dataset["dataset_sha256"]:
            parser.error("Prior replay has a different frozen dataset")
        excluded = frozenset(
            row["id"] for entries in prior["runs"].values() for row in entries
        )
        previous_attempts = int(prior["attempted_requests"])
    print(json.dumps(asyncio.run(
        replay(
            dataset, a_labels, args.out,
            max_requests=args.max_requests, delay=args.delay_seconds,
            max_total_tokens=args.max_total_tokens,
            selected_variants=tuple(dict.fromkeys(args.variants)),
            skip_ambiguous=args.skip_ambiguous,
            excluded_case_ids=excluded,
            previous_attempts=previous_attempts,
            retry_rate_limited=args.retry_rate_limited,
            refresh_unused_config=args.refresh_unused_candidate_config,
            stop_on_impossible_gates=args.stop_on_impossible_gates,
            screen_positives_first=args.screen_positives_first,
        )
    ), indent=2))


if __name__ == "__main__":
    main()
