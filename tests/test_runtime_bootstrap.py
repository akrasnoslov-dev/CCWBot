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
