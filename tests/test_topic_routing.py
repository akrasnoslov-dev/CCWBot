from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import bot.alerts as alerts
import bot.handlers as handlers
from bot.alerting.event_analysis import EVENT_ALERT_TYPE
from bot.topic_routing import CoinTopicRouteConfig


class FakeMessage:
    def __init__(self):
        self.replies: list[str] = []

    async def reply_text(self, text, **_kwargs):
        self.replies.append(text)


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)


def _command_update(user_id=1001):
    return SimpleNamespace(
        message=FakeMessage(),
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=2001),
    )


def _context(args):
    return SimpleNamespace(args=args, user_data={})


@pytest.mark.asyncio
async def test_settopic_accepts_supported_symbol_and_numeric_ids(monkeypatch):
    saved = AsyncMock()
    monkeypatch.setattr(handlers, "is_admin_update", AsyncMock(return_value=True))
    monkeypatch.setattr(handlers, "sync_user_from_update", AsyncMock())
    monkeypatch.setattr(handlers, "save_runtime_coin_topic_route", saved)
    update = _command_update()
    context = _context(["btc", "-1001234567890", "42"])

    await handlers.set_topic(update, context)

    saved.assert_awaited_once_with(
        symbol="btc",
        chat_id=-1001234567890,
        message_thread_id=42,
    )
    assert update.message.replies == ["BTC topic routing saved."]


@pytest.mark.asyncio
async def test_settopic_rejects_unsupported_symbol(monkeypatch):
    saved = AsyncMock()
    monkeypatch.setattr(handlers, "is_admin_update", AsyncMock(return_value=True))
    monkeypatch.setattr(handlers, "sync_user_from_update", AsyncMock())
    monkeypatch.setattr(handlers, "save_runtime_coin_topic_route", saved)
    update = _command_update()

    await handlers.set_topic(update, _context(["xrp", "-1001234567890", "42"]))

    saved.assert_not_awaited()
    assert update.message.replies == ["Unsupported symbol. Supported symbols: BTC, ETH, TON, SOL."]


@pytest.mark.asyncio
async def test_settopic_rejects_non_admin_user(monkeypatch):
    saved = AsyncMock()
    monkeypatch.setattr(handlers, "is_admin_update", AsyncMock(return_value=False))
    monkeypatch.setattr(handlers, "sync_user_from_update", AsyncMock())
    monkeypatch.setattr(handlers, "save_runtime_coin_topic_route", saved)
    update = _command_update()
    context = _context(["btc", "-1001234567890", "42"])

    await handlers.set_topic(update, context)

    saved.assert_not_awaited()
    assert update.message.replies == ["Sorry, only the bot admin can configure topics."]


@pytest.mark.asyncio
async def test_settopic_rejects_non_numeric_ids(monkeypatch):
    saved = AsyncMock()
    monkeypatch.setattr(handlers, "is_admin_update", AsyncMock(return_value=True))
    monkeypatch.setattr(handlers, "sync_user_from_update", AsyncMock())
    monkeypatch.setattr(handlers, "save_runtime_coin_topic_route", saved)
    update = _command_update()

    await handlers.set_topic(update, _context(["btc", "group", "topic"]))

    saved.assert_not_awaited()
    assert update.message.replies == ["Chat ID and topic ID must be whole numbers."]


@pytest.mark.asyncio
async def test_cleartopic_removes_routing(monkeypatch):
    cleared = AsyncMock(return_value=True)
    monkeypatch.setattr(handlers, "is_admin_update", AsyncMock(return_value=True))
    monkeypatch.setattr(handlers, "sync_user_from_update", AsyncMock())
    monkeypatch.setattr(handlers, "clear_runtime_coin_topic_route", cleared)
    update = _command_update()

    await handlers.clear_topic(update, _context(["btc"]))

    cleared.assert_awaited_once_with("btc")
    assert update.message.replies == ["BTC topic routing cleared."]


