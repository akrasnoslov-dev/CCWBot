"""Circuit breaker and provider-side 4xx fallback, with mocked providers only.

Nothing here reaches a real provider: every failure is a constructed exception.
"""

from datetime import datetime, timedelta, timezone

import pytest

from bot.services.llm import breaker
from bot.services.llm import config as llm_config
from bot.services.llm.base_provider import BaseProvider, ProviderResult
from bot.services.llm.errors import AIProviderRateLimitError, AllProvidersFailedError
from bot.services.llm.router import LLMRouter
from bot.services.llm.telemetry import classify_ai_error_reason

# Breaker state and the LLM_BREAKER_* variables are reset per test by the session-wide autouse
# fixture in tests/conftest.py, because breaker state is process-global and leaks across files.


class FakeProvider(BaseProvider):
    def __init__(self, name, behavior):
        self.name = name
        self._behavior = behavior
        self.calls = 0

    async def chat_completion(self, *, call_type, symbol, model, messages, max_tokens,
                              response_format, timeout=15, reasoning_effort=None):
        self.calls += 1
        behavior = self._behavior
        if isinstance(behavior, BaseException):
            raise behavior
        if callable(behavior):
            return behavior(name=self.name, model=model)
        return behavior


def _result(name, model="m"):
    return ProviderResult(provider=name, model=model, raw_content="{}", input_chars=1)


def _ok(name, model):
    return _result(name, model)


def _error(status_code, message="boom", code=None, body=None):
    err = RuntimeError(message)
    err.status_code = status_code
    if code is not None:
        err.code = code
    if body is not None:
        err.body = body
    return err


def _groq_decommissioned_error():
    """The shape Groq actually returns for a decommissioned model.

    The body carries BOTH `code: model_decommissioned` and `type: invalid_request_error`, and
    the latter matches the bad-request markers. This is the payload that caused the 18-day
    outage, so it is pinned here rather than approximated.
    """
    return _error(
        400,
        "Error code: 400 - {'error': {'message': 'The model "
        "`meta-llama/llama-4-scout-17b-16e-instruct` has been decommissioned and is no longer "
        "supported.', 'type': 'invalid_request_error', 'code': 'model_decommissioned'}}",
        body={
            "error": {
                "message": (
                    "The model `meta-llama/llama-4-scout-17b-16e-instruct` has been "
                    "decommissioned and is no longer supported."
                ),
                "type": "invalid_request_error",
                "code": "model_decommissioned",
            }
        },
    )


def _configure(monkeypatch, priority, keys):
    monkeypatch.setenv("LLM_PROVIDER_PRIORITY", ",".join(priority))
    # Per-call-type overrides take precedence over LLM_PROVIDER_PRIORITY, so a value in the
    # developer's .env would otherwise silently reorder the chain under these tests.
    for override in ("LLM_EVENT_PROVIDERS", "LLM_REPORT_PROVIDERS", "LLM_HEARTBEAT_PROVIDERS"):
        monkeypatch.delenv(override, raising=False)
    for provider in ("groq", "cerebras", "gemini", "mistral"):
        env = llm_config.api_key_env(provider)
        if provider in keys:
            monkeypatch.setenv(env, f"{provider}-key")
        else:
            monkeypatch.delenv(env, raising=False)


async def _call(router, call_type="event_analysis"):
    return await router.chat_completion(
        call_type=call_type,
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=10,
        response_format=None,
    )


# --- failure classification -------------------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        _error(404, "The model `llama-4-scout` does not exist or you do not have access"),
        _error(404, "model not found", code="model_not_found"),
        _error(400, "model has been decommissioned", code="model_decommissioned"),
        _error(400, "Invalid model: foo"),
        _error(404, "models/gemini-9 is not found for API version v1beta"),
        _error(400, "unknown model", code="unknown_model"),
    ],
)
def test_provider_side_model_failures_classify_as_model_error(error):
    assert classify_ai_error_reason(error) == "provider_model_error"


