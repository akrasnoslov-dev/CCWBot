import pytest

from bot.runtime import bootstrap


def test_validate_required_config_accepts_legacy_single_admin(monkeypatch):
    monkeypatch.setattr(bootstrap, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(bootstrap, "TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(bootstrap, "TELEGRAM_ADMIN_USER_IDS", (111111111,))

    bootstrap.validate_required_config()


def test_validate_required_config_accepts_multi_admin_list(monkeypatch):
    monkeypatch.setattr(bootstrap, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(bootstrap, "TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(bootstrap, "TELEGRAM_ADMIN_USER_IDS", (111111111, 222222222))

    bootstrap.validate_required_config()


def test_validate_required_config_rejects_missing_admins(monkeypatch):
    monkeypatch.setattr(bootstrap, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(bootstrap, "TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(bootstrap, "TELEGRAM_ADMIN_USER_IDS", ())

    with pytest.raises(ValueError, match="TELEGRAM_ADMIN_USER_ID or TELEGRAM_ADMIN_USER_IDS"):
        bootstrap.validate_required_config()


@pytest.mark.asyncio
async def test_initialize_runtime_runs_database_logging_and_cache_warmup_in_order(monkeypatch):
    calls = []

    async def record(name):
        calls.append(name)

    monkeypatch.setattr(bootstrap, "initialize_database", lambda: record("database"))
    monkeypatch.setattr(
        bootstrap,
        "apply_persisted_error_file_logging_state",
        lambda: record("error_file_logging"),
    )
    monkeypatch.setattr(bootstrap, "warm_up_price_cache", lambda: record("price_cache"))

    await bootstrap.initialize_runtime()

    assert calls == ["database", "error_file_logging", "price_cache"]
