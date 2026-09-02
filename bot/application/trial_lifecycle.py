"""Independent scheduling for durable Premium-trial lifecycle transitions."""

from telegram.ext import Application, ContextTypes

from bot.runtime import DB_ENABLED, DB_SESSION_LOCAL, log

TRIAL_EXPIRY_JOB_NAME = "premium_trial_expiry"
TRIAL_EXPIRY_CHECK_INTERVAL_SECONDS = 15 * 60


async def expire_due_premium_trials(session):
    """Lazy import keeps the scheduler independent of database compatibility exports."""
    from bot.db.premium import expire_due_premium_trials as expire_due

    return await expire_due(session)


async def process_due_trial_expiries(_: ContextTypes.DEFAULT_TYPE) -> None:
    """Record due expiry transitions without coupling them to alert processing."""
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return
    try:
        async with DB_SESSION_LOCAL() as session:
            expired = await expire_due_premium_trials(session)
        if expired:
            log(f"ops_event=premium_trial_expired count={len(expired)}")
    except Exception as error:  # pragma: no cover - defensive scheduled-job isolation
        log(f"ops_event=premium_trial_expiry_failed error_class={type(error).__name__}")


def schedule_premium_trial_expiry(app: Application) -> None:
    for job in app.job_queue.get_jobs_by_name(TRIAL_EXPIRY_JOB_NAME):
        job.schedule_removal()
    if not (DB_ENABLED and DB_SESSION_LOCAL):
        return
    app.job_queue.run_repeating(
        process_due_trial_expiries,
        interval=TRIAL_EXPIRY_CHECK_INTERVAL_SECONDS,
        first=60,
        name=TRIAL_EXPIRY_JOB_NAME,
        job_kwargs={"max_instances": 1, "coalesce": True, "misfire_grace_time": 60},
    )
    log(
        "ops_event=premium_trial_expiry_scheduled "
        f"interval_seconds={TRIAL_EXPIRY_CHECK_INTERVAL_SECONDS}"
    )
