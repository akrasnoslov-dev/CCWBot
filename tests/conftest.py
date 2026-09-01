import os
import socket

os.environ.setdefault("PREMIUM_MONTHLY_STARS", "199")

# --- Test network safety net -------------------------------------------------------------------
# Block real outbound network connections during the whole test suite so no test can ever call a
# real service: LLM providers (Groq/Gemini/Mistral), CoinGecko, Telegram, or an RSS host.
# An accidental real call would otherwise hang CI (there is no fast failure) instead of failing
# loudly. Everything external in the bot must be mocked in tests. Loopback is allowed so the
# Alembic/PostgreSQL migration tests and any local sockets keep working. This intercepts DNS
# resolution, which every real outbound connection performs.
_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "::"}
_real_getaddrinfo = socket.getaddrinfo


def _is_loopback(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    host = str(host)
    return host in _ALLOWED_HOSTS or host.startswith("127.")


def _guarded_getaddrinfo(host, *args, **kwargs):
    if not _is_loopback(host):
        raise RuntimeError(
            f"Blocked real network access to {host!r} during tests. External calls "
            "(LLM providers, CoinGecko, Telegram, RSS) must be mocked, not made for real."
        )
    return _real_getaddrinfo(host, *args, **kwargs)


socket.getaddrinfo = _guarded_getaddrinfo


# --- LLM circuit-breaker isolation -------------------------------------------------------------
# breaker state is process-global and is written by every test that drives the router, not only
# by the breaker tests. Without a session-wide reset a failure recorded in one test file leaks
# into another and silently changes which provider the router picks — e.g. setting
# LLM_BREAKER_FAILURE_THRESHOLD=1 locally (a documented variable) turned unrelated router tests
# red. Reset per test, and neutralise the tuning variables so a developer's .env cannot alter
# test outcomes.
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_llm_breaker_state(monkeypatch):
    from bot.services.llm import breaker

    for name in (
        "LLM_BREAKER_ENABLED",
        "LLM_BREAKER_FAILURE_THRESHOLD",
        "LLM_BREAKER_BACKOFF_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    breaker.reset_breakers()
    yield
    breaker.reset_breakers()