@pytest.mark.parametrize(
    "error",
    [
        _error(400, "context_length_exceeded: too many tokens"),
        _error(413, "request too large"),
        _error(400, "unsupported parameter: reasoning_effort"),
        _error(400, "missing required field messages"),
    ],
)
def test_genuine_request_defects_classify_as_bad_request(error):
    assert classify_ai_error_reason(error) == "provider_bad_request"


def test_json_validate_failed_gets_its_own_reason():
    error = _error(400, "json_validate_failed", code="json_validate_failed")
    assert classify_ai_error_reason(error) == "provider_json_validate_failed"


def test_unclassified_4xx_still_reports_provider_4xx():
    assert classify_ai_error_reason(_error(402, "payment required")) == "provider_4xx"


def test_real_groq_decommission_payload_classifies_as_model_error():
    # Regression guard for the exact 2026-07-17 failure. The body matches BOTH the model
    # markers and `invalid_request_error`, so this pins the check order: reorder the branches
    # in classify_ai_error_reason and the outage reproduces.
    assert classify_ai_error_reason(_groq_decommissioned_error()) == "provider_model_error"


def test_model_marker_in_the_body_alone_is_enough():
    # A client that surfaces only structured fields, with an unhelpful str(error).
    error = _error(400, "Bad Request", body={"error": {"code": "model_decommissioned"}})
    assert classify_ai_error_reason(error) == "provider_model_error"


def test_json_validate_marker_in_the_body_alone_is_enough():
    # Without reading the body this would match `invalid_request_error` and be misread as a
    # defective request, which is terminal — the opposite of the intended handling.
    error = _error(
        400,
        "Bad Request",
        body={"error": {"code": "json_validate_failed", "type": "invalid_request_error"}},
    )
    assert classify_ai_error_reason(error) == "provider_json_validate_failed"


@pytest.mark.asyncio
async def test_real_groq_decommission_payload_advances_the_chain(monkeypatch):
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = FakeProvider("groq", _groq_decommissioned_error())
    cerebras = FakeProvider("cerebras", _ok)
    router = LLMRouter(registry={"groq": groq, "cerebras": cerebras})

    result = await _call(router)

    assert result.provider == "cerebras"


def test_new_reasons_keep_the_provider_prefix_ops_agent_matches_on():
    # ops-agent buckets llm failures with `error_reason LIKE 'provider_%'`; the sub-kinds must
    # stay inside that pattern so existing queries and detectors keep working unchanged.
    # Derived from the classifier, not from literals, so a rename cannot pass this silently.
    reasons = {
        classify_ai_error_reason(_error(404, "model_not_found")),
        classify_ai_error_reason(_error(400, "context_length_exceeded")),
        classify_ai_error_reason(_error(400, "json_validate_failed")),
        classify_ai_error_reason(_error(402, "payment required")),
        classify_ai_error_reason(
            AllProvidersFailedError("all circuit-broken", circuit_broken=True)
        ),
    }
    assert len(reasons) == 5
    for reason in reasons:
        assert reason.startswith("provider_")


# --- fallback eligibility ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_model_not_found_advances_the_chain(monkeypatch):
    # The 2026-07-17 outage: Groq answered 404 model_not_found for the pinned event-analysis
    # model and the configured Cerebras fallback was never attempted.
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = FakeProvider("groq", _error(404, "model_not_found", code="model_not_found"))
    cerebras = FakeProvider("cerebras", _ok)
    router = LLMRouter(registry={"groq": groq, "cerebras": cerebras})

    result = await _call(router)

    assert result.provider == "cerebras"
    assert groq.calls == 1
    assert cerebras.calls == 1


@pytest.mark.asyncio
async def test_genuine_bad_request_does_not_advance_the_chain(monkeypatch):
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = FakeProvider("groq", _error(400, "context_length_exceeded"))
    cerebras = FakeProvider("cerebras", _ok)
    router = LLMRouter(registry={"groq": groq, "cerebras": cerebras})

    with pytest.raises(RuntimeError) as raised:
        await _call(router)

    assert "context_length_exceeded" in str(raised.value)
    assert cerebras.calls == 0


