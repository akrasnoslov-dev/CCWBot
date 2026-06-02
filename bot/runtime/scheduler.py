from telegram.ext import Application

from bot.application.alert_processing import (
    schedule_automatic_market_check,
    schedule_market_heartbeat_generation,
    schedule_seen_news_cleanup,
)
from bot.application.report_processing import schedule_report_cache_generation


def schedule_runtime_jobs(app: Application, *, automatic_check_interval_seconds: int) -> None:
    schedule_automatic_market_check(app, automatic_check_interval_seconds)
    schedule_market_heartbeat_generation(app)
    schedule_report_cache_generation(app)
    schedule_seen_news_cleanup(app)
