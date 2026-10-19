"""Pure, offline safety and isolation checks for PR349 fallbacks."""
from datetime import datetime, timedelta, timezone

from scripts import auto_event_alert_quality_replay as worker
from scripts import multi_provider_event_significance_benchmark as benchmark


def test_cloudflare_uses_native_bare_schema_not_groq_envelope():
    fmt = benchmark.response_format(
        "cloudflare", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["type"] == "object"
    assert "schema" not in fmt["json_schema"]


def test_gemini_uses_json_object_mode():
    assert benchmark.response_format("gemini", "gemini-3.8-flash") == {
        "type": "json_object"}


def test_provider_retry_requires_transient_error_and_elapsed_backoff():
    now = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
    past = (now - timedelta(seconds=50)).isoformat()
    assert not benchmark.eligible_again({
        "status": "provider_error", "http_status": 429,
        "error_at_utc": past, "retry_after_seconds": 100,
    }, now)
    assert benchmark.eligible_again({
        "status": "provider_error", "http_status": 503,
        "error_at_utc": (now - timedelta(seconds=125)).isoformat(),
    }, now)
    assert not benchmark.eligible_again({
        "status": "provider_error", "http_status": 400,
        "error_at_utc": past,
    }, now)
    assert not benchmark.eligible_again({
        "status": "valid", "error_at_utc": past,
    }, now)


def test_replay_fingerprint_separates_providers():
    dataset = {"dataset_sha256": "test-snapshot"}
    g = {"provider": "gemini", "model": "gemini-3.8-flash",
         "max_tokens": 8500, "reasoning_effort": "medium",
         "format": {"type": "json_object"}}
    c = {**g, "provider": "cloudflare", "model": "llama"}
    assert benchmark.new_state(dataset, g)["fingerprint"] != (
        benchmark.new_state(dataset, c)["fingerprint"])


def test_auto_worker_dry_run_does_not_contact_providers(tmp_path, monkeypatch):
    frozen = tmp_path / "frozen.json"
    labels = tmp_path / "labels.json"
    frozen.touch()
    labels.touch()
    monkeypatch.setattr(worker, "FROZEN", frozen)
    monkeypatch.setattr(worker, "LABELS", labels)
    result = worker.run_once(dry_run=True)
    assert result == {"status": "dry_run", "providers": [
        "cloudflare", "gemini", "groq"]}


def test_worker_skips_candidate_with_impossible_recall(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(worker, "LOGDIR", tmp_path)
    monkeypatch.setitem(worker.CANDIDATES, "cloudflare", (
        "balanced_novelty", "global_prior_safe"))
    ledger = tmp_path / "fallback_cloudflare_balanced_novelty" / "replay_state.json"
    ledger.parent.mkdir()
    ledger.write_text(json.dumps({
        "dataset_sha256": "frozen",
        "runs": {"balanced_novelty": [
            {"id": "a", "status": "valid", "should_alert": False}]},
    }))
    dataset = {"dataset_sha256": "frozen",
               "cases": [{"id": name} for name in "abcde"]}
    labels = {name: "alert" for name in "abcde"}
    assert worker.select_candidate("cloudflare", dataset, labels) == (
        "global_prior_safe", "new_candidate")


def test_worker_stops_at_fully_scored_candidate(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(worker, "LOGDIR", tmp_path)
    monkeypatch.setitem(worker.CANDIDATES, "cloudflare", (
        "balanced_novelty", "global_prior_safe"))
    ledger = tmp_path / "fallback_cloudflare_balanced_novelty" / "replay_state.json"
    ledger.parent.mkdir()
    ledger.write_text(json.dumps({
        "dataset_sha256": "frozen",
        "runs": {"balanced_novelty": [
            {"id": "a", "status": "valid", "should_alert": True},
            {"id": "b", "status": "valid", "should_alert": False}]},
    }))
    dataset = {"dataset_sha256": "frozen",
               "cases": [{"id": "a"}, {"id": "b"}]}
    labels = {"a": "alert", "b": "no_alert"}
    assert worker.select_candidate("cloudflare", dataset, labels) == (
        None, "candidate_fully_scored_needs_review")


def test_worker_protects_production_groq_quota(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(worker, "LOGDIR", tmp_path)
    (tmp_path / "quality_worker_policy.json").write_text(
        json.dumps({"stop_groq_at_utc": "2020-01-01T00:00:00+00:00"}))
    assert worker.production_reserved("groq")
    assert not worker.production_reserved("cloudflare")

def test_cloudflare_neuron_accounting_is_aggregate_and_conservative(tmp_path):
    import json

    first = tmp_path / "fallback_cloudflare_one" / "replay_state.json"
    first.parent.mkdir()
    first.write_text(json.dumps({
        "attempted_requests": 3,
        "runs": {"one": [
            {"status": "valid", "prompt_tokens": 1000,
             "completion_tokens": 500},
            {"status": "provider_error"},
        ]},
    }))
    second = tmp_path / "fallback_cloudflare_two" / "replay_state.json"
    second.parent.mkdir()
    second.write_text(json.dumps({
        "attempted_requests": 1,
        "runs": {"two": [
            {"status": "valid", "prompt_tokens": 2000,
             "completion_tokens": 1000},
        ]},
    }))
    computed = benchmark.recorded_cloudflare_neurons(tmp_path)
    known = (
        (3000 * benchmark.CLOUDFLARE_INPUT_NEURONS_PER_M)
        + (1500 * benchmark.CLOUDFLARE_OUTPUT_NEURONS_PER_M)
    ) / 1_000_000
    assert abs(computed - known - 400) < 0.00001


def test_provider_wide_retry_after_covers_other_prompt_variants(tmp_path):
    import json

    now = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
    path = tmp_path / "fallback_cloudflare_old" / "replay_state.json"
    path.parent.mkdir()
    path.write_text(json.dumps({
        "runs": {"old": [{
            "status": "provider_error",
            "http_status": 429,
            "error_at_utc": (now - timedelta(seconds=30)).isoformat(),
            "retry_after_seconds": 503,
        }]},
    }))
    assert benchmark.provider_backoff_remaining(
        tmp_path, "cloudflare", now=now
    ) == 473
    assert benchmark.provider_backoff_remaining(
        tmp_path, "gemini", now=now
    ) == 0
    assert benchmark.provider_backoff_remaining(
        tmp_path, "cloudflare", now=now + timedelta(seconds=504)
    ) == 0