@pytest.mark.asyncio
async def test_json_validate_failed_advances_the_chain(monkeypatch):
    # Positive case for the step-2 decision: unusable model *output* is fallback-eligible,
    # matching how a client-side AIInvalidJsonError has always been handled.
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = FakeProvider("groq", _error(400, "json_validate_failed", code="json_validate_failed"))
    cerebras = FakeProvider("cerebras", _ok)
    router = LLMRouter(registry={"groq": groq, "cerebras": cerebras})

    result = await _call(router)

    assert result.provider == "cerebras"
    assert groq.calls == 1
    assert cerebras.calls == 1


@pytest.mark.asyncio
async def test_json_validate_failed_does_not_advance_past_a_bad_request(monkeypatch):
    # Negative case for the same decision: the fallback-eligible set was widened for output
    # failures only. A malformed request is still terminal on the first provider.
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = FakeProvider("groq", _error(400, "invalid_request_error: bad messages"))
    cerebras = FakeProvider("cerebras", _ok)
    router = LLMRouter(registry={"groq": groq, "cerebras": cerebras})

    with pytest.raises(RuntimeError):
        await _call(router)
    assert cerebras.calls == 0


@pytest.mark.asyncio
async def test_all_providers_model_broken_raises_all_failed(monkeypatch):
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", _error(404, "model_not_found")),
            "cerebras": FakeProvider("cerebras", _error(404, "model_not_found")),
        }
    )

    with pytest.raises(AllProvidersFailedError):
        await _call(router)


# --- circuit breaker --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_breaker_opens_after_threshold_and_skips_the_pair(monkeypatch):
    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "3")
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = FakeProvider("groq", _error(404, "model_not_found"))
    cerebras = FakeProvider("cerebras", _ok)
    router = LLMRouter(registry={"groq": groq, "cerebras": cerebras})

    for _ in range(3):
        assert (await _call(router)).provider == "cerebras"
    assert groq.calls == 3

    # Fourth cycle: groq is open, so it is skipped without spending a request.
    assert (await _call(router)).provider == "cerebras"
    assert groq.calls == 3
    assert cerebras.calls == 4


@pytest.mark.asyncio
async def test_open_breaker_does_not_cost_a_cycle(monkeypatch):
    # The important half of "must not suppress the fallback chain": skipping a broken primary
    # means the fallback answers *this* cycle, not that the cycle produces nothing.
    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "1")
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = FakeProvider("groq", _error(404, "model_not_found"))
    router = LLMRouter(registry={"groq": groq, "cerebras": FakeProvider("cerebras", _ok)})

    await _call(router)
    result = await _call(router)

    assert result.provider == "cerebras"
    assert groq.calls == 1  # attempted once, then skipped rather than re-attempted


def test_breaker_half_opens_on_schedule_then_closes_on_success():
    monkeypatch_now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    for _ in range(5):
        breaker.record_failure(**key, reason="provider_model_error", now=monkeypatch_now)

    assert breaker.should_skip(**key, now=monkeypatch_now) is True
    # Still open just before the first backoff step (60s) elapses.
    assert breaker.should_skip(**key, now=monkeypatch_now + timedelta(seconds=59)) is True
    # Elapsed -> half-open, so exactly one probe is allowed through.
    assert breaker.should_skip(**key, now=monkeypatch_now + timedelta(seconds=61)) is False

    breaker.record_success(**key)
    assert breaker.should_skip(**key, now=monkeypatch_now + timedelta(seconds=62)) is False
    assert breaker.breaker_snapshot() == {}


