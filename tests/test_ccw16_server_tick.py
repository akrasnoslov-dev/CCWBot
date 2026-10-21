"""Offline tests for the restricted CCW-16 server scheduler."""
import json
import os
from unittest.mock import patch

import pytest

from scripts import ccw16_server_tick as tick

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Hetzner-only scheduler")


def setup(tmp_path, count=8, invalid=False):
    calls = [
        {"id": f"case-{i}", "provider": provider, "prompt": variant}
        for provider in tick.PROVIDERS
        for variant in sorted(tick.PROMPTS)
        for i in range(20)
    ]
    staged = tmp_path / tick.STAGED.name
    staged.write_text(json.dumps({
        "version": 1, "dataset_sha256": tick.SHA256, "calls": calls,
    }), encoding="utf-8")
    staged.chmod(0o600)
    rows = [
        {
            "id": x["id"], "provider": x["provider"], "prompt": x["prompt"],
            "status": "schema_error" if invalid and n == 0 else "valid",
            "state": "finished",
        }
        for n, x in enumerate(calls[:count])
    ]
    ledger = tmp_path / tick.LEDGER.name
    ledger.write_text(json.dumps({
        "version": 1, "dataset_sha256": tick.SHA256, "attempts": rows,
    }), encoding="utf-8")
    ledger.chmod(0o600)
    (tmp_path / tick.RUNNER.name).write_text("# test\n", encoding="utf-8")


def test_progress_counts_are_strict(tmp_path):
    setup(tmp_path, 8)
    result = tick.inspect(tmp_path)
    assert result["total"] == 8
    assert result["by_provider"] == {"groq": 8, "cloudflare": 0}
    assert not result["completed"] and not result["blocked"]


def test_completion_requires_all_120_valid(tmp_path):
    setup(tmp_path, 120)
    result = tick.inspect(tmp_path)
    assert result["completed"]
    assert result["by_provider"] == {"groq": 60, "cloudflare": 60}


def test_invalid_output_halts_future_attempts(tmp_path):
    setup(tmp_path, 5, invalid=True)
    assert tick.inspect(tmp_path)["blocked"]


def test_duplicate_attempt_fails_closed(tmp_path):
    setup(tmp_path, 2)
    path = tmp_path / tick.LEDGER.name
    data = json.loads(path.read_text(encoding="utf-8"))
    data["attempts"][1] = data["attempts"][0]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match="duplicate"):
        tick.inspect(tmp_path)


def test_private_state_must_not_be_world_readable(tmp_path):
    setup(tmp_path, 0)
    (tmp_path / tick.STAGED.name).chmod(0o644)
    with pytest.raises(RuntimeError, match="permissions"):
        tick.inspect(tmp_path)


def test_dry_run_never_calls_provider(tmp_path):
    setup(tmp_path, 3)
    with (
        patch.object(tick, "check_identity"),
        patch.object(tick, "invoke_provider") as call,
    ):
        result = tick.tick(tmp_path, dry_run=True)
    assert result["state"] == "dry_run"
    call.assert_not_called()


def test_one_call_at_most_per_provider_per_tick(tmp_path):
    setup(tmp_path, 8)
    with (
        patch.object(tick, "check_identity"),
        patch.object(tick, "invoke_provider", return_value={
            "new_attempts": 1, "deferred": False,
        }) as call,
    ):
        result = tick.tick(tmp_path)
    assert result["state"] == "running"
    assert call.call_count == 2
    assert {c.args[0] for c in call.call_args_list} == set(tick.PROVIDERS)


def test_runner_error_halts(tmp_path):
    setup(tmp_path, 8)
    with (
        patch.object(tick, "check_identity"),
        patch.object(tick, "invoke_provider", side_effect=RuntimeError("error")),
    ):
        result = tick.tick(tmp_path)
    assert result["state"] == "halted_for_manual_review"
