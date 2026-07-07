from pathlib import Path

import bot.config as config

ROOT = Path(__file__).resolve().parents[1]


def test_removed_price_move_env_does_not_remain_runtime_config():
    assert not hasattr(config, "PRICE_MOVE_ALERT_PERCENT")


def test_env_example_uses_semantic_event_alert_cooldown_not_legacy_threshold():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "PRICE_MOVE_ALERT_PERCENT" not in env_example
    assert "EVENT_ALERT_SEMANTIC_COOLDOWN_SECONDS=14400" in env_example


def test_single_admin_user_id_parses_for_backward_compatibility():
    assert config.combine_telegram_admin_user_ids("111111111", None) == (111111111,)


def test_multi_admin_user_ids_parse_comma_list():
    assert config.combine_telegram_admin_user_ids(
        None, "111111111,222222222"
    ) == (111111111, 222222222)


def test_single_and_multi_admin_user_ids_are_combined_and_deduplicated():
    assert config.combine_telegram_admin_user_ids(
        "111111111", "222222222, 111111111"
    ) == (111111111, 222222222)


def test_admin_user_ids_ignore_empty_whitespace_and_invalid_values():
    assert config.combine_telegram_admin_user_ids(
        "not-a-user-id", " , 111111111, invalid, -12345, 0, 222222222, "
    ) == (111111111, 222222222)


def test_compose_bot_startup_does_not_run_migrations_automatically():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "command: python main.py" in compose
    assert 'command: sh -c "alembic upgrade head && exec python main.py"' not in compose
    assert "command: alembic upgrade head" in compose
