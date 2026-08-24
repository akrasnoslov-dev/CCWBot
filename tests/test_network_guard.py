"""Guards the test-suite network safety net installed in tests/conftest.py.

If this ever regresses, an un-mocked real provider/HTTP call could hang CI instead of failing
fast, which is exactly what this net prevents.
"""

import socket

import pytest


def test_external_host_resolution_is_blocked():
    with pytest.raises(RuntimeError, match="Blocked real network access"):
        socket.getaddrinfo("api.groq.com", 443)


@pytest.mark.parametrize(
    "host",
    ["generativelanguage.googleapis.com", "api.mistral.ai"],
)
def test_fallback_provider_hosts_are_blocked(host):
    with pytest.raises(RuntimeError, match="Blocked real network access"):
        socket.getaddrinfo(host, 443)


def test_loopback_resolution_is_allowed():
    # Loopback must keep working so the Alembic/PostgreSQL migration tests can connect.
    assert socket.getaddrinfo("127.0.0.1", 80)
    assert socket.getaddrinfo("localhost", 80)
