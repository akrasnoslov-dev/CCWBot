"""Finite direct-provider CCW-16 canary runner; Python stdlib only.

This script does NOT access production, load Telegram or DB credentials,
register a timer, enable paid services, or retry failed provider requests.
Execute only as restricted ccwbot_ops in isolated CCW-16 home.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path("/home/ccwbot_ops/ccw16_replay")
INPUT = HERE / "private_calls.json"
CREDENTIALS = HERE / "secrets" / "providers.env"
LEDGER = HERE / "pilot-ledger.json"
LOCK = HERE / "running.lock"
MAX_TOTAL = 120
PER_PROVIDER = 60
MAX_DAILY = {"groq": 60_000, "cloudflare": 1_000}  # owner-approved 2026-10-21
MIN_SECONDS_BETWEEN_PROVIDER_CALLS = 90
EXPECTED_SHA = "ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
REQUIRED = {"symbol", "materiality", "novelty", "should_alert", "reason_code", "confidence"}
MATERIALITY = {"material", "routine", "unclear"}
NOVELTY = {"new", "continuation", "repeated", "unclear"}
REASONS_POS = {"unusual_move","fast_move","reversal","trend_acceleration","market_news_alignment"}
REASONS_NEG = {"routine_move","news_only","unclear"}


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_keys() -> dict:
    keys = {}
    if CREDENTIALS.stat().st_mode & 0o077:
        fail("Credential file is not private")
    for line in CREDENTIALS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = shlex.split(line)
        if len(parts) != 1 or "=" not in parts[0]:
            fail("Malformed provider credential line")
        key, value = parts[0].split("=", 1)
        keys[key] = value
    if set(keys) != {"GROQ_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"}:
        fail("Isolated credential subset violation")
    return keys


def read_calls() -> list:
    doc = json.loads(INPUT.read_text(encoding="utf-8"))
    if doc.get("dataset_sha256") != EXPECTED_SHA or doc.get("version") != 1:
        fail("Frozen input fingerprint mismatch")
    calls = doc.get("calls")
    if not isinstance(calls, list) or len(calls) != 120:
        fail("Expected exact 20-by-3-by-2 matrix")
    combinations = set()
    for row in calls:
        ident = (row["id"], row["prompt"], row["provider"])
        if ident in combinations:
            fail("Duplicate case/provider/prompt")
        combinations.add(ident)
        if row["provider"] not in {"groq", "cloudflare"}:
            fail("Unsupported provider")
        if hashlib.sha256(row["body"]["messages"][1]["content"].encode()).hexdigest() != row["prompt_sha256"]:
            fail("Prompt altered after offline freeze")
    if Counter(x["provider"] for x in calls) != {"groq": 60, "cloudflare": 60}:
        fail("Provider count mismatch")
    return calls


def read_ledger() -> dict:
    if not LEDGER.exists():
        return {"version": 1, "dataset_sha256": EXPECTED_SHA, "attempts": []}
    doc = json.loads(LEDGER.read_text(encoding="utf-8"))
    if doc.get("version") != 1 or doc.get("dataset_sha256") != EXPECTED_SHA:
        fail("Ledger fingerprint mismatch")
    return doc


def persist(doc: dict) -> None:
    tmp = LEDGER.with_suffix(".tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(doc, stream, separators=(",", ":"), sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, LEDGER)


def reserve_units(row: dict) -> int:
    if row["provider"] == "cloudflare":
        # 250 neurons upper bound for input <=6000 UTF-8 bytes and 300 output.
        # Model's Workers AI price coefficients are conservatively covered.
        if len(json.dumps(row["body"], separators=(",",":")).encode()) > 6000:
            fail("Cloudflare request exceeds conservative neuron reservation")
        if row["body"].get("max_tokens") != 300:
            fail("Unexpected Cloudflare output budget")
        return 250
    if row["body"].get("max_tokens") != 6300 or row["body"].get("reasoning_effort") != "medium":
        fail("Unexpected Groq inference budget/settings")
    total = sum(len(m["content"].encode("utf-8")) for m in row["body"]["messages"])
    return 6300 + total


def quota_allows(doc: dict, row: dict, reservation: int, now: datetime) -> tuple:
    previous = doc["attempts"]
    if len(previous) >= MAX_TOTAL:
        return False, "max_pilot_attempts"
    provider = row["provider"]
    matches = [x for x in previous if x["provider"] == provider]
    if len(matches) >= PER_PROVIDER:
        return False, "max_provider_attempts"
    if any(x.get("id") == row["id"] and x.get("prompt") == row["prompt"] for x in matches):
        return False, "already_attempted"
    recent = [x for x in matches
              if datetime.fromisoformat(x["timestamp"]).astimezone(timezone.utc).date() == now.date()]
    used = sum(x.get("settled_units", x["reserved_units"]) for x in recent)
    if used + reservation > MAX_DAILY[provider]:
        return False, "conservative_daily_cap"
    if matches:
        latest = max(datetime.fromisoformat(x["timestamp"]) for x in matches)
        if (now-latest).total_seconds() < MIN_SECONDS_BETWEEN_PROVIDER_CALLS:
            return False, "min_provider_spacing"
        if any(x.get("http_status") == 429 for x in recent):
            return False, "provider_429_today"
    return True, "ok"


def classify(payload: dict, symbol: str) -> tuple:
    try:
        text = payload["choices"][0]["message"]["content"]
        data = json.loads(text)
    except (TypeError, KeyError, IndexError, ValueError):
        return "invalid_json", None
    if not isinstance(data, dict) or set(data) != REQUIRED:
        return "schema_error", None
    if data["symbol"] != symbol:
        return "schema_error", None
    if type(data["should_alert"]) is not bool or data["materiality"] not in MATERIALITY or data["novelty"] not in NOVELTY:
        return "schema_error", None
    if data["confidence"] not in {"low", "medium", "high"}:
        return "schema_error", None
    if data["should_alert"]:
        if (data["materiality"] != "material" or data["novelty"] != "new"
                or data["reason_code"] not in REASONS_POS):
            return "schema_error", None
    elif data["reason_code"] not in REASONS_NEG:
        return "schema_error", None
    return "valid", data


def call_once(row: dict, keys: dict) -> dict:
    provider = row["provider"]
    if provider == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        auth = keys["GROQ_API_KEY"]
    else:
        account = keys["CLOUDFLARE_ACCOUNT_ID"]
        if not account.replace("-", "").isalnum():
            fail("Invalid Cloudflare account ID")
        url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions"
        auth = keys["CLOUDFLARE_API_TOKEN"]
    request = urllib.request.Request(
        url, data=json.dumps(row["body"], separators=(",",":")).encode("utf-8"),
        headers={"Authorization": "Bearer " + auth,
                 "Content-Type": "application/json",
                 "User-Agent": "CCW16-isolated-pilot/1"},
        method="POST")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=110) as answer:
            code = answer.status
            payload = json.loads(answer.read(500_000).decode("utf-8"))
        result = {"http_status": code, "duration_ms": round((time.monotonic()-t0)*1000)}
        # Compare with the symbol in the frozen model-visible market input.
        result["status"], parsed = classify(payload, row["symbol"])
        if parsed is not None:
            result["decision"] = {k:parsed[k] for k in REQUIRED}
        usage = payload.get("usage", {})
        if isinstance(usage, dict):
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if type(usage.get(k)) is int:
                    result[k] = usage[k]
        return result
    except urllib.error.HTTPError as exc:
        return {"status": "http_error", "http_status": exc.code,
                "duration_ms":round((time.monotonic()-t0)*1000)}
    except Exception as exc:
        return {"status": "transport_or_format_error", "error_type":type(exc).__name__,
                "duration_ms":round((time.monotonic()-t0)*1000)}


def reconcile_measured_usage(ledger: dict) -> None:
    """Release conservative in-flight reservations only for verified usage.

    Failed requests or missing/contradictory provider usage never receive a
    refund. Cloudflare neuron estimate includes a 25% safety margin.
    """
    changed = False
    for attempt in ledger["attempts"]:
        if attempt.get("status") != "valid" or "settled_units" in attempt:
            continue
        reserved = attempt["reserved_units"]
        if attempt["provider"] == "groq":
            total = attempt.get("total_tokens")
            if type(total) is not int or total < 1 or total > reserved:
                continue
            settled = total
        else:
            inp = attempt.get("prompt_tokens")
            out = attempt.get("completion_tokens")
            if type(inp) is not int or type(out) is not int or inp < 0 or out < 0:
                continue
            estimated = (inp*26668 + out*204805 + 999999) // 1000000
            settled = max(1, (estimated*125 + 99)//100)
            if settled > reserved:
                continue
        attempt["settled_units"] = settled
        changed = True
    if changed:
        persist(ledger)


def run(provider: str, count: int) -> dict:
    if os.getuid() == 0:
        fail("Never run as root")
    if Path.home() != Path("/home/ccwbot_ops"):
        fail("Not running under the isolated operator account")
    if provider not in ("groq", "cloudflare"):
        fail("Unsupported provider")
    keys = read_keys()
    rows = read_calls()
    ledger = read_ledger()
    reconcile_measured_usage(ledger)
    completed = []
    for row in rows:
        if row["provider"] != provider:
            continue
        if len(completed) >= count:
            break
        try:
            user_text = row["body"]["messages"][1]["content"]
            compact = json.loads(user_text.split("Input JSON:\n",1)[1])
            row["symbol"] = compact["sym"]
            if row["symbol"] not in ("BTC", "ETH", "GRAM", "SOL"):
                fail("Unexpected original model-visible symbol")
        except (ValueError, KeyError, IndexError, TypeError):
            fail("Cannot verify original model-visible symbol")
        now = datetime.now(timezone.utc)
        reservation = reserve_units(row)
        okay, reason = quota_allows(ledger, row, reservation, now)
        if not okay:
            # Only skip previously attempted jobs; stop on any quota/rate cap.
            if reason == "already_attempted":
                continue
            return {"provider":provider, "new_attempts":len(completed),
                    "stop":reason, "cases":completed}
        stamp = {"id":row["id"], "prompt":row["prompt"], "provider":provider,
                 "input_sha256":row["input_sha256"],
                 "prompt_sha256":row["prompt_sha256"],
                 "timestamp":now.isoformat(), "reserved_units":reservation,
                 "state":"reserved"}
        ledger["attempts"].append(stamp)
        persist(ledger)
        response = call_once(row,keys)
        stamp.update(response)
        stamp["state"] = "finished"
        reconcile_measured_usage(ledger)
        persist(ledger)
        completed.append({"status":stamp["status"],"http_status":stamp.get("http_status"),
                          "prompt":stamp["prompt"],"model":row["body"]["model"],
                          "tokens":stamp.get("total_tokens"),
                          "latency_ms":stamp.get("duration_ms")})
        # Do not retry failure or rate limit.
        if stamp["status"] != "valid":
            break
        if len(completed) < count:
            time.sleep(MIN_SECONDS_BETWEEN_PROVIDER_CALLS)
    return {"provider":provider, "new_attempts":len(completed),
            "pilot_attempts_total":len(ledger["attempts"]),
            "cases":completed}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--provider", required=True, choices=("groq","cloudflare"))
    parser.add_argument("--count", type=int, default=1)
    args=parser.parse_args()
    if args.count < 1 or args.count > 4:
        fail("Per-invocation maximum is 4 requests")
    os.mkdir(LOCK, mode=0o700)
    try:
        print(json.dumps(run(args.provider,args.count),sort_keys=True),flush=True)
    finally:
        os.rmdir(LOCK)

if __name__ == "__main__":
    main()
