from types import SimpleNamespace

import pytest

import bot.alerts as alerts


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


@pytest.mark.asyncio
async def test_get_alert_recipients_deduplicates_active_db_users(monkeypatch):
    async def fake_get_active_users_with_alert_preferences(_session):
        return [
            SimpleNamespace(
                id=1,
                telegram_chat_id=100,
                premium_subscription=None,
                coin_subscriptions=[SimpleNamespace(symbol="btc", is_enabled=True)],
            ),
            SimpleNamespace(
                id=2,
                telegram_chat_id=100,
                premium_subscription=None,
                coin_subscriptions=[SimpleNamespace(symbol="btc", is_enabled=True)],
            ),
            SimpleNamespace(
                id=3,
                telegram_chat_id=200,
                premium_subscription=None,
                coin_subscriptions=[SimpleNamespace(symbol="btc", is_enabled=True)],
            ),
            SimpleNamespace(
                id=4,
                telegram_chat_id=None,
                premium_subscription=None,
                coin_subscriptions=[SimpleNamespace(symbol="btc", is_enabled=True)],
            ),
        ]

    async def fake_get_last_sent_alert_at(_session, *, user_id, symbol):
        return None

    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", lambda: FakeSession())
    monkeypatch.setattr(
        alerts,
        "get_active_users_with_alert_preferences",
        fake_get_active_users_with_alert_preferences,
    )
    monkeypatch.setattr(alerts, "get_last_sent_alert_at", fake_get_last_sent_alert_at)

    recipients = await alerts.get_alert_recipients("BTC", "price_movement")

    assert recipients == [
        alerts.AlertRecipient(chat_id=100, user_id=1),
        alerts.AlertRecipient(chat_id=200, user_id=3),
    ]


@pytest.mark.asyncio
async def test_get_alert_recipients_skips_non_btc_events(monkeypatch):
    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "TELEGRAM_CHAT_ID", "123")

    assert await alerts.get_alert_recipients("ETH", "price_movement") == []
    assert await alerts.get_alert_recipients("BTC", "weekly_report") == []


@pytest.mark.asyncio
async def test_get_alert_recipients_uses_configured_chat_without_db(monkeypatch):
    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "TELEGRAM_CHAT_ID", "123")

    assert await alerts.get_alert_recipients("BTC", "price_movement") == [
        alerts.AlertRecipient(chat_id=123)
    ]
