import pytest

from bot import alerts


def test_news_trace_counts_actual_payload_without_exposing_contents(caplog):
    candidates = [
        {
            "news_id": "n1",
            "title": "Crypto market falls private marker",
            "url": "https://example.com/x",
        },
        {"news_id": "n2", "title": "Unrelated technology private marker"},
    ]
    payload = {
        "plain_text": "Related context:\n• Private title\n\nPossible action:\nWatch.",
        "html_text": (
            '<b>Related context</b>\n• <a href="https://example.com/x">Private title</a>'
            "\n\n<b>Possible action</b>"
        ),
    }
    with caplog.at_level("INFO", logger="bot.alerts"):
        alerts._log_event_news_trace(
            symbol="SOL",
            context_fingerprint="a" * 64,
            analysis_id=23,
            candidates=candidates,
            shortlist_count=2,
            selected_ids=["n1", "n2", "n3"],
            alert_payload=payload,
            reused=False,
        )
    assert "mapped_count=2" in caplog.text
    assert "missing_id_count=1" in caplog.text
    assert "irrelevant_count=1" in caplog.text
    assert "rendered_count=1" in caplog.text
    assert "linked_count=1" in caplog.text
    assert "private" not in caplog.text.lower()
    assert "example.com" not in caplog.text


def test_news_trace_allows_empty_selection(caplog):
    payload = {
        "plain_text": (
            "Related context:\nNo relevant news linked to this market move."
            "\n\nPossible action:\nWatch."
        ),
        "html_text": (
            "<b>Related context</b>\nNo relevant news linked to this market move."
            "\n\n<b>Possible action</b>"
        ),
    }
    with caplog.at_level("INFO", logger="bot.alerts"):
        alerts._log_event_news_trace(
            symbol="SOL",
            context_fingerprint="a" * 64,
            analysis_id=23,
            candidates=[],
            shortlist_count=0,
            selected_ids=[],
            alert_payload=payload,
            reused=True,
        )
    assert "selected_count=0" in caplog.text
    assert "rendered_count=0" in caplog.text
    assert "linked_count=0" in caplog.text


def test_render_sees_full_shortlist_but_significance_stays_bounded():
    from bot.services.ai_agent_groq import (
        _event_alert_render_prompt_payload,
        _event_significance_prompt_payload,
    )

    payload = {
        "symbol": "SOL",
        "market": {},
        "news": [
            {"news_id": f"n{i}", "title": f"Story {i}", "source": "Source"} for i in range(1, 5)
        ],
    }
    assert len(_event_significance_prompt_payload(payload)["n"]) == 2
    assert [item["i"] for item in _event_alert_render_prompt_payload(payload)["n"]] == [
        "n1",
        "n2",
        "n3",
        "n4",
    ]


def test_render_prompt_distinguishes_macro_context_from_causation():
    from bot.services.ai_agent_groq import build_event_alert_render_prompt

    prompt = build_event_alert_render_prompt({"symbol": "SOL", "market": {}})
    assert "evidence of broad crypto market impact" in prompt
    assert "Do not invent causal connections" in prompt


@pytest.mark.asyncio
@pytest.mark.parametrize("selected_ids", [["n1"], []])
async def test_synthetic_stage2_selection_reaches_shared_telegram_payload(
    monkeypatch, selected_ids, caplog
):
    from unittest.mock import AsyncMock

    article = {
        "title": "Bitcoin and Ether fall as US election results unsettle risk assets",
        "source": "News source",
        "url": "https://example.org/market",
    }
    candidates = alerts._format_candidate_news([article], symbol="sol")
    payload = {
        "symbol": "SOL",
        "timestamp_utc": "2026-11-05T12:00:00+00:00",
        "market": {
            "price": 100,
            "analysed_window_minutes": 180,
            "chg_window_percent": -2,
            "chg24h_percent": -3,
            "snapshots": [{"m": -180, "p": 102}, {"m": 0, "p": 100}],
        },
        "last_msg": {"time": None, "price": None},
        "news": alerts._compact_event_analysis_news(candidates),
    }
    significance = {
        "symbol": "SOL",
        "should_alert": True,
        "confidence": "high",
        "materiality": "material",
        "novelty": "new",
        "reason_code": "unusual_move",
    }
    render = {
        "message_body": "The current observations show a lower short-term range.",
        "possible_action": "The next observation may clarify whether the move continues.",
        "related_news_ids": selected_ids,
    }

    async def render_model(input_payload, *, schema_check):
        from bot.services.llm.errors import AISchemaValidationError

        with pytest.raises(AISchemaValidationError):
            schema_check({**render, "related_news_ids": ["n999"]})
        schema_check(render)
        return "synthetic", render

    monkeypatch.setattr(
        alerts, "ask_event_significance_raw", AsyncMock(return_value=("synthetic", significance))
    )
    monkeypatch.setattr(alerts, "ask_event_alert_render_raw", render_model)
    monkeypatch.setattr(alerts, "_save_event_alert_render_outcome", AsyncMock())
    save = AsyncMock(return_value=123)
    monkeypatch.setattr(alerts, "_save_event_analysis_attempt", save)
    monkeypatch.setattr(alerts, "_record_alert_delivery_outcome", AsyncMock())
    monkeypatch.setattr(alerts, "_get_previous_event_alert_id", AsyncMock(return_value=None))
    with caplog.at_level("INFO", logger="bot.alerts"):
        decision, analysis_id = await alerts._create_event_analysis_decision(payload)
    assert "stage=shared_payload_ready" not in caplog.text
    assert analysis_id == 123
    assert decision.related_news_ids == selected_ids
    assert save.await_args.kwargs["decision"].related_news_ids == selected_ids
    mapped = alerts._related_news_by_id(candidates, selected_ids, symbol="SOL")
    output = alerts._build_event_alert_payload(
        decision=decision, input_payload=payload, related_news=mapped
    )
    if selected_ids:
        assert 'href="https://example.org/market"' in output["rich_html"]
    else:
        assert "No relevant news linked" in output["plain_text"]


