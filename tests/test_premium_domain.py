from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bot.domain.premium import (
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


def test_expired_active_lifecycle_status_does_not_grant_premium_access():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    subscription = SimpleNamespace(
        status="active",
        active_until=now - timedelta(seconds=1),
    )
    user = SimpleNamespace(
        premium_subscription=subscription,
        alert_frequency_seconds=3600,
    )

    assert not is_user_premium_active(subscription, now)
    assert not is_coin_unlocked_for_user(user, "eth", now)


def test_coin_unlock_rules():
    now = datetime(2026, 5, 11, tzinfo=timezone.utc)
    free_user = make_user()
    premium_user = make_user(active_until=now + timedelta(days=1))

    assert is_coin_unlocked_for_user(free_user, "btc", now)
    assert not is_coin_unlocked_for_user(free_user, "eth", now)
    assert is_coin_unlocked_for_user(premium_user, "eth", now)
