from telegram.ext import Application

from bot.application.alert_processing import (
    schedule_automatic_market_check,
    schedule_market_heartbeat_generation,
    schedule_seen_news_cleanup,
)
from bot.application.report_processing import schedule_report_cache_generation
from bot.application.trial_lifecycle import schedule_premium_trial_expiry
from bot.config import ENABLE_NEWS_INTELLIGENCE
from bot.news import ingest_news_job
from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log


def schedule_runtime_jobs(app: Application, *, automatic_check_interval_seconds: int) -> None:
    schedule_automatic_market_check(app, automatic_check_interval_seconds)
    schedule_market_heartbeat_generation(app)
    schedule_report_cache_generation(app)
    schedule_news_ingestion(app)
    schedule_seen_news_cleanup(app)
    schedule_premium_trial_expiry(app)


def schedule_news_ingestion(app: Application) -> None:
    """Keep persisted news current independently of report cache/market alert cadence."""
    for job in app.job_queue.get_jobs_by_name("news_ingestion"):
        job.schedule_removal()
    if not (DB_ENABLED and DB_SESSION_LOCAL and ENABLE_NEWS_INTELLIGENCE):
        log("ops_event=news_ingestion_scheduled enabled=false")
        return
    app.job_queue.run_repeating(
        ingest_news_job,
        interval=3600,
        first=240,
        name="news_ingestion",
        job_kwargs={"max_instances": 1, "coalesce": True, "misfire_grace_time": 180},
    )
    log("ops_event=news_ingestion_scheduled enabled=true interval_seconds=3600")