def test_news_trace_distinguishes_presentation_cap_from_relevance(caplog):
    candidates = [{"news_id": f"n{i}", "title": "Crypto market falls"} for i in range(1, 6)]
    payload = {
        "plain_text": "Related context:\n\u2022 A\n\u2022 B\n\u2022 C\n\nPossible action:",
        "html_text": '<b>Related context</b>\n<a href="a">A</a>\n<a href="b">B</a>'
        '\n<a href="c">C</a>\n\n<b>Possible action</b>',
    }
    with caplog.at_level("INFO", logger="bot.alerts"):
        alerts._log_event_news_trace(
            symbol="SOL",
            context_fingerprint="a" * 64,
            analysis_id=23,
            candidates=candidates,
            shortlist_count=5,
            selected_ids=[f"n{i}" for i in range(1, 6)],
            alert_payload=payload,
            reused=False,
        )
    assert "irrelevant_count=0 relevance_kept_count=5 presentation_cap_count=2" in caplog.text
    assert "formatting_drop_count=0 rendered_count=3 linked_count=3" in caplog.text


@pytest.mark.asyncio
async def test_reuse_translates_selected_id_before_trace(monkeypatch, caplog):
    import json
    from contextlib import asynccontextmanager
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    article = {
        "title": "Crypto prices fall after election results",
        "source": "Source",
        "url": "https://example.org/news",
    }
    stored = {**article, "news_id": "n1"}
    current = {**article, "news_id": "n2"}
    market = {
        "price": 100,
        "analysed_window_minutes": 180,
        "chg_window_percent": -2,
        "chg24h_percent": -3,
    }
    payload = {
        "symbol": "SOL",
        "timestamp_utc": "2026-11-05T12:00:00+00:00",
        "market": market,
        "news": [current],
    }
    analysis = SimpleNamespace(
        id=11,
        symbol="SOL",
        title="SOL market move",
        message_body="The current observations show a lower short-term range.",
        possible_action="The next observation may clarify whether the move continues.",
        urgency="normal",
        confidence="high",
        related_news_ids='["n1"]',
        raw_input_json=json.dumps({**payload, "news": [stored]}),
        event_key="sol_market_move",
    )
    market_event = SimpleNamespace(
        id=7, event_instance_key="sol:instance", event_key="sol_market_move"
    )

    @asynccontextmanager
    async def fake_session():
        yield object()

    monkeypatch.setattr(alerts, "DB_ENABLED", True)
    monkeypatch.setattr(alerts, "DB_SESSION_LOCAL", lambda: fake_session())
    monkeypatch.setattr(
        alerts,
        "get_reusable_event_analysis_candidates",
        AsyncMock(return_value=[(market_event, analysis)]),
    )
    reused = await alerts._get_reusable_event_analysis_by_context(payload, candidate_news=[current])
    assert reused is not None
    assert reused.decision.related_news_ids == ["n2"]
    with caplog.at_level("INFO", logger="bot.alerts"):
        alerts._log_event_news_trace(
            symbol="SOL",
            context_fingerprint="a" * 64,
            analysis_id=11,
            candidates=[current],
            shortlist_count=1,
            selected_ids=reused.decision.related_news_ids,
            alert_payload=reused.alert_payload,
            reused=True,
        )
    assert "reused=True" in caplog.text
    assert "selected_positions=['n2']" in caplog.text
    assert "mapped_count=1" in caplog.text
    assert "linked_count=1" in caplog.text
