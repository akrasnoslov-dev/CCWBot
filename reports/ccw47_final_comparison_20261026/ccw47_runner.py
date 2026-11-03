#!/usr/bin/env python3
"""CCW-12: isolated paid Luna replay vs saved Refined v2, no production writes.

Use in a separate checkout of dev under the unprivileged ccwbot_ops account.
The old Refined v2 calls are reused, not re-billed. No DB/Telegram access.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import statistics
import sys
import time
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime

DATASET = "ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
EXPECTED_CANDIDATE_SHA256 = "b2217c3608ec763d1b0072e75d3f34948dcedfb0ba25c3984560171aad05202c"
COST_LIMIT_USD = 0.50  # conservative per-run reservation; not an account-side billing limit
INPUT_RATE = 0.10 / 1_000_000  # verify billed rate separately before use
OUTPUT_RATE = 0.50 / 1_000_000
MAX_OUTPUT = 4096  # same as the original 200-case Luna test
MODEL = "gpt-6-luna"
SYSTEM = "You are a careful crypto monitoring assistant."
FIELDS = {"symbol", "materiality", "novelty", "should_alert", "reason_code", "confidence"}
POS = {"unusual_move", "fast_move", "reversal", "trend_acceleration", "market_news_alignment"}
NEG = {"routine_move", "news_only", "unclear"}
SOURCE_REL = pathlib.Path("research/event_alerts/versioned_evidence_20261026/reports/event-alert-review-20261016/ccw29_private/fresh200_unseen")
LABEL_REL = pathlib.Path("research/event_alerts/owner_labels_66.csv")
PROMPT_REL = pathlib.Path("benchmarks/event-alert-owner-20261026/prompt_refined_v2_final.txt")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(obj) -> str:
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, (int, float, str)):
        return json.dumps(obj, ensure_ascii=False, allow_nan=False)
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(canonical(v) for v in obj) + "]"
    if isinstance(obj, dict):
        return "{" + ",".join(json.dumps(str(k), ensure_ascii=False) + ":" + canonical(v)
                              for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))) + "}"
    raise TypeError(type(obj).__name__)


def percent(v):
    if v is None:
        return None
    try:
        x = round(v, 6)
    except (TypeError, ValueError):
        return v
    return v if x == 0 and v != 0 else x


def timestamp(v):
    if isinstance(v, dt.datetime):
        x = v
    else:
        v = str(v or "").strip()
        if not v:
            return None
        try:
            x = dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            try:
                x = parsedate_to_datetime(v)
            except (TypeError, ValueError):
                return None
    return x.replace(tzinfo=dt.timezone.utc) if x.tzinfo is None else x.astimezone(dt.timezone.utc)


def news_age(input_data, item):
    observed = timestamp(input_data.get("timestamp_utc"))
    published = timestamp(item.get("time") or item.get("published_at_utc") or
                          item.get("published_at") or item.get("published"))
    if not observed or not published:
        return None
    return max(0, int((observed - published).total_seconds() // 3600))


def compact(input_data):
    m = input_data.get("market") or {}
    snapshots = m.get("snapshots") or []
    n = []
    for item in (input_data.get("news") or [])[:2]:
        if not isinstance(item, dict):
            continue
        entry = {"t": item.get("title"), "r": item.get("relevance_label"),
                 "mat": item.get("material")}
        age = news_age(input_data, item)
        if age is not None:
            entry["h"] = age
        n.append(entry)
    p = {"sym": input_data.get("symbol"), "m": {
        "s": [[s.get("m"), s.get("p")] for s in snapshots[-6:] if isinstance(s, dict)],
        "w": m.get("analysed_window_minutes"),
        "c30": percent(m.get("chg30m_percent")),
        "c60": percent(m.get("chg1h_percent")),
        "cw": percent(m.get("chg_window_percent")),
        "c24": percent(m.get("chg24h_percent")),
        "cl": percent(m.get("chg_since_msg_percent")),
        "pw": percent(m.get("relative_window_percentile_30d")),
        "p24": percent(m.get("relative_24h_percentile_30d")),
    }, "n": n}
    prev = input_data.get("previous_event_alert") or {}
    if prev:
        p["prev"] = {"min": prev.get("age_minutes"), "f": prev.get("semantic_family"),
                     "cw": percent(prev.get("analysed_window_move"))}
    cnt = input_data.get("recent_event_counts") or {}
    if cnt:
        p["cnt"] = {"h6": cnt.get("h6"), "h24": cnt.get("h24")}
    return p


def load(repo):
    base = repo / SOURCE_REL
    source = json.loads((base / "fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf-8"))
    old = json.loads((base / "openai-luna-fresh200-ledger_PRIVATE.json").read_text(encoding="utf-8"))
    old_prompt = (base / "candidate_refined.txt").read_text(encoding="utf-8").rstrip("\r\n")
    new_prompt = (repo / PROMPT_REL).read_text(encoding="utf-8").rstrip("\r\n")
    if source["dataset_sha256"] != DATASET or old["dataset_sha256"] != DATASET:
        raise ValueError("Dataset mismatch; refusing paid test")
    cases = source["cases"]
    if len(cases) != 200 or len({x["id"] for x in cases}) != 200:
        raise ValueError("Frozen 200-case cohort missing or duplicated")
    previous = {x["id"]: x for x in old["attempts"] if x.get("prompt") == "refined"}
    if len(previous) != 200:
        raise ValueError("Refined v2 reference must contain exactly 200 matched decisions")
    for x in cases:
        # Reconstruct the actual production-equivalent compact input and validate it
        # against the old, paid, per-case request hashes. This protects matched parity.
        if sha(canonical(x["input"]).encode()) != x["input_sha256"]:
            raise ValueError("Source input hash mismatch: " + x["id"])
        candidate_old = old_prompt + "\nInput JSON:\n" + canonical(compact(x["input"]))
        prior = previous[x["id"]]
        if prior["status"] != "valid" or prior["input_sha256"] != x["input_sha256"]:
            raise ValueError("Old model result not valid or input not matched: " + x["id"])
        if sha(candidate_old.encode()) != prior["prompt_sha256"]:
            raise ValueError("Original Refined v2 prompt reconstruction differs: " + x["id"])
        if prior["symbol"] != x["symbol"]:
            raise ValueError("Symbol mismatch: " + x["id"])
    if sha(new_prompt.encode()) != EXPECTED_CANDIDATE_SHA256:
        raise ValueError("Frozen new candidate prompt SHA differs; refusing paid calls")
    if len(new_prompt) < 400 or new_prompt == old_prompt:
        raise ValueError("Final prompt absent/unchanged")
    with (repo / LABEL_REL).open(encoding="utf-8", newline="") as f:
        labels = {x["case_id"]: x["owner_label"] for x in csv.DictReader(f)}
    if len(labels) != 66 or collections.Counter(labels.values()) != {"alert": 24, "no_alert": 34, "ambiguous": 8}:
        raise ValueError("Owner review labels differ from frozen reference")
    if not set(labels).issubset(previous):
        raise ValueError("Owner labels do not belong to same frozen market cohort")
    return cases, previous, labels, new_prompt, old_prompt


def valid_decision(answer, sym):
    if not isinstance(answer, dict) or set(answer) != FIELDS or answer["symbol"] != sym:
        return False
    if type(answer["should_alert"]) is not bool:
        return False
    if answer["materiality"] not in {"material", "routine", "unclear"} or answer["novelty"] not in {"new", "continuation", "repeated", "unclear"}:
        return False
    if answer["confidence"] not in {"low", "medium", "high"}:
        return False
    if answer["should_alert"]:
        return answer["materiality"] == "material" and answer["novelty"] == "new" and answer["reason_code"] in POS
    return answer["reason_code"] in NEG and not (answer["materiality"] == "material" and answer["novelty"] == "new")


def write_atomic(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix(".tmp")
    with temp.open("x", encoding="utf-8") as f:
        os.chmod(temp, 0o600)
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def reserve(messages):
    # UTF-8 bytes are a deliberately conservative input-token allowance.
    input_max = sum(len(m["content"].encode("utf-8")) for m in messages) + 1024
    return round(input_max * INPUT_RATE + MAX_OUTPUT * OUTPUT_RATE, 9)


def execute(repo, work, cases, old, labels, prompt):
    if os.geteuid() == 0:
        raise ValueError("Paid requests must run unprivileged, not as root")
    if work.is_symlink():
        raise ValueError("Workspace may not be a symlink")
    work.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(work, 0o700)
    key_path = work / "openai_test_key.private"
    ledger_path = work / "new_refined_luna_ledger_PRIVATE.json"
    if not key_path.is_file() or key_path.is_symlink() or key_path.stat().st_mode & 0o077:
        raise ValueError("Missing private mode-0600 test key file in isolated workspace")
    key = key_path.read_text(encoding="utf-8").strip()
    if not key.startswith("sk-"):
        raise ValueError("OpenAI test key missing/malformed")
    settings = {"dataset_sha256": DATASET, "model": MODEL, "prompt_sha256": sha(prompt.encode()),
                "max_completion_tokens": MAX_OUTPUT, "max_budget_usd": COST_LIMIT_USD,
                "input_rate_per_million_usd": INPUT_RATE * 1_000_000,
                "output_rate_per_million_usd": OUTPUT_RATE * 1_000_000,
                "baseline_reused_paid_results": True}
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        if any(ledger.get(k) != v for k, v in settings.items()):
            raise ValueError("Existing test ledger settings mismatch")
    else:
        ledger = dict(settings, rows=[])
        write_atomic(ledger_path, ledger)
    seen = {row["id"] for row in ledger["rows"]}
    if len(seen) != len(ledger["rows"]):
        raise ValueError("Duplicate attempts detected")
    used = sum(float(row.get("charged_upper_usd", row["reserved_usd"])) for row in ledger["rows"])
    failures = []
    try:
        for index, case in enumerate(cases, 1):
            if case["id"] in seen:
                continue  # never retry uncertain responses on resume
            user = prompt + "\nInput JSON:\n" + canonical(compact(case["input"]))
            messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
            expected_max = reserve(messages)
            if used + expected_max > COST_LIMIT_USD:
                print("STOP: $0.50 conservative request budget exhausted", flush=True)
                break
            body = {"model": MODEL, "messages": messages, "response_format": {"type": "json_object"},
                    "max_completion_tokens": MAX_OUTPUT}
            row = {"id": case["id"], "symbol": case["symbol"], "input_sha256": case["input_sha256"],
                   "prompt_sha256": sha(user.encode()), "reserved_usd": expected_max,
                   "charged_upper_usd": expected_max, "status": "in_flight",
                   "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
            ledger["rows"].append(row)
            write_atomic(ledger_path, ledger)  # checkpoint BEFORE paid request
            used += expected_max
            req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
                data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode(),
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                         "User-Agent": "CCW12-paired-luna-isolated/1"}, method="POST")
            started = time.monotonic()
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    obj = json.loads(resp.read(1000000))
                    code = resp.status
                content = obj["choices"][0]["message"].get("content")
                decision = json.loads(content) if content else None
                usage = obj.get("usage") or {}
                inp, out = usage.get("prompt_tokens"), usage.get("completion_tokens")
                success = valid_decision(decision, case["symbol"])
                cost = inp * INPUT_RATE + out * OUTPUT_RATE if type(inp) is int and type(out) is int and inp >= 0 and out >= 0 else expected_max
                if cost > expected_max + 1e-7:
                    row["status"] = "cost_bounds_error"
                    failures.append("Measured cost exceeded conservative reservation")
                else:
                    row["status"] = "valid" if success else "invalid_response"
                row.update(http_status=code, input_tokens=inp, completion_tokens=out,
                           latency_ms=round((time.monotonic() - started) * 1000),
                           charged_upper_usd=round(cost, 9))
                if success:
                    row["decision"] = decision
                used += row["charged_upper_usd"] - expected_max
            except urllib.error.HTTPError as exc:
                row.update(status="http_error", http_status=exc.code,
                           latency_ms=round((time.monotonic() - started) * 1000))
                failures.append("HTTP error; no automatic retry")
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError) as exc:
                row.update(status="transport_or_parse_error", error_type=type(exc).__name__,
                           latency_ms=round((time.monotonic() - started) * 1000))
                failures.append("Unknown request result; no automatic retry")
            write_atomic(ledger_path, ledger)
            print(f"{index}/200; valid={sum(r['status']=='valid' for r in ledger['rows'])}; "
                  f"upper_spend_usd={used:.6f}; last_status={row['status']}", flush=True)
            # Preserve every non-valid result and continue with the next untouched
            # case. Never retry a recorded case. Stop only when access/rate/budget
            # conditions make further requests unsafe or non-comparable.
            if row.get("status") == "cost_bounds_error" or row.get("http_status") in {400, 401, 402, 403, 429}:
                print("STOP: paid run halted on access, rate-limit, or budget error", flush=True)
                break
    finally:
        key_path.unlink(missing_ok=True)
        print("Ephemeral key file removed", flush=True)
    return ledger


def summarize(cases, old, labels, ledger, prompt, old_prompt):
    fresh = {r["id"]: r for r in ledger["rows"] if r.get("status") == "valid"}
    comparable = [c for c in cases if c["id"] in fresh]
    def score(lookup, keys):
        a = collections.Counter()
        for id_ in keys:
            label = labels[id_]
            if label == "ambiguous":
                continue
            result = lookup[id_]["decision"]["should_alert"]
            a[("TP" if result else "FN") if label == "alert" else ("FP" if result else "TN")] += 1
        return a
    table = ["# CCW-12 matched Luna significance comparison", "",
             f"Frozen dataset: `{DATASET}`. New prompt SHA-256: `{sha(prompt.encode())}`. "
             f"Old prompt SHA-256: `{sha(old_prompt.encode())}`.",
             "Old Refined v2 = archived paid Luna responses; Refined v2 final = new paid Luna responses on identical cases. "
             "No production LLM routing, database records, Telegram sends or recipient cooldown were changed.", "",
             "## Matched comparison", "",
             "| Metric | Refined v2 (old) | Refined v2 final (new) |", "|---|---:|---:|"]
    old_rows = [old[c["id"]] for c in comparable]
    new_rows = [fresh[c["id"]] for c in comparable]
    def fmt(v):
        return str(v) if not isinstance(v,float) else f"{v:.6f}"
    def add(name, a, b):
        table.append(f"| {name} | {fmt(a)} | {fmt(b)} |")
    add("Valid / all 200", len(old), len(fresh))
    add("Matched decisions", len(comparable), len(comparable))
    add("Proposed alerts / matched", sum(r["decision"]["should_alert"] for r in old_rows),
        sum(r["decision"]["should_alert"] for r in new_rows))
    for k, v in [(k,[c for c in comparable if c["symbol"]==k]) for k in ("BTC","ETH","GRAM","SOL")]:
        add(f"{k} alerts / matched", sum(old[c["id"]]["decision"]["should_alert"] for c in v),
            sum(fresh[c["id"]]["decision"]["should_alert"] for c in v))
    scored = [c["id"] for c in comparable if c["id"] in labels and labels[c["id"]] != "ambiguous"]
    old_score = score(old, scored)
    new_score = score(fresh, scored)
    add("Owner-labelled decisive matches (selection-biased)", len(scored), len(scored))
    for k in ("TP", "FP", "FN", "TN"):
        add("Owner-review " + k, old_score[k], new_score[k])
    for label, numerator in (("Conditional precision", "TP"), ("Conditional recall", "TP")):
        denom = ("FP" if label.endswith("precision") else "FN")
        def ratio(s):
            return f"{100*s[numerator]/(s[numerator]+s[denom]):.1f}%" if s[numerator]+s[denom] else "N/A"
        add(label + " (58 selected disagreements)", ratio(old_score), ratio(new_score))
    ambiguous_ids = [c["id"] for c in comparable if labels.get(c["id"]) == "ambiguous"]
    add("Owner ambiguous (excluded)", len(ambiguous_ids), len(ambiguous_ids))
    add("Alerts among owner-ambiguous cases", sum(old[i]["decision"]["should_alert"] for i in ambiguous_ids),
        sum(fresh[i]["decision"]["should_alert"] for i in ambiguous_ids))
    for symbol in ("BTC", "ETH", "GRAM", "SOL"):
        per = [i for i in scored if old[i]["symbol"] == symbol]
        a, b = score(old, per), score(fresh, per)
        add(symbol + " owner TP/FP/FN/TN", "/".join(str(a[k]) for k in ("TP", "FP", "FN", "TN")),
            "/".join(str(b[k]) for k in ("TP", "FP", "FN", "TN")))
    for field in ("materiality", "novelty", "reason_code", "confidence"):
        a, b = collections.Counter(r["decision"][field] for r in old_rows), collections.Counter(r["decision"][field] for r in new_rows)
        for value in sorted(a.keys() | b.keys()):
            add(field + ": " + str(value), a[value], b[value])
    for key, title in (("prompt_tokens", "Input tokens"), ("completion_tokens", "Completion tokens incl. reasoning"),
                       ("estimated_charged_usd", "USD uncached-price upper estimate"),
                       ("duration_ms", "Median latency ms")):
        other = "charged_upper_usd" if key == "estimated_charged_usd" else "latency_ms" if key == "duration_ms" else key
        a = [r[key] for r in old_rows if isinstance(r.get(key),(int,float))]
        b = [r[other] for r in new_rows if isinstance(r.get(other),(int,float))]
        if "Median" in title:
            add(title, statistics.median(a) if a else "N/A", statistics.median(b) if b else "N/A")
        else:
            add(title + " (matched)", sum(a), sum(b))
            add(title + " / case avg", statistics.mean(a) if a else "N/A", statistics.mean(b) if b else "N/A")
    add("Median input tokens", statistics.median([r["prompt_tokens"] for r in old_rows]),
        statistics.median([r["input_tokens"] for r in new_rows])) if new_rows else None
    add("Median completion tokens", statistics.median([r["completion_tokens"] for r in old_rows]),
        statistics.median([r["completion_tokens"] for r in new_rows])) if new_rows else None
    def percentile_95(values):
        return sorted(values)[max(0, __import__("math").ceil(len(values)*0.95) - 1)] if values else "N/A"
    add("P95 response latency ms", percentile_95([r["duration_ms"] for r in old_rows]),
        percentile_95([r["latency_ms"] for r in new_rows]))
    add("New paid calls", 0, len(ledger["rows"]))
    add("New paid spending (estimate)", 0, sum(r.get("charged_upper_usd",0) for r in ledger["rows"]))
    add("Total old experiment cost USD / 200", sum(r["estimated_charged_usd"] for r in old.values()),
        "N/A — see new paid spending")
    add("New non-valid responses", 0, sum(r["status"] != "valid" for r in ledger["rows"]))
    add("Identical binary decisions", len(comparable),
        sum(old[c["id"]]["decision"]["should_alert"] == fresh[c["id"]]["decision"]["should_alert"] for c in comparable))
    table += ["", "## Changed binary decisions", "",
              "| Direction | Count | Case IDs |", "|---|---:|---|"]
    for was, became, title in [(False,True,"no_alert → alert"),(True,False,"alert → no_alert")]:
        ids = [c["id"] for c in comparable if old[c["id"]]["decision"]["should_alert"] == was and
               fresh[c["id"]]["decision"]["should_alert"] == became]
        table.append(f"| {title} | {len(ids)} | {', '.join(ids) if ids else '—'} |")
    table += ["", "## Limits", "",
        "- Precision/recall are **conditional on 58 selected disagreement cases**, not representative of 200 or unseen live traffic.",
        "- This is a replay of archived real-production market contexts; not a live collection or Telegram-delivery test.",
        "- Same coin/family recipient cooldown, final Situation/Possible Action, and production Groq/Cloudflare behavior are **not evaluated**.",
        "- OpenAI usage is per-request metering; price rates are inherited from archived Luna experiment and should be checked against current billing.",
        "- Only the owner can choose a winner; do not change production or merge new significance instructions automatically.",
        "- Incomplete coverage or errors prevent a final head-to-head decision; no re-run without explicit authorization."]
    return "\n".join(table) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("preflight", "run", "report"))
    ap.add_argument("--repo", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    ap.add_argument("--work", type=pathlib.Path, default=pathlib.Path.home() / "ccw12_refined_compare")
    args = ap.parse_args()
    args.repo = args.repo.resolve()
    cases, old, labels, prompt, old_prompt = load(args.repo)
    if args.mode == "preflight":
        print(json.dumps({"status": "READY", "model": MODEL, "dataset_sha256": DATASET,
              "cases": len(cases), "old_valid": len(old), "owner_labels": len(labels),
              "old_prompt_sha256": sha(old_prompt.encode()), "new_prompt_sha256": sha(prompt.encode()),
              "new_max_budget_usd": COST_LIMIT_USD, "new_calls": 200,
              "price_assumption_usd_per_1m_tokens": [INPUT_RATE * 1_000_000,OUTPUT_RATE * 1_000_000],
              "production_changes": False}, ensure_ascii=False, indent=2))
        return
    args.work.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(args.work,0o700)
    if args.mode == "run":
        ledger = execute(args.repo, args.work, cases, old, labels, prompt)
    else:
        p = args.work / "new_refined_luna_ledger_PRIVATE.json"
        if not p.is_file():
            raise ValueError("No new paid-run ledger exists; run command first")
        ledger = json.loads(p.read_text(encoding="utf-8"))
    if ledger.get("dataset_sha256") != DATASET or ledger.get("prompt_sha256") != sha(prompt.encode()):
        raise ValueError("Ledger/dataset/prompt mismatch")
    report = summarize(cases, old, labels, ledger, prompt, old_prompt)
    destination = args.work / "CCW12_REFINED_COMPARISON.md"
    destination.write_text(report, encoding="utf-8")
    os.chmod(destination,0o600)
    print("REPORT:", destination)
    print(report.split("## Changed binary decisions")[0])


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, AssertionError) as err:
        sys.exit("SAFE_STOP: " + str(err))
