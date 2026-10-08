from types import SimpleNamespace

import bot.alerts as alerts
import bot.services.ai_agent_groq as ai_agent_groq


def test_significance_prompt_defaults_to_no_alert_and_requires_new_significance():
    payload = {
        "symbol": "GRAM",
        "market": {
            "analysed_window_minutes": 180,
            "chg_window_percent": 1.11,
            "chg24h_percent": 3.2,
            "relative_window_percentile_30d": 97.0,
            "relative_24h_percentile_30d": 99.0,
        },
        "news": [],
    }
    prompt = ai_agent_groq.build_event_significance_prompt(payload).lower()
    assert "default=>no alert" in prompt
    assert "q1 materiality" in prompt
    assert "q2 novelty" in prompt
    assert "q3 should_alert" in prompt
    assert "large c24/p24" in prompt
    assert "previous/recent events can only reduce novelty" in prompt
    assert "only after q1/q2/q3 choose reason_code" in prompt
    assert "no fixed numeric cutoff" in prompt


def test_report_scheduler_check_interval_fits_refresh_grace():
    assert alerts.REPORT_CACHE_CHECK_INTERVAL_SECONDS <= 1800

    class Queue:
        def __init__(self):
            self.jobs = []
        def get_jobs_by_name(self, name):
            return []
        def run_repeating(self, callback, **kwargs):
            self.jobs.append(SimpleNamespace(callback=callback, **kwargs))

    queue = Queue()
    alerts.schedule_report_cache_generation(SimpleNamespace(job_queue=queue))
    assert len(queue.jobs) == 2
    assert all(job.interval <= 1800 for job in queue.jobs)