def test_failed_half_open_probe_widens_the_interval():
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    for _ in range(5):
        breaker.record_failure(**key, reason="provider_model_error", now=now)
    first_open_until = breaker.breaker_snapshot()[("event_analysis", "groq", "m")]["open_until"]
    assert first_open_until == now + timedelta(seconds=60)

    # Elapse, probe, fail again -> next (wider) step of the schedule.
    breaker.should_skip(**key, now=now + timedelta(seconds=61))
    breaker.record_failure(**key, reason="provider_model_error", now=now + timedelta(seconds=61))
    second_open_until = breaker.breaker_snapshot()[("event_analysis", "groq", "m")]["open_until"]

    assert second_open_until == now + timedelta(seconds=61) + timedelta(seconds=300)


def test_breaker_backoff_schedule_is_configurable(monkeypatch):
    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("LLM_BREAKER_BACKOFF_SECONDS", "10,20")
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    breaker.record_failure(**key, reason="provider_model_error", now=now)
    assert breaker.breaker_snapshot()[("event_analysis", "groq", "m")]["open_until"] == (
        now + timedelta(seconds=10)
    )


def test_breaker_state_is_per_call_type_and_model():
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    broken = {"call_type": "event_analysis", "provider": "groq", "model": "dead-model"}

    for _ in range(5):
        breaker.record_failure(**broken, reason="provider_model_error", now=now)

    assert breaker.should_skip(**broken, now=now) is True
    # Same provider, different call type -> unaffected.
    assert breaker.should_skip(
        call_type="daily_report", provider="groq", model="dead-model", now=now
    ) is False
    # Same call type and provider, different model -> unaffected.
    assert breaker.should_skip(
        call_type="event_analysis", provider="groq", model="live-model", now=now
    ) is False
    # Different provider -> unaffected.
    assert breaker.should_skip(
        call_type="event_analysis", provider="cerebras", model="dead-model", now=now
    ) is False


def test_transient_failures_do_not_open_the_breaker():
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    for reason in ("rate_limit", "timeout", "provider_5xx", "network_error", "invalid_json"):
        for _ in range(10):
            breaker.record_failure(**key, reason=reason, now=now)

    assert breaker.should_skip(**key, now=now) is False
    assert breaker.breaker_snapshot() == {}


def test_breaker_only_counts_fallback_eligible_reasons():
    # Invariant: opening a breaker on a reason the router treats as terminal would skip the
    # primary next cycle and hand the same defective request to the fallback, walking a
    # purely client-side bug down the whole chain.
    from bot.services.llm.router import _FALLBACK_REASONS

    assert breaker.DETERMINISTIC_BREAKER_REASONS <= _FALLBACK_REASONS


@pytest.mark.parametrize("reason", ["provider_bad_request", "provider_4xx"])
def test_terminal_request_defects_do_not_open_the_breaker(reason):
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    for _ in range(10):
        breaker.record_failure(**key, reason=reason, now=now)

    assert breaker.should_skip(**key, now=now) is False


def test_json_validate_failures_do_not_open_the_breaker():
    # Content-dependent: the prompt carries fresh market data every cycle, and the client-side
    # equivalent (AIInvalidJsonError) does not open a breaker either. The two must agree.
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    for _ in range(10):
        breaker.record_failure(**key, reason="provider_json_validate_failed", now=now)

    assert breaker.should_skip(**key, now=now) is False


@pytest.mark.asyncio
async def test_client_side_invalid_output_does_not_open_the_breaker(monkeypatch):
    # The HTTP call succeeded, so the pair is reachable; unusable output is handled by the
    # chain, not by latching a breaker against a working endpoint.
    import json as _json

    from bot.services.llm.errors import AIInvalidJsonError

    _configure(monkeypatch, ["groq"], {"groq"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider(
                "groq",
                lambda name, model: ProviderResult(
                    provider=name, model=model, raw_content="not json", input_chars=1
                ),
            )
        }
    )

    async def _validate(result):
        try:
            return _json.loads(result.raw_content)
        except ValueError as error:
            raise AIInvalidJsonError(str(error), raw_content=result.raw_content) from error

    for _ in range(8):
        with pytest.raises(AIInvalidJsonError):
            await router.chat_completion(
                call_type="event_analysis",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=10,
                response_format=None,
                validate_response=_validate,
            )

    assert breaker.breaker_snapshot() == {}


