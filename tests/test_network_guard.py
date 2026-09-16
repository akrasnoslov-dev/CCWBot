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


def test_direct_external_ip_connection_is_blocked_without_a_network_attempt():
    client = socket.socket()
    try:
        with pytest.raises(RuntimeError, match="Blocked real network access"):
            client.connect(("8.8.8.8", 53))
    finally:
        client.close()


def test_direct_external_ip_connect_ex_and_udp_sendto_are_blocked():
    tcp_client = socket.socket()
    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        with pytest.raises(RuntimeError, match="Blocked real network access"):
            tcp_client.connect_ex(("8.8.8.8", 53))
        with pytest.raises(RuntimeError, match="Blocked real network access"):
            udp_client.sendto(b"test", ("8.8.8.8", 53))
    finally:
        tcp_client.close()
        udp_client.close()
