from types import SimpleNamespace

from bot.runtime import scheduler
from bot.runtime.telegram_app import register_handlers
from main import register_handlers as legacy_register_handlers


def test_main_reexports_telegram_handler_registration():
    assert legacy_register_handlers is register_handlers


def test_runtime_scheduler_delegates_all_startup_jobs(monkeypatch):
    calls = []
    app = SimpleNamespace()

    monkeypatch.setattr(
        scheduler,
        "schedule_automatic_market_check",
        lambda app_arg, interval: calls.append(("market", app_arg, interval)),
    )
    monkeypatch.setattr(
        scheduler,
        "schedule_market_heartbeat_generation",
        lambda app_arg: calls.append(("heartbeat", app_arg)),
    )
    monkeypatch.setattr(
        scheduler,
        "schedule_report_cache_generation",
        lambda app_arg: calls.append(("reports", app_arg)),
    )
    monkeypatch.setattr(
        scheduler,
        "schedule_seen_news_cleanup",
        lambda app_arg: calls.append(("seen_news", app_arg)),
    )

    scheduler.schedule_runtime_jobs(app, automatic_check_interval_seconds=300)

    assert calls == [
        ("market", app, 300),
        ("heartbeat", app),
        ("reports", app),
        ("seen_news", app),
    ]