def test_overlong_backoff_value_falls_back_instead_of_overflowing(monkeypatch, caplog):
    # A zero-count typo must not make `now + timedelta(...)` raise OverflowError: that call
    # runs inside the router's exception handler, so it would replace the real provider error
    # and abort the whole chain — disabling the resilience this module adds.
    import logging

    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("LLM_BREAKER_BACKOFF_SECONDS", "999999999999")
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        breaker.record_failure(**key, reason="provider_model_error", now=now)

    assert breaker.breaker_snapshot()[("event_analysis", "groq", "m")]["open_until"] == (
        now + timedelta(seconds=60)
    )
    assert any("LLM_BREAKER_BACKOFF_SECONDS" in r.getMessage() for r in caplog.records)


def test_half_open_probe_is_handed_out_to_only_one_caller():
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    for _ in range(5):
        breaker.record_failure(**key, reason="provider_model_error", now=now)

    elapsed = now + timedelta(seconds=61)
    assert breaker.should_skip(**key, now=elapsed) is False  # this caller probes
    assert breaker.should_skip(**key, now=elapsed) is True  # a racing caller still skips


def test_an_abandoned_probe_does_not_skip_the_pair_forever():
    # A probe consumed without reporting an outcome (e.g. intercepted by rate-limit backoff)
    # must not leave the triple skipped indefinitely.
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    for _ in range(5):
        breaker.record_failure(**key, reason="provider_model_error", now=now)
    breaker.should_skip(**key, now=now + timedelta(seconds=61))  # probe handed out, no outcome

    assert breaker.should_skip(**key, now=now + timedelta(seconds=120)) is True
    assert breaker.should_skip(**key, now=now + timedelta(seconds=700)) is False


@pytest.mark.asyncio
async def test_rate_limit_does_not_open_the_breaker_through_the_router(monkeypatch):
    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "2")
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = FakeProvider("groq", AIProviderRateLimitError("429", provider="groq", model="m"))
    cerebras = FakeProvider("cerebras", _ok)
    router = LLMRouter(registry={"groq": groq, "cerebras": cerebras})

    for _ in range(4):
        await _call(router)

    assert groq.calls == 4  # never skipped; rate limits use their own backoff registry
    assert breaker.breaker_snapshot() == {}


@pytest.mark.asyncio
async def test_success_resets_the_failure_count(monkeypatch):
    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "3")
    _configure(monkeypatch, ["groq"], {"groq"})
    state = {"fail": True}

    def _flaky(name, model):
        if state["fail"]:
            raise _error(404, "model_not_found")
        return _result(name, model)

    router = LLMRouter(registry={"groq": FakeProvider("groq", _flaky)})

    for _ in range(2):
        with pytest.raises(AllProvidersFailedError):
            await _call(router)
    state["fail"] = False
    await _call(router)

    assert breaker.breaker_snapshot() == {}

    # The counter restarted, so two more failures must not be enough to open it.
    state["fail"] = True
    for _ in range(2):
        with pytest.raises(AllProvidersFailedError):
            await _call(router)
    resolved_model = llm_config.model_for("groq", "event_analysis")
    snapshot = breaker.breaker_snapshot()[("event_analysis", "groq", resolved_model)]
    assert snapshot["consecutive_failures"] == 2
    assert snapshot["open_until"] is None


@pytest.mark.asyncio
async def test_every_provider_broken_reports_circuit_broken(monkeypatch):
    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "1")
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", _error(404, "model_not_found")),
            "cerebras": FakeProvider("cerebras", _error(404, "model_not_found")),
        }
    )

    with pytest.raises(AllProvidersFailedError):
        await _call(router)

    with pytest.raises(AllProvidersFailedError) as raised:
        await _call(router)
    assert "circuit-broken" in str(raised.value)
    assert raised.value.attempts == []


