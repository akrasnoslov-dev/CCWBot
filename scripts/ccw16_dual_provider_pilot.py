"""CCW-16 bounded, opt-in Groq/Cloudflare Event Analysis replay.

Offline prepare/score by default. Never loads .env, touches production DB,
falls back between providers, or sends Telegram messages. Private inputs/ledger
must stay outside version control in an access-controlled workspace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from bot.alerting.event_analysis import validate_event_significance_output
from bot.services.ai_agent_groq import (
    _EVENT_SIGNIFICANCE_JSON_SCHEMA,
    SYSTEM_PROMPT,
)
from scripts.ccw15_prompt_pack import (
    FROZEN_DATASET_SHA256,
    PROMPTS,
    build_prompt,
    inspect_private_frozen,
)
from scripts.event_alert_benchmark import _read_evaluations, digest, load_frozen

SYMBOLS = ("BTC", "ETH", "GRAM", "SOL")
SCHEMA = _EVENT_SIGNIFICANCE_JSON_SCHEMA
MODELS = {
    "groq": "openai/gpt-oss-120b",
    "cloudflare": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
}
REQUIRED_ATTESTATIONS = (
    "CCW16_ISOLATION_VERIFIED",
    "CCW16_GROQ_SPARE_QUOTA_VERIFIED",
    "CCW16_CLOUDFLARE_SPARE_QUOTA_VERIFIED",
    "CCW16_FREE_TIER_VERIFIED",
)
MAX_ATTEMPTS = 120  # includes errors/crashed reservations
MAX_DAILY = {"groq": 20_000, "cloudflare": 1_000}
CLOUDFLARE_NEURON_RESERVE = 250
MIN_INTERVAL_SECONDS = 90
PROVIDER_KEYS = {"groq": "GROQ_API_KEY", "cloudflare": "CLOUDFLARE_API_TOKEN"}


def select_cases(dataset: dict, labels: dict) -> list[dict]:
    """Deterministic 5 per symbol: 2 alert, 2 no_alert, 1 ambiguous."""
    chosen = []
    for symbol in SYMBOLS:
        for warrant, count in (("alert", 2), ("no_alert", 2), ("ambiguous", 1)):
            pool = [
                case for case in dataset["cases"]
                if case["symbol"] == symbol
                and labels[case["id"]]["warrant"] == warrant
            ]
            if len(pool) < count:
                raise ValueError("Insufficient frozen cases in sampling stratum")
            pool.sort(key=lambda c: hashlib.sha256(
                ("ccw16-v1:" + c["id"]).encode("ascii")
            ).hexdigest())
            chosen.extend(pool[:count])
    if len(chosen) != 20 or len({x["id"] for x in chosen}) != 20:
        raise ValueError("Invalid prespecified pilot sample")
    return chosen


def work_items(cases: list[dict]) -> list[dict]:
    return [
        {"id": case["id"], "symbol": case["symbol"],
         "input_sha256": case["input_sha256"], "prompt": name,
         "provider": provider}
        for case in cases
        for name in PROMPTS
        for provider in MODELS
    ]


def request_body(provider: str, input_payload: dict, prompt: str) -> dict:
    if provider not in MODELS:
        raise ValueError("Unsupported provider")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    if provider == "groq":
        return {
            "model": MODELS[provider],
            "messages": messages,
            "reasoning_effort": "medium",
            "max_tokens": 6300,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "event_significance", "strict": True, "schema": SCHEMA,
                },
            },
        }
    return {
        "model": MODELS[provider],
        "messages": messages,
        "max_tokens": 300,
        "response_format": {"type": "json_schema", "json_schema": SCHEMA},
    }


def classify_result(response: dict) -> str:
    if response.get("error"):
        return str(response["error"])
    try:
        result = json.loads(response["content"])
    except (ValueError, TypeError, KeyError):
        return "invalid_json"
    if not isinstance(result, dict) or set(result) != set(SCHEMA["required"]):
        return "schema_error"
    if any(result[k] not in SCHEMA["properties"][k]["enum"]
           for k in ("materiality", "novelty", "reason_code", "confidence")):
        return "schema_error"
    if type(result.get("should_alert")) is not bool or not isinstance(result.get("symbol"), str):
        return "schema_error"
    try:
        validate_event_significance_output(result, expected_symbol=response.get("symbol"))
    except (ValueError, TypeError, KeyError):
        return "schema_error"
    return "valid"


def budget_allows(ledger: dict, provider: str, reserve: int, now: datetime) -> bool:
    consumed = sum(
        int(row["reserved"]) for row in ledger.get("attempts", [])
        if row["provider"] == provider
        and datetime.fromisoformat(row["timestamp"]).astimezone(timezone.utc).date()
        == now.astimezone(timezone.utc).date()
    )
    return consumed + reserve <= MAX_DAILY[provider]


def require_live_preflight(provider: str) -> None:
    if provider not in MODELS:
        raise RuntimeError("Unsupported provider")
    if any(os.environ.get(k) != "1" for k in REQUIRED_ATTESTATIONS):
        raise RuntimeError("CCW-16 preflight not verified for both providers")
    if not os.environ.get(PROVIDER_KEYS[provider]):
        raise RuntimeError("Isolated benchmark credentials not supplied")
    if provider == "cloudflare" and not os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        raise RuntimeError("Isolated Cloudflare account ID missing")


def _atomic_private_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        path.parent.chmod(0o700)
    tmp = path.with_name(path.name + ".tmp")
    descriptor = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(data, handle, separators=(",", ":"), sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)
    if os.name != "nt":
        path.chmod(0o600)


def prepare(benchmark: Path, reviewer: Path, manifest_path: Path) -> dict:
    audit = inspect_private_frozen(benchmark, reviewer)
    dataset = load_frozen(benchmark)
    _, labels = _read_evaluations(reviewer, dataset)
    cases = select_cases(dataset, labels)
    manifest = {
        "version": 1,
        "dataset_sha256": FROZEN_DATASET_SHA256,
        "cases": [
            {k: case[k] for k in ("id", "symbol", "input_sha256", "input")}
            for case in cases
        ],
    }
    _atomic_private_json(manifest_path, manifest)
    return {
        "prepared_cases": len(cases),
        "planned_provider_prompt_evaluations": len(work_items(cases)),
        "warrant_counts": dict(Counter(labels[c["id"]]["warrant"] for c in cases)),
        "dataset_sha256": audit["dataset_sha256"],
        "live_attempts": 0,
    }


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or data.get("dataset_sha256") != FROZEN_DATASET_SHA256:
        raise ValueError("Wrong frozen dataset/version")
    cases = data.get("cases", [])
    if len(cases) != 20 or len({x.get("id") for x in cases}) != 20:
        raise ValueError("Invalid manifest case coverage")
    if Counter(c["symbol"] for c in cases) != Counter({s: 5 for s in SYMBOLS}):
        raise ValueError("Invalid symbol distribution")
    for case in cases:
        if digest(case["input"]) != case["input_sha256"]:
            raise ValueError("Frozen model-visible input was changed")
    return data


def _reserve(provider: str, prompt: str) -> int:
    if provider == "cloudflare":
        # Conservative only for short input plus max 300 completion tokens.
        if len(prompt.encode("utf-8")) > 6000:
            raise ValueError("Cloudflare prompt exceeds conservative neuron reserve")
        return CLOUDFLARE_NEURON_RESERVE
    # Approximate worst-case token envelope: every UTF-8 byte as one token.
    return 6300 + len((SYSTEM_PROMPT + prompt).encode("utf-8"))


def _make_request(provider: str, body: dict) -> dict:
    import httpx

    token = os.environ[PROVIDER_KEYS[provider]]
    if provider == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
    else:
        account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
        if not account_id.replace("-", "").isalnum():
            raise ValueError("Invalid Cloudflare account ID")
        url = (f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
               "/ai/v1/chat/completions")
    try:
        response = httpx.post(url, json=body,
                              headers={"Authorization": f"Bearer {token}"},
                              timeout=110.0)
    except (httpx.TimeoutException, httpx.NetworkError):
        return {"error": "provider_error", "http_status": None}
    if response.status_code != 200:
        return {
            "error": "provider_error", "http_status": response.status_code,
            "rate_limited": response.status_code == 429,
        }
    try:
        payload = response.json()
        usage = payload.get("usage") or {}
        choices = payload["choices"]
        content = choices[0]["message"]["content"]
        return {
            "content": content,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "neurons": usage.get("neurons"),
        }
    except (KeyError, IndexError, ValueError, TypeError):
        return {"error": "schema_error", "http_status": 200}


def execute(manifest_path: Path, ledger_path: Path, provider: str, limit: int) -> dict:
    require_live_preflight(provider)
    if limit < 1 or limit > MAX_ATTEMPTS:
        raise ValueError("Finite attempt limit outside approved 1..120 range")
    manifest = load_manifest(manifest_path)
    previous = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {
        "version": 1, "dataset_sha256": FROZEN_DATASET_SHA256, "attempts": [],
    }
    if previous.get("version") != 1 or previous.get("dataset_sha256") != FROZEN_DATASET_SHA256:
        raise ValueError("Incompatible existing attempt ledger")
    keyed = {(x["id"], x["prompt"], x["provider"]) for x in previous["attempts"]}
    by_id = {c["id"]: c for c in manifest["cases"]}
    attempted_here = 0
    stop = "exhausted_requested_limit"
    for job in work_items(manifest["cases"]):
        if job["provider"] != provider:
            continue
        key = (job["id"], job["prompt"], provider)
        if key in keyed:
            continue  # Reservation survives crash; never auto-retry.
        if attempted_here >= limit or len(previous["attempts"]) >= MAX_ATTEMPTS:
            stop = "bounded_attempt_limit"
            break
        now = datetime.now(timezone.utc)
        latest = [datetime.fromisoformat(r["timestamp"]) for r in previous["attempts"]
                  if r["provider"] == provider]
        if latest and (now - max(latest)).total_seconds() < MIN_INTERVAL_SECONDS:
            stop = "minimum_interval_not_elapsed"
            break
        case = by_id[job["id"]]
        prompt = build_prompt(case["input"], job["prompt"])
        reserve = _reserve(provider, prompt)
        if not budget_allows(previous, provider, reserve, now):
            stop = "daily_reserved_quota_limit"
            break
        record = {
            **job, "timestamp": now.isoformat(), "reserved": reserve,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "model": MODELS[provider], "status": "reserved",
        }
        previous["attempts"].append(record)
        _atomic_private_json(ledger_path, previous)  # Persist BEFORE HTTP.
        attempted_here += 1
        result = _make_request(provider, request_body(provider, case["input"], prompt))
        result["symbol"] = case["symbol"]
        record["status"] = classify_result(result)
        for key in ("http_status", "prompt_tokens", "completion_tokens",
                    "total_tokens", "neurons"):
            if key in result:
                record[key] = result[key]
        if record["status"] == "valid":
            parsed = json.loads(result["content"])
            record["should_alert"] = parsed["should_alert"]
            record["materiality"] = parsed["materiality"]
            record["novelty"] = parsed["novelty"]
        _atomic_private_json(ledger_path, previous)
        if record.get("http_status") == 429 or record["status"] != "valid":
            stop = "provider_error_or_invalid_response"
            break  # Stop all local calls on errors, fail closed.
    return {
        "provider": provider, "attempts_this_invocation": attempted_here,
        "total_attempts": len(previous["attempts"]),
        "stop_reason": stop,
        "statuses": dict(Counter(x["status"] for x in previous["attempts"])),
    }


def score(benchmark: Path, reviewer: Path, ledger_path: Path) -> dict:
    inspect_private_frozen(benchmark, reviewer)
    ds = load_frozen(benchmark)
    _, labels = _read_evaluations(reviewer, ds)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    output = {}
    for provider in MODELS:
        output[provider] = {}
        for prompt in PROMPTS:
            records = [r for r in ledger["attempts"]
                       if r["provider"] == provider and r["prompt"] == prompt]
            v = [r for r in records if r["status"] == "valid"
                 and labels[r["id"]]["warrant"] != "ambiguous"]
            tp = sum(labels[r["id"]]["warrant"] == "alert" and r["should_alert"] for r in v)
            fn = sum(labels[r["id"]]["warrant"] == "alert" and not r["should_alert"] for r in v)
            fp = sum(labels[r["id"]]["warrant"] == "no_alert" and r["should_alert"] for r in v)
            tn = sum(labels[r["id"]]["warrant"] == "no_alert" and not r["should_alert"] for r in v)
            output[provider][prompt] = {
                "attempted": len(records), "valid_decisive": len(v),
                "ambiguous_valid": sum(
                    labels[r["id"]]["warrant"] == "ambiguous"
                    and r["status"] == "valid" for r in records),
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision_observed": tp / (tp + fp) if tp + fp else None,
                "recall_observed": tp / (tp + fn) if tp + fn else None,
                "pilot_complete": len(records) == 20 and all(
                    r["status"] == "valid" for r in records),
            }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", choices=tuple(MODELS))
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--benchmark", type=Path)
    parser.add_argument("--reviewer-a", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    if sum((args.prepare, bool(args.run), args.score)) != 1:
        parser.error("Select exactly one of --prepare, --run, --score")
    if args.prepare:
        if not args.benchmark or not args.reviewer_a:
            parser.error("Prepare needs --benchmark and --reviewer-a")
        result = prepare(args.benchmark, args.reviewer_a, args.manifest)
    elif args.run:
        if not args.ledger:
            parser.error("Run requires --ledger")
        require_live_preflight(args.run)
        args.ledger.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = args.ledger.with_name(args.ledger.name + ".lock")
        # Atomic cross-process lock. A crash leaves the lock, so the operator
        # must investigate before manually resuming; never double-spend quota.
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            result = execute(args.manifest, args.ledger, args.run, args.limit)
        finally:
            os.close(descriptor)
            lock.unlink()
    else:
        if not args.ledger or not args.benchmark or not args.reviewer_a:
            parser.error("Score requires --ledger, --benchmark and --reviewer-a")
        result = score(args.benchmark, args.reviewer_a, args.ledger)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
