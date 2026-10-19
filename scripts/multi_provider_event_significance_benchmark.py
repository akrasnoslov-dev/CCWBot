"""Isolated, resumable free-tier significance checks on configured fallback LLMs.

Reads only the frozen sanitized market input; sends no alerts. The reviewer labels
NEVER leave this machine. Each provider/model is scored separately.
No automatic retry of 429/4xx; observed Retry-After is enforced on subsequent runs.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
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
from scripts.live_event_significance_benchmark import (  # noqa: E402
    VARIANTS,
    eligible_replay_cases,
    load_reviewer_a,
    maximum_possible_quality,
    save_state,
)

PRIVATE = ROOT / "reports" / "event-alert-review-20261016"
VARIANT = "path_facts"
PROVIDERS = ("gemini", "cloudflare")


def response_format(provider: str, model: str) -> dict:
    schema = ai_agent_groq._EVENT_SIGNIFICANCE_JSON_SCHEMA
    if provider == "cloudflare" and model == "@cf/meta/llama-3.3-70b-instruct-fp8-fast":
        return {"type": "json_schema", "json_schema": schema}
    return {"type": "json_object"}


def configuration(provider: str, model_override: str | None = None) -> dict:
    load_dotenv(ROOT / ".env")
    model = model_override or config.model_for(provider, "event_analysis")
    effort = config.reasoning_effort_for(model, "event_analysis")
    return {
        "provider": provider, "model": model,
        "max_tokens": config.effective_max_tokens_for(
            call_type="event_analysis", provider=provider, model=model
        ),
        "reasoning_effort": effort,
        "format": response_format(provider, model),
    }


def new_state(dataset: dict, cfg: dict, variant: str = VARIANT) -> dict:
    fingerprint = hashlib.sha256(json.dumps({
        **cfg, "prompt": candidate_prompt({"symbol": None}, variant).split("\nInput JSON:\n")[0],
        "system": ai_agent_groq.SYSTEM_PROMPT,
    }, sort_keys=True).encode()).hexdigest()
    return {"dataset_sha256": dataset["dataset_sha256"], "fingerprint": fingerprint,
            "provider": cfg["provider"], "model": cfg["model"],
            "attempted_requests": 0, "runs": {variant: []}}


def retry_seconds(row: dict) -> float | None:
    if row.get("status") != "provider_error":
        return None
    status = row.get("http_status")
    if status == 429:
        return max(60.0, float(row.get("retry_after_seconds", 3600)))
    if status in (500, 502, 503, 504):
        return 120.0
    if status is None:
        return 300.0
    return None


def eligible_again(row: dict, now: datetime) -> bool:
    seconds = retry_seconds(row)
    observed = row.get("error_at_utc")
    # An initial exploratory probe predates timestamp recording. Retry that
    # transient provider failure once; all later errors carry an exact timestamp.
    if seconds is not None and not observed and row.get("http_status") in (500, 502, 503, 504):
        return True
    if seconds is None or not observed:
        return False
    try:
        return now >= datetime.fromisoformat(observed) + __import__("datetime").timedelta(
            seconds=seconds
        )
    except (ValueError, TypeError):
        return False


async def run(provider: str, *, max_requests: int, delay: float,
              variant: str = VARIANT, model_override: str | None = None,
              stop_on_impossible_gates: bool = True) -> dict:
    cfg = configuration(provider, model_override)
    key = config.api_key(provider)
    base = config.base_url(provider)
    if not key or not base:
        return {"provider": provider, "status": "credentials_or_endpoint_missing"}
    dataset = load_frozen(PRIVATE / "v2_private_sanitized.json")
    labels = load_reviewer_a(PRIVATE / "reviewer_A_significance_for_pr1.json", dataset)
    suffix = ("_" + cfg["model"].replace("/", "_").replace("@", "")) if model_override else ""
    directory = (
        PRIVATE / "merged_pilots_private"
        / ("fallback_" + provider + "_" + variant + suffix)
    )
    directory.mkdir(parents=True, exist_ok=True)
    state_path = directory / "replay_state.json"
    expected = new_state(dataset, cfg, variant)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else expected
    for key_name in ("dataset_sha256", "fingerprint", "provider", "model"):
        if state[key_name] != expected[key_name]:
            raise ValueError(f"{provider}: frozen input / configuration changed")
    already = {r["id"]: r for r in state["runs"][variant]}
    now = datetime.now(timezone.utc)
    for past in state["runs"][variant]:
        wait = retry_seconds(past)
        if wait is not None and past.get("error_at_utc"):
            elapsed = (now - datetime.fromisoformat(past["error_at_utc"])).total_seconds()
            if elapsed < wait:
                return {"provider": provider, "stop": "provider_backoff",
                        "retry_after_seconds": round(wait - elapsed),
                        "attempted_requests": state["attempted_requests"]}
    # Mixed chronological/asset/error-class ordering checks false positives
    # promptly; positive-only prefixes conceal an always-alert model.
    rows = eligible_replay_cases(dataset, labels, excluded_case_ids=frozenset(),
                                 skip_ambiguous=True, screen_positives_first=False)
    now = datetime.now(timezone.utc)
    total = 0
    stop = "requested_limit"
    client = AsyncOpenAI(api_key=key, base_url=base, max_retries=0, timeout=30)
    try:
        for case in rows:
            prior = already.get(case["id"])
            if prior is not None and not eligible_again(prior, now):
                continue
            if stop_on_impossible_gates and not maximum_possible_quality(
                    dataset, labels, state, variant)["can_meet_target"]:
                stop = "candidate_cannot_meet_quality_gates"
                break
            if total >= max_requests:
                break
            if total:
                await asyncio.sleep(delay)
            item = {"id": case["id"], "input_sha256": case["input_sha256"]}
            state["attempted_requests"] += 1
            total += 1
            save_state(state_path, state)
            opts = {
                "model": cfg["model"],
                "messages": [
                    {"role": "system", "content": ai_agent_groq.SYSTEM_PROMPT},
                    {"role": "user", "content": candidate_prompt(case["input"], variant)},
                ],
                "max_tokens": cfg["max_tokens"],
                "response_format": cfg["format"],
                "timeout": 30,
            }
            if provider == "cloudflare":
                opts["temperature"] = 0.0
            if cfg["reasoning_effort"]:
                opts["reasoning_effort"] = cfg["reasoning_effort"]
            try:
                answer = await client.chat.completions.create(**opts)
                if answer.usage is not None:
                    for api_field, field in (("total_tokens", "total_tokens"),
                                             ("prompt_tokens", "prompt_tokens"),
                                             ("completion_tokens", "completion_tokens")):
                        value = getattr(answer.usage, api_field, None)
                        if isinstance(value, int):
                            item[field] = value
                content = (answer.choices[0].message.content or "").strip()
                try:
                    parsed = ai_agent_groq._parse_json(content)
                    if parsed is None:
                        item["status"] = "invalid_json"
                    else:
                        valid = validate_event_significance_output(
                            parsed, expected_symbol=case["symbol"])
                        item.update(status="valid", should_alert=valid.should_alert,
                                    materiality=valid.materiality, novelty=valid.novelty,
                                    reason_code=valid.reason_code)
                except Exception as exc:
                    item.update(status="schema_error", error_type=type(exc).__name__)
            except Exception as exc:
                http = getattr(exc, "status_code", None)
                item.update(status="provider_error", error_type=type(exc).__name__,
                            error_at_utc=datetime.now(timezone.utc).isoformat())
                if isinstance(http, int):
                    item["http_status"] = http
                if http == 429:
                    item["rate_limit_at_utc"] = datetime.now(timezone.utc).isoformat()
                    headers = getattr(getattr(exc, "response", None), "headers", None)
                    raw = headers.get("retry-after") if headers else None
                    try:
                        if raw is not None and 0 <= float(raw) <= 86400:
                            item["retry_after_seconds"] = float(raw)
                    except (TypeError, ValueError):
                        pass
                stop = "provider_http_" + str(http)
            if prior is not None:
                state["runs"][variant][state["runs"][variant].index(prior)] = item
            else:
                state["runs"][variant].append(item)
            already[case["id"]] = item
            save_state(state_path, state)
            counts = Counter(r["status"] for r in state["runs"][variant])
            print(json.dumps({"provider": provider, "request": state["attempted_requests"],
                              "symbol": case["symbol"], "status": item["status"],
                              "http_status": item.get("http_status"),
                              "tokens": item.get("total_tokens"),
                              "valid": counts["valid"]}), flush=True)
            if stop != "requested_limit":
                break
    finally:
        await client.close()
    quality = maximum_possible_quality(dataset, labels, state, variant)
    return {"provider": provider, "model": cfg["model"],
            "attempted_requests": state["attempted_requests"], "requests_this_run": total,
            "valid": sum(r["status"] == "valid" for r in state["runs"][variant]),
            "stop": stop, "best_possible": quality}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=PROVIDERS, required=True)
    parser.add_argument("--variant", choices=VARIANTS, default=VARIANT)
    parser.add_argument("--model-override", default=None)
    parser.add_argument("--max-requests", type=int, default=4)
    parser.add_argument("--delay-seconds", type=float, default=15)
    parser.add_argument("--approve-provider-requests", action="store_true")
    args = parser.parse_args()
    if not args.approve_provider_requests:
        parser.error("External provider calls require explicit approval")
    if not 1 <= args.max_requests <= 153 or args.delay_seconds < 0:
        parser.error("Invalid request count or delay")
    print(json.dumps(asyncio.run(run(args.provider, max_requests=args.max_requests,
                                     delay=args.delay_seconds, variant=args.variant,
                                     model_override=args.model_override)), sort_keys=True))


if __name__ == "__main__":
    main()