def test_breaker_can_be_disabled(monkeypatch):
    monkeypatch.setenv("LLM_BREAKER_ENABLED", "false")
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    for _ in range(20):
        breaker.record_failure(**key, reason="provider_model_error", now=now)

    assert breaker.should_skip(**key, now=now) is False


def test_invalid_backoff_schedule_falls_back_and_warns(monkeypatch, caplog):
    import logging

    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("LLM_BREAKER_BACKOFF_SECONDS", "sixty,later")
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    with caplog.at_level(logging.WARNING, logger="bot.services.llm.env"):
        breaker.record_failure(**key, reason="provider_model_error", now=now)

    assert any("LLM_BREAKER_BACKOFF_SECONDS" in r.getMessage() for r in caplog.records)
    assert breaker.breaker_snapshot()[("event_analysis", "groq", "m")]["open_until"] == (
        now + timedelta(seconds=60)
    )


@pytest.mark.asyncio
async def test_breaker_logs_open_half_open_and_close(monkeypatch, caplog):
    import logging

    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "1")
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    with caplog.at_level(logging.INFO, logger="bot.services.llm.breaker"):
        breaker.record_failure(**key, reason="provider_model_error", now=now)
        breaker.should_skip(**key, now=now + timedelta(seconds=61))
        breaker.record_success(**key)

    events = " ".join(r.getMessage() for r in caplog.records)
    assert "ops_event=llm_breaker_opened" in events
    assert "ops_event=llm_breaker_half_open" in events
    assert "ops_event=llm_breaker_closed" in events
    assert "backoff_seconds=60" in events


# --- evidence trail ---------------------------------------------------------------------


def test_circuit_broken_exhaustion_classifies_distinctly():
    # "every provider known-bad, waiting to probe" must not persist as a generic other_error:
    # that is the difference between a fresh failure and an outage already in progress.
    error = AllProvidersFailedError("all circuit-broken", circuit_broken=True)
    assert error.circuit_broken is True
    assert classify_ai_error_reason(error) == "provider_circuit_broken"


def test_ordinary_exhaustion_is_not_reported_as_circuit_broken():
    error = AllProvidersFailedError("all failed", attempts=["groq"])
    assert error.circuit_broken is False
    assert classify_ai_error_reason(error) != "provider_circuit_broken"


@pytest.mark.asyncio
async def test_skipped_provider_still_writes_a_usage_log_row(monkeypatch):
    # Without this row a broken provider stops appearing in llm_usage_logs once its breaker
    # opens, so the evidence of an ongoing outage fades out a few cycles after it starts.
    from bot.services.llm import router as router_module

    written = []

    async def _capture(**kwargs):
        written.append(kwargs)
        return None

    monkeypatch.setattr(router_module, "write_llm_usage_log", _capture)
    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "1")
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", _error(404, "model_not_found")),
            "cerebras": FakeProvider("cerebras", _ok),
        }
    )

    await _call(router)
    assert written == []  # nothing skipped yet: groq was actually attempted

    await _call(router)

    assert len(written) == 1
    row = written[0]
    assert row["provider"] == "groq"
    assert row["call_type"] == "event_analysis"
    assert row["status"] == "skipped_due_to_circuit_breaker"
    assert row["error_reason"] == "provider_circuit_broken"
    assert row["input_chars"] is not None


@pytest.mark.asyncio
async def test_mixed_skip_and_attempt_reports_only_attempted_providers(monkeypatch):
    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "1")
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    router = LLMRouter(
        registry={
            "groq": FakeProvider("groq", _error(404, "model_not_found")),
            "cerebras": FakeProvider("cerebras", _error(500, "server error")),
        }
    )

    with pytest.raises(AllProvidersFailedError):
        await _call(router)  # opens groq's breaker

    with pytest.raises(AllProvidersFailedError) as raised:
        await _call(router)

    # groq was skipped, cerebras was really attempted: the message must not claim otherwise.
    assert raised.value.attempts == ["cerebras"]
    assert raised.value.circuit_broken is False
    assert "circuit-broken" not in str(raised.value)


