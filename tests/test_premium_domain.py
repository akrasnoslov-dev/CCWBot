from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bot.domain.premium import (
    can_deliver_market_heartbeat_now,
    get_effective_market_heartbeat_frequency_seconds,
    is_coin_unlocked_for_user,
    is_user_premium_active,
)
from bot.domain.supported_coins import is_symbol_free


def make_user(active_until=None, frequency=21600):
    return SimpleNamespace(
        alert_frequency_seconds=frequency,
        premium_subscription=SimpleNamespace(active_until=active_until)
        if active_until is not None
        else None,
    )


def test_is_symbol_free_only_btc():
    assert is_symbol_free("btc") is True
    assert is_symbol_free("eth") is False


def test_is_user_premium_active_uses_active_until():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    assert is_user_premium_active(SimpleNamespace(active_until=now + timedelta(days=1)), now)
    assert not is_user_premium_active(SimpleNamespace(active_until=now), now)
    assert not is_user_premium_active(SimpleNamespace(active_until=now - timedelta(seconds=1)), now)
    assert not is_user_premium_active(SimpleNamespace(active_until=None), now)


def test_coin_unlock_rules():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    free_user = make_user()
    premium_user = make_user(active_until=now + timedelta(days=1))

    assert is_coin_unlocked_for_user(free_user, "btc", now)
    assert not is_coin_unlocked_for_user(free_user, "eth", now)
    assert is_coin_unlocked_for_user(premium_user, "eth", now)


def test_effective_market_heartbeat_frequency_rules():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    assert get_effective_market_heartbeat_frequency_seconds(make_user(frequency=3600), now) == 21600
    assert (
        get_effective_market_heartbeat_frequency_seconds(
            make_user(active_until=now + timedelta(days=1), frequency=3600),
            now,
        )
        == 3600
    )
    assert (
        get_effective_market_heartbeat_frequency_seconds(
            make_user(active_until=now + timedelta(days=1), frequency=123),
            now,
        )
        == 21600
    )
    assert (
        get_effective_market_heartbeat_frequency_seconds(
            make_user(active_until=now - timedelta(days=1), frequency=3600),
            now,
        )
        == 21600
    )


def test_market_heartbeat_delivery_uses_unlock_and_frequency():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    premium_user = make_user(active_until=now + timedelta(days=1), frequency=3600)
    free_user = make_user()

    assert can_deliver_market_heartbeat_now(premium_user, "eth", now, None)
    assert can_deliver_market_heartbeat_now(
        premium_user, "eth", now, now - timedelta(seconds=3600)
    )
    assert not can_deliver_market_heartbeat_now(
        premium_user, "eth", now, now - timedelta(seconds=3599)
    )
    assert not can_deliver_market_heartbeat_now(free_user, "eth", now, None)
    assert can_deliver_market_heartbeat_now(
        free_user, "btc", now, now - timedelta(seconds=21600)
    )
