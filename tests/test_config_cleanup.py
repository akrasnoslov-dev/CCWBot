from pathlib import Path

import bot.config as config

ROOT = Path(__file__).resolve().parents[1]


def test_removed_price_move_env_does_not_remain_runtime_config():
    assert not hasattr(config, "PRICE_MOVE_ALERT_PERCENT")


def test_env_example_uses_semantic_event_alert_cooldown_not_legacy_threshold():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "PRICE_MOVE_ALERT_PERCENT" not in env_example
    assert "EVENT_ALERT_SEMANTIC_COOLDOWN_SECONDS=14400" in env_example