@pytest.mark.asyncio
async def test_topics_lists_configured_routes(monkeypatch):
    monkeypatch.setattr(handlers, "is_admin_update", AsyncMock(return_value=True))
    monkeypatch.setattr(handlers, "sync_user_from_update", AsyncMock())
    monkeypatch.setattr(
        handlers,
        "list_runtime_coin_topic_routes",
        AsyncMock(
            return_value=[
                CoinTopicRouteConfig(
                    symbol="btc",
                    chat_id=-1001234567890,
                    message_thread_id=42,
                ),
                CoinTopicRouteConfig(
                    symbol="eth",
                    chat_id=-1001234567890,
                    message_thread_id=43,
                ),
            ]
        ),
    )
    update = _command_update()

    await handlers.topics(update, _context([]))

    assert update.message.replies == [
        "Configured topics\n"
        "BTC: chat -1001234567890, topic 42\n"
        "ETH: chat -1001234567890, topic 43"
    ]


@pytest.mark.asyncio
async def test_event_alert_delivery_uses_message_thread_id_when_topic_configured(monkeypatch):
    bot = FakeBot()
    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", None)
    monkeypatch.setattr(
        alerts,
        "get_runtime_coin_topic_route",
        AsyncMock(
            return_value=CoinTopicRouteConfig(
                symbol="btc",
                chat_id=-1001234567890,
                message_thread_id=42,
            )
        ),
    )

    delivered = await alerts._deliver_market_event_alert(
        SimpleNamespace(bot=bot),
        symbol="btc",
        alert_payload={"plain_text": "BTC market alert\n\nNot financial advice."},
        market_event_id=10,
        event_ai_analysis_id=20,
        recipients=[alerts.AlertRecipient(chat_id=2001, user_id=1)],
        event_type=EVENT_ALERT_TYPE,
    )

    assert delivered is True
    assert bot.messages == [
        {"chat_id": 2001, "text": "BTC market alert\n\nNot financial advice."},
        {
            "chat_id": -1001234567890,
            "text": "BTC market alert\n\nNot financial advice.",
            "message_thread_id": 42,
        },
    ]


@pytest.mark.asyncio
async def test_event_alert_delivery_falls_back_without_topic(monkeypatch):
    bot = FakeBot()
    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", None)
    monkeypatch.setattr(alerts, "get_runtime_coin_topic_route", AsyncMock(return_value=None))

    delivered = await alerts._deliver_market_event_alert(
        SimpleNamespace(bot=bot),
        symbol="btc",
        alert_payload={"plain_text": "BTC market alert\n\nNot financial advice."},
        market_event_id=10,
        event_ai_analysis_id=20,
        recipients=[alerts.AlertRecipient(chat_id=2001, user_id=1)],
        event_type=EVENT_ALERT_TYPE,
    )

    assert delivered is True
    assert bot.messages == [
        {"chat_id": 2001, "text": "BTC market alert\n\nNot financial advice."}
    ]


@pytest.mark.asyncio
async def test_delivery_loop_does_not_call_llm_per_recipient(monkeypatch):
    bot = FakeBot()
    ask_event_analysis_raw = AsyncMock()
    monkeypatch.setattr(alerts, "DB_ENABLED", False)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", None)
    monkeypatch.setattr(alerts, "get_runtime_coin_topic_route", AsyncMock(return_value=None))
    monkeypatch.setattr(alerts, "ask_event_analysis_raw", ask_event_analysis_raw)

    await alerts._deliver_market_event_alert(
        SimpleNamespace(bot=bot),
        symbol="btc",
        alert_payload={"plain_text": "BTC market alert\n\nNot financial advice."},
        market_event_id=10,
        event_ai_analysis_id=20,
        recipients=[
            alerts.AlertRecipient(chat_id=2001, user_id=1),
            alerts.AlertRecipient(chat_id=2002, user_id=2),
        ],
        event_type=EVENT_ALERT_TYPE,
    )

    ask_event_analysis_raw.assert_not_awaited()
    assert len(bot.messages) == 2