@pytest.mark.asyncio
async def test_auth_error_opens_the_breaker_through_the_router(monkeypatch):
    # auth_error and config_missing are counted alongside provider_model_error; only the
    # latter was previously exercised end-to-end.
    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "2")
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = FakeProvider("groq", _error(401, "invalid api key"))
    router = LLMRouter(registry={"groq": groq, "cerebras": FakeProvider("cerebras", _ok)})

    for _ in range(3):
        await _call(router)

    assert groq.calls == 2  # attempted twice, then skipped


def test_rate_limit_backoff_returns_an_unspent_probe():
    # A probe intercepted by the provider's own rate-limit backoff never made an HTTP call, so
    # it proves nothing. Consuming it would silently replace the configured backoff schedule
    # with the half-open staleness timeout and stop the interval from widening.
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    key = {"call_type": "event_analysis", "provider": "groq", "model": "m"}

    for _ in range(5):
        breaker.record_failure(**key, reason="provider_model_error", now=now)

    elapsed = now + timedelta(seconds=61)
    assert breaker.should_skip(**key, now=elapsed) is False  # probe handed out
    breaker.record_not_attempted(**key, now=elapsed)

    snapshot = breaker.breaker_snapshot()[("event_analysis", "groq", "m")]
    assert snapshot["half_open"] is False
    # Same interval re-armed, not widened: nothing was learned.
    assert snapshot["open_until"] == elapsed + timedelta(seconds=60)
    assert breaker.should_skip(**key, now=elapsed + timedelta(seconds=30)) is True


@pytest.mark.asyncio
async def test_rate_limit_backoff_during_a_probe_does_not_spend_it(monkeypatch):
    from datetime import datetime as _dt

    from bot.services.llm.errors import LLMRateLimitBackoffActive

    monkeypatch.setenv("LLM_BREAKER_FAILURE_THRESHOLD", "1")
    _configure(monkeypatch, ["groq", "cerebras"], {"groq", "cerebras"})
    groq = FakeProvider("groq", _error(404, "model_not_found"))
    router = LLMRouter(registry={"groq": groq, "cerebras": FakeProvider("cerebras", _ok)})

    await _call(router)  # opens groq's breaker
    model = llm_config.model_for("groq", "event_analysis")
    key = ("event_analysis", "groq", model)

    # Force the probe, then have the provider refuse before any HTTP call.
    breaker.should_skip(call_type="event_analysis", provider="groq", model=model)
    groq._behavior = LLMRateLimitBackoffActive(
        provider="groq", model=model, limited_until=_dt.now(timezone.utc)
    )
    await _call(router)

    assert breaker.breaker_snapshot()[key]["half_open"] is False
    assert breaker.breaker_snapshot()[key]["open_until"] is not None


def test_json_validation_is_still_detected_through_the_router_wrapper():
    # Once json_validate_failed became fallback-eligible the error reaches callers wrapped in
    # AllProvidersFailedError. Callers that ask "was this a JSON-mode failure?" must still get
    # a yes, or the documented GROQ_JSON_MODE_RETRY_PLAIN path silently becomes unreachable.
    from bot.services.llm.telemetry import is_json_validation_error, usage_status_for_error

    inner = _error(400, "json_validate_failed", code="json_validate_failed")
    wrapper = AllProvidersFailedError("All providers failed", last_error=inner)

    assert is_json_validation_error(inner) is True
    assert is_json_validation_error(wrapper) is True
    assert usage_status_for_error(inner) == "schema_error"


def test_a_request_defect_mentioning_a_missing_field_is_not_a_model_error():
    # Guard against the generic phrases: "does not exist" also appears in genuine request
    # defects, which must stay terminal rather than being retried across the whole chain.
    assert classify_ai_error_reason(
        _error(400, "parameter 'foo' does not exist")
    ) != "provider_model_error"
