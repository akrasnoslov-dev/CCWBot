# Graph Report - CCWBot  (2026-10-29)

## Corpus Check
- 655 files · ~1,152,065 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 34 file(s) not represented in the graph (top: .toml 12, (none) 8, .csv 7)

## Summary
- 5816 nodes · 17184 edges · 233 communities (195 shown, 38 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1436 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9f4f33ad`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- json
- BundleWriter
- test_onboarding.py
- test_db_queries_and_detectors.py
- test_llm_breaker.py
- telemetry.py
- test_rich_market_report_delivery.py
- test_telegram_stars_payments.py
- common.py
- test_system_status.py
- alembic
- test_openai_costs.py
- bot/alerts.py
- test_groq_budget.py
- test_product_analytics.py
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- load_frozen
- bootstrap.py
- test_event_alert_postrelease_regressions.py
- replay_event_significance.py
- test_heartbeat_silence.py
- LlmUsageLog
- event_text.py
- properties
- test_event_analysis_cloudflare_schema.py
- system_status.py
- validate_market_report_output
- properties
- event_analysis.py
- ccw41_reviewer_c_audit.py
- detectors.py
- handlers/__init__.py
- admin.py
- test_report_cooldowns.py
- Provider fallback (redundancy)
- error_file_logging.py
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- users.py
- Observability Snippets
- select
- bot/news.py
- ProviderResult
- news_intelligence_service.py
- make_news_key
- log
- test_llm_rate_limit_backoff.py
- normalize_symbol
- AISchemaValidationError
- test_news_ingestion.py
- test_event_alert_render_reliability.py
- test_llm_outage_detectors.py
- manifest.json
- CCWBot Growth Strategy: 0 -> 1 Premium
- database.py
- price_service.py
- db/reports.py
- test_bundle_and_cli.py
- event_identity.py
- test_event_analysis_health.py
- schedule_report_cache_generation
- cli.py
- test_admin_cleanup.py
- User
- transient.py
- 0001_initial_schema.py
- validate_event_significance_output
- CCWBot
- decimal
- bot/health.py
- 0024_gram_symbol.py
- test_event_alert_composition_investigation.py
- test_agent_workflow_contract.py
- test_event_alert_delivery_quality_regressions.py
- test_news_intelligence_schema.py
- news_service.py
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- datetime
- canonicalize_event_key
- ccw15_prompt_pack.py
- CCW-20 paired final messages
- event_chart.py
- build_alert_evidence_payloads
- test_watchlist_ux.py
- collections_abc
- Context Audit Report
- LlmOperationOutcome
- watchlist.py
- utc_now
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- bot/config.py
- resolve_alert_recipient_outcomes
- test_event_alert_rich_chart_ux.py
- Ops-Agent Service
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- _fixture
- LLMJsonResult
- test_event_alert_chart_markers.py
- test_price_service.py
- Event Alert logic
- README.md
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
- db/prices.py
- Market Reports
- Release Checklist
- test-ci.md
- _AlertEvidenceFakeConnection
- CCWBot ChatGPT Project Instructions
- backup_postgres.sh
- application/__init__.py
- bot/__init__.py
- observability/__init__.py
- Product analytics
- unittest_mock
- automatic_price_check
- architecture-guardian.md
- code-quality.md
- db-migration-guardian.md
- devops-release.md
- market-pipeline.md
- test_ccw9_ccw10.py
- product-policy.md
- security-review.md
- telegram-stars-payments.md
- CCW-20 final Cloudflare Render A/B — 2026-10-26
- AGENTS.md
- agents/README.md
- codex_task_prompt_template.md
- Project Context
- db/premium.py
- FakeResponse
- TransientSessions
- RichDeliveryUncertain
- Development
- test_market_heartbeat.py
- os
- test_llm_config_budgets.py
- ChatGPT / Bridge / Codex Workflow
- _parse_json
- collectors/__init__.py
- ops_agent/__init__.py
- test_multicoin_alerts.py
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- test_db_collector_failure_is_isolated_and_later_collectors_continue
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: extra exports and benchmark
- pkgutil
- build_llm_messages
- reviewer-c-rubric.md
- What You Must Do When Invoked
- extraction-spec.md
- test_alembic_migrations.py
- test_rich_403_preserves_safe_blocked_classification_without_raw_errors
- CCW-41 exploratory Reviewer-C agreement/disagreement
- test_heartbeat_does_not_query_previous_event
- test_growth_analytics_migration.py
- bot/reports.py
- get_report_market_data_batch
- _StructuredRecordBuffer
- test_heartbeat_postgres.py
- 0003_premium_watchlist_foundation.py
- test_price_handlers.py
- FakeAsyncClient
- /graphify
- scope
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- 0008_database_comments.py
- CCW-43 — Evidence-based Event Analysis prompt redesign
- test_rich_confirmed_telegram_rejections
- test_report_llm_exhaustion_recovery.py
- P
- bot
- news_context.py
- 0025_llm_operation_correlation.py
- .__init__
- test_prod_diagnostic_fixes.py
- 0026_growth_analytics.py
- CCWBot Operational Report — Unverified (No Production Bundle)
- 0004_multicoin_delivery_idempotency.py
- 0005_telegram_stars_payments.py
- CCW-25 — Self-hosted LLM owner decision
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- CCWBot — blind owner disagreement-only replay
- 0007_unique_telegram_user_id.py
- Repository-backed Graphify
- CCW-25 research evidence
- 0009_error_file_logging_toggle.py
- operator_prompt.md
- onboarding.py
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- 0028_premium_trials.py
- 0030_event_alert_policy_cleanup.py
- README_RU.md
- 0031_onboarding_customize_event.py
- fresh200_luna_wait_start.sh
- openai_luna_wait_start.sh
- backfill_blocked_users.py
- build_review.py
- 0027_market_heartbeat_defaults.py
- _extract_ton_coin_data_from_simple_price
- _coingecko_headers
- NoopAsyncClient
- .__init__
- 0006_payment_recurring_metadata.py
- CCW20_FINAL_MESSAGE_BASELINE_20261026.md
- asyncio

## God Nodes (most connected - your core abstractions)
1. `select()` - 172 edges
2. `Period` - 115 edges
3. `Base` - 99 edges
4. `LLMRouter` - 98 edges
5. `normalize_symbol()` - 88 edges
6. `User` - 68 edges
7. `utc_now()` - 64 edges
8. `run_detectors()` - 64 edges
9. `EventAnalysisDecision` - 63 edges
10. `Alert` - 60 edges

## Surprising Connections (you probably didn't know these)
- `Event Alert chart reference markers (2026-10-26)` --references--> `price()`  [INFERRED]
  docs/alert_logic.md → bot/handlers/price.py
- `Which 4xx responses fall back` --references--> `AIInvalidJsonError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py
- `Event Alert Regression Evidence` --references--> `unknown()`  [INFERRED]
  docs/ops_agent_service.md → tests/test_event_alert_rich_chart_ux.py
- `Final Report Flow` --references--> `unknown()`  [INFERRED]
  docs/ops_agent_service.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (233 total, 38 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.14
Nodes (47): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), alert_analysis_result(), event_analysis_result(), factual_market_input() (+39 more)

### Community 1 - "json"
Cohesion: 0.02
Nodes (95): Ground-truth evidence and limitations, Versioned artifacts, _json_dumps(), Canonical JSON that writes Decimal market values without binary-float loss., build_event_analysis_prompt(), build_market_heartbeat_prompt(), build_market_report_prompt(), _event_significance_prompt_payload() (+87 more)

### Community 2 - "BundleWriter"
Cohesion: 0.14
Nodes (10): BundleWriter, Any, Path, Publish the manifest only after its complete JSON payload is on disk., write_json(), write_json_atomic(), write_protected_json(), write_text() (+2 more)

### Community 3 - "test_onboarding.py"
Cohesion: 0.20
Nodes (30): ProductEvent, UserCoinSubscription, Send a first-run BTC brief or a concise returning-user dashboard., send_start_experience(), inspect, build_session(), create_user(), FakeMessage (+22 more)

### Community 4 - "test_db_queries_and_detectors.py"
Cohesion: 0.04
Nodes (62): alembic_migration, alembic_operations, ops_agent_collectors, _alert_evidence_windows(), datetime, run_detectors(), Period, sqlite3 (+54 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.08
Nodes (71): _backoff_schedule(), breaker_snapshot(), _BreakerState, _failure_threshold(), is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics. (+63 more)

### Community 6 - "telemetry.py"
Cohesion: 0.05
Nodes (85): _create_market_heartbeat(), _validate(), Provider interface and the shared OpenAI-compatible provider implementation.…, BudgetLease, Conservative zero-cost Groq admission control, shared across all call types. A…, LLMRateLimitBackoffActive, Provider-agnostic LLM error types shared across the provider router. These were…, Raised when a provider/model is already in temporary rate-limit backoff. (+77 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.09
Nodes (42): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report(), market_report_change_chart() (+34 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.10
Nodes (54): Payment, build_premium_activation_keyboard(), build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date(), _get_payment_attr() (+46 more)

### Community 9 - "common.py"
Cohesion: 0.11
Nodes (27): Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, Edit a transient callback screen without exposing Telegram failures., Best-effort deletion of a user's slash command in a private chat., safe_delete_command_invocation(), safe_edit_callback_message(), _telegram_user_id(), handle_application_error() (+19 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.17
Nodes (48): build_admin_llm_diagnostics_text(), build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health., builtins, build_session_factory(), _event_analysis(), _final_failed_alert() (+40 more)

### Community 12 - "test_openai_costs.py"
Cohesion: 0.06
Nodes (84): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., _cost(), monthly_budget_usd(), OpenAIBudget, OpenAIBudgetExhausted, OpenAIBudgetLease, _positive_decimal_env() (+76 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.04
Nodes (77): bot_alerting, alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.… (+69 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.08
Nodes (31): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., _Charge, GroqBudget, GroqBudgetExhausted (+23 more)

### Community 15 - "test_product_analytics.py"
Cohesion: 0.06
Nodes (69): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+61 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.17
Nodes (33): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), BundleHasher, _content_fingerprints() (+25 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.12
Nodes (42): ask_event_analysis_raw(), _configure(), ContentProvider, _empty_report_news_context(), _grounded_alert(), _grounding_market(), _grounding_schema_check(), _install_report_inputs() (+34 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (81): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+73 more)

### Community 19 - "load_frozen"
Cohesion: 0.11
Nodes (37): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Read-only local check, importlib_util, random, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, CCW-29 fresh private holdout: collect real POST-200 market cases via…, choose() (+29 more)

### Community 20 - "bootstrap.py"
Cohesion: 0.11
Nodes (28): AbstractEventLoop, AppRunner, Application, register_bot_handlers(), start_health_server(), handle_health(), stop_health_server(), bot_runtime (+20 more)

### Community 21 - "test_event_alert_postrelease_regressions.py"
Cohesion: 0.10
Nodes (35): _build_exact_event_context_fingerprint(), build_event_significance_prompt(), _payload(), parametrize, test_ccw349_invalid_headline_does_not_hide_second_valid_headline(), test_ccw349_news_priority_changes_model_visible_context_and_fingerprint(), test_decimal_json_is_full_precision_json_number_not_float_or_string(), test_exact_context_does_not_reuse_the_ambiguous_change_field_contract() (+27 more)

### Community 22 - "replay_event_significance.py"
Cohesion: 0.09
Nodes (31): _groq_json_mode_enabled(), scripts, classify_replay_error(), effort_budget(), groq_significance_response_format(), live_report(), load_cases(), NonObjectSignificanceError (+23 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.15
Nodes (22): pytest_asyncio, fake_get_active_users_with_alert_preferences(), add_delivery(), asyncio, parametrize, test_cache_expiring_before_lock_acquisition_is_not_sent(), test_delayed_success_uses_completion_not_reservation(), test_event_resets_timer_during_generation_market_fetch() (+14 more)

### Community 24 - "LlmUsageLog"
Cohesion: 0.11
Nodes (34): LlmUsageLog, Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider… (+26 more)

### Community 25 - "event_text.py"
Cohesion: 0.05
Nodes (91): _action_price_levels_supported(), _action_without_negated_technical_levels(), compact_elapsed_since(), compact_event_alert_possible_action(), compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation() (+83 more)

### Community 26 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 27 - "test_event_analysis_cloudflare_schema.py"
Cohesion: 0.08
Nodes (34): ask_event_alert_render_raw(), ask_event_significance_raw(), ask_market_heartbeat_raw(), ask_market_report_raw(), ask_news_intelligence_raw(), _json_response_validator(), Return JSON mode and provider-specific schemas for verified model attempts., _structured_response_formats() (+26 more)

### Community 28 - "system_status.py"
Cohesion: 0.11
Nodes (39): _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, _container_started_at(), _delivery_failure_category(), _delivery_health() (+31 more)

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "event_analysis.py"
Cohesion: 0.15
Nodes (34): CanonicalEventKey, _claim_clause(), _claimed_percent(), _decimal_market_value(), _direction_for_claim(), _duration_minutes(), _duration_minutes_from_claim(), _elapsed_minutes() (+26 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.07
Nodes (72): audit(), positive_age_minutes(), ranking(), main(), _number(), _time(), _aggregate_markdown(), _cli() (+64 more)

### Community 33 - "detectors.py"
Cohesion: 0.11
Nodes (34): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+26 more)

### Community 34 - "handlers/__init__.py"
Cohesion: 0.15
Nodes (42): acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_error_logging_status_text(), chat_id(), error_logging_off(), error_logging_on() (+34 more)

### Community 35 - "admin.py"
Cohesion: 0.08
Nodes (64): _build_admin_llm_diagnostics_text(), _build_admin_openai_costs_text(), _build_admin_system_status_text(), _format_admin_alert_settings(), _llm_diagnostics_menu(), _premium_grant_usage_text(), _premium_revoke_usage_text(), InlineKeyboardMarkup (+56 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.18
Nodes (32): MarketReport, reports(), get_or_generate_report(), One shared refresh on old content; never fan out LLM/RSS per recipient., AsyncClock, build_session_factory(), _daily_message(), _empty_report_news_context() (+24 more)

### Community 37 - "Provider fallback (redundancy)"
Cohesion: 0.17
Nodes (11): Admin OpenAI Platform Costs monitoring (optional, read-only), Current Event Alert Luna-only policy (owner update 2026-10-29), Event Analysis timeout and operation budget, Groq free-tier admission control (Event Analysis), Historical CCW-20 Event Alert provider order (superseded), Historical Gemini 429 quota classification and backoff, LLM Usage Reporting, Ops-Agent LLM Usage Evidence (+3 more)

### Community 38 - "error_file_logging.py"
Cohesion: 0.08
Nodes (48): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., bot_observability, _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports() (+40 more)

### Community 39 - "LLMRouter"
Cohesion: 0.13
Nodes (65): AIInvalidJsonError, AIProviderRateLimitError, AllProvidersFailedError, RuntimeError, Raised when a provider refuses a request because the account is rate limited., Raised when the provider response is not valid JSON., Raised when every provider in the fallback chain has been exhausted.…, LLMRouter (+57 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.05
Nodes (77): EventAnalysisDecision, _event_input_hash(), _as_news_only_rejected_decision(), _build_event_alert_html_message(), _build_event_alert_payload(), _create_event_analysis_decision(), _decision_describes_market_event(), _decision_is_primarily_news_context() (+69 more)

### Community 42 - "users.py"
Cohesion: 0.14
Nodes (28): get_active_users_with_alert_preferences(), get_or_create_user(), get_user_by_telegram_chat_id(), get_user_role(), is_telegram_chat_delivery_enabled(), mark_user_bot_blocked(), AsyncSession, datetime (+20 more)

### Community 43 - "Observability Snippets"
Cohesion: 0.08
Nodes (29): consecutive_failures(), Output, Rules you enforce, What you review, Admin System Status, Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis (+21 more)

### Community 44 - "select"
Cohesion: 0.06
Nodes (91): attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery(), get_event_ai_analysis(), get_last_sent_alert(), get_last_sent_alert_at(), get_last_sent_event_alert_at_for_event_key() (+83 more)

### Community 45 - "bot/news.py"
Cohesion: 0.16
Nodes (29): _dedupe_report_news(), fetch_report_news_context(), within_window(), _has_report_news_identity(), _item_link(), _item_published_at(), _item_related_symbols(), _news_row_rank() (+21 more)

### Community 46 - "ProviderResult"
Cohesion: 0.14
Nodes (21): ABC, BaseProvider, ProviderResult, Normalized successful chat-completion result returned by every provider., Common interface for all LLM providers., True when this provider has all configuration required for an attempt., Run one chat completion and return a :class:`ProviderResult` on success.…, _configure() (+13 more)

### Community 47 - "news_intelligence_service.py"
Cohesion: 0.11
Nodes (31): _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text(), _dedup_hint_is_specific_to_title(), _dedup_terms() (+23 more)

### Community 48 - "make_news_key"
Cohesion: 0.09
Nodes (36): _collapse_whitespace(), make_news_key(), _normalize_news_link(), Normalize repeated spaces so keys stay stable across feed formatting., Return a stable URL string for news identity checks., Build a stable key for a news item. Links are preferred because RSS titles can…, SeenNews, cleanup_seen_news() (+28 more)

### Community 49 - "log"
Cohesion: 0.11
Nodes (29): _automatic_market_check_job_name(), _build_market_heartbeat_id(), cleanup_seen_news_job(), generate_market_heartbeats(), _is_fresh_heartbeat(), DEFAULT_TYPE, Compatibility wrapper for older imports; schedules the market-wide check., schedule_automatic_btc_check() (+21 more)

### Community 50 - "test_llm_rate_limit_backoff.py"
Cohesion: 0.09
Nodes (37): CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions…, get_provider(), get_provider(), OpenAI paid fallback, guarded by an explicit kill switch and durable budget., _default_registry(), get_llm_rate_limit_backoff() (+29 more)

### Community 51 - "normalize_symbol"
Cohesion: 0.06
Nodes (55): Escape all model/news wording; only safely link explicit HTTP(S) sources., _report_coin_icon_html(), _safe_rich_line(), _coin_name(), _build_event_alert_rich_html(), _build_market_heartbeat_html_message(), _build_market_heartbeat_payload(), _build_market_heartbeat_rich_html() (+47 more)

### Community 52 - "AISchemaValidationError"
Cohesion: 0.13
Nodes (26): _schema_check(), AISchemaValidationError, datetime, Exception, Raised when validated JSON does not match the expected schema. ``raw_content``…, call_render(), FakeProvider, good_render() (+18 more)

### Community 53 - "test_news_ingestion.py"
Cohesion: 0.12
Nodes (13): ingest_news_job(), Hourly market-wide RSS ingestion; never creates alerts or resolves recipients., email_utils, _entry(), _feed(), asyncio, datetime, Regression tests for the independent, bounded RSS ingestion path. (+5 more)

### Community 54 - "test_event_alert_render_reliability.py"
Cohesion: 0.24
Nodes (17): build_event_alert_render_prompt(), _payload(), asyncio, parametrize, Regression contracts for production Event Alert Render rejection categories.…, test_ccw20_render_copy_asks_for_meaningful_price_scenarios(), test_ccw20_render_prompt_missing_context_fails_closed(), test_flat_news_led_input_cannot_be_recovered_as_market_alert() (+9 more)

### Community 55 - "test_llm_outage_detectors.py"
Cohesion: 0.18
Nodes (24): _detector(), _evidence(), parametrize, Detectors and evidence quality for an LLM-side Event Analysis outage. Covers…, Mimic the collector: newest bucket first, each bucket capped by remaining…, _row(), _simulate_row_cap(), test_a_failure_storm_no_longer_starves_delivered_analyses_of_the_row_cap() (+16 more)

### Community 56 - "manifest.json"
Cohesion: 0.06
Nodes (35): batch_size, batches, path, sha256, case_count, cases, dataset_sha256, operator_prompt_sha256 (+27 more)

### Community 57 - "CCWBot Growth Strategy: 0 -> 1 Premium"
Cohesion: 0.15
Nodes (12): Acquisition limitation, CCWBot Growth Strategy: 0 -> 1 Premium, Change, Current comparable cohort, Decision rule, Experiment 1 - Premium-only onboarding selector, Handoff prompt for a new chat, Primary metric (+4 more)

### Community 58 - "database.py"
Cohesion: 0.05
Nodes (60): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), alembic_script, AppSettings, Base (+52 more)

### Community 59 - "price_service.py"
Cohesion: 0.17
Nodes (21): _build_stale_price_payload(), _coingecko_bool(), get_btc_market_data(), get_btc_price(), _get_cached_price(), get_coin_price(), _get_stale_cached_price(), _get_with_retry() (+13 more)

### Community 60 - "db/reports.py"
Cohesion: 0.32
Nodes (7): get_latest_market_report(), AsyncSession, datetime, Market report cache persistence. Belongs here: daily/weekly market report cache…, Save one cached market report generation attempt., Return the newest cached market report for a cadence., save_market_report()

### Community 61 - "test_bundle_and_cli.py"
Cohesion: 0.04
Nodes (91): ops_agent, BundleSizeLimitError, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., _add_failure(), build_parser(), _collect(), _collection_result() (+83 more)

### Community 62 - "event_identity.py"
Cohesion: 0.06
Nodes (52): AnalysedWindowReference, _build_event_instance_key(), _calculate_price_change(), _canonical_decimal_string(), _canonical_event_analysis_context(), _event_alert_change_label(), _event_analysis_datetime(), _event_analysis_news_age_hours() (+44 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.09
Nodes (28): _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, evaluate_state(), failure_escalation_threshold(), max_success_age_seconds(), datetime, In-process health signal for Event Analysis. Event Alerts were fully dead for…, Return ``(state, last_success_age_seconds)`` for the Event Analysis health… (+20 more)

### Community 64 - "schedule_report_cache_generation"
Cohesion: 0.15
Nodes (9): schedule_report_cache_generation(), Market report use-case entrypoints., generate_daily_report_cache_job(), generate_weekly_report_cache_job(), One recovery attempt after a scheduled failure; no recurring retry storm., _schedule_failed_report_retry(), test_report_cache_scheduler_replaces_weekly_direct_send_and_strong_signal(), test_report_scheduler_check_interval_fits_refresh_grace() (+1 more)

### Community 65 - "cli.py"
Cohesion: 0.06
Nodes (70): asyncio, httpx, sha256_file(), sha256_tree(), utc_stamp(), main(), _collect_alert_repetition_rows(), collect_db() (+62 more)

### Community 66 - "test_admin_cleanup.py"
Cohesion: 0.13
Nodes (17): bot_handlers, AsyncFalse, AsyncTrue, _callback_update(), _callback_values(), FakeMessage, FakeQuery, asyncio (+9 more)

### Community 67 - "User"
Cohesion: 0.19
Nodes (20): save_alert(), Alert, User, backfill_blocked_users_from_alerts(), Disable users with historical failed Telegram blocked-user delivery records., build_session_factory(), create_market_event(), create_user() (+12 more)

### Community 68 - "transient.py"
Cohesion: 0.15
Nodes (18): decorator(), wrapper(), enter_callback(), enter_command(), exit_request(), private_key(), Manage command-generated Telegram replies without touching passive…, Manual rich sends bypass PTB's normal send_message override. (+10 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "validate_event_significance_output"
Cohesion: 0.18
Nodes (15): empirical_absolute_move_percentile(), Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., validate_event_significance_output(), _significance_schema_check(), _payload(), parametrize, test_empirical_absolute_move_percentile_returns_none_for_insufficient_or_missing_data() (+7 more)

### Community 71 - "CCWBot"
Cohesion: 0.10
Nodes (20): Admin System Status, CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables (+12 more)

### Community 72 - "decimal"
Cohesion: 0.24
Nodes (11): calculate_price_change_percent(), is_cooldown_active(), datetime, Decimal, Core alert-rule helpers used by automatic market checks., Calculate a percent change without mixing binary floats and ``Decimal`` values., Return True while a previous alert is still inside the cooldown window., decimal (+3 more)

### Community 73 - "bot/health.py"
Cohesion: 0.10
Nodes (23): aiohttp, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any, datetime, Authoritative last successful Event Analysis time, or None when unavailable.…, Event Analysis health, as a nested block that never changes the top-level… (+15 more)

### Community 74 - "0024_gram_symbol.py"
Cohesion: 0.33
Nodes (13): _coerce_related_symbols(), _column_names(), downgrade(), _has_table_and_symbol(), _has_table_columns(), _merge_price_state(), _merge_user_coin_subscriptions(), _merge_user_symbol_alert_state() (+5 more)

### Community 75 - "test_event_alert_composition_investigation.py"
Cohesion: 0.20
Nodes (26): market_direction_claims_supported(), Check explicit period directions and the direction implied by relationships., market(), parametrize, Synthetic regressions for the October alert-composition investigation., test_alignment_fallback_names_direction_and_verified_size_relationship(), test_alignment_without_monotonic_snapshots_survives_compaction(), test_consistent_with_describes_alignment_not_snapshot_persistence() (+18 more)

### Community 76 - "test_agent_workflow_contract.py"
Cohesion: 0.19
Nodes (10): _adapter_path(), _agent_names(), _agent_paths(), _load_toml(), Path, test_agent_definitions_have_matching_claude_adapters(), test_agent_definitions_have_required_schema(), test_agent_routing_references_existing_agents() (+2 more)

### Community 77 - "test_event_alert_delivery_quality_regressions.py"
Cohesion: 0.17
Nodes (21): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, _event_alert_render_prompt_payload(), Return only a supported sign; no rounded or raw market numbers reach Render., _render_market_direction(), test_specific_next_observation_is_not_generic(), _decision(), _market() (+13 more)

### Community 78 - "test_news_intelligence_schema.py"
Cohesion: 0.27
Nodes (16): _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), asyncio, parametrize, Offline News Intelligence symbol-contract regression tests; no provider calls., _router() (+8 more)

### Community 79 - "news_service.py"
Cohesion: 0.13
Nodes (25): fetch_crypto_news(), headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Merge available feeds by publication age *before* applying the batch limit. A…, Low-cost, word-boundary-aware prefilter; not an alert decision. (+17 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.23
Nodes (38): NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap(), build_session(), FakeNewsLlm, asyncio (+30 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "datetime"
Cohesion: 0.04
Nodes (64): argparse, concurrent_futures, datetime, http_server, Owner-approved, local-only pinned benchmark dependencies., Audit only aggregated benchmark budget and next-call feasibility (no inference)., call_once(), classify() (+56 more)

### Community 83 - "canonicalize_event_key"
Cohesion: 0.11
Nodes (27): canonicalize_event_key(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal(), _fallback_event_key(), _is_random_event_key(), _normalize_event_key_text() (+19 more)

### Community 84 - "ccw15_prompt_pack.py"
Cohesion: 0.12
Nodes (21): hashfile(), main(), metrics(), Versioned private calibration reference from owner's 66 A/C re-decisions.…, write(), CCW-43 offline source verification, paired scoring, and restricted case error…, build_prompt(), check_production_parity() (+13 more)

### Community 85 - "CCW-20 paired final messages"
Cohesion: 0.09
Nodes (21): 10. ev_3c7f3da2e73e4b90 — ETH, 11. ev_7804adc277bd3333 — GRAM, 12. ev_345fc49db8255adf — GRAM, 13. ev_7b3325d2f2609480 — GRAM, 14. ev_1b39a518ede3c14f — GRAM, 15. ev_6500c5ad9f5364bc — GRAM, 16. ev_4bba21dd01bc8372 — SOL, 17. ev_1ea4cea05b78ed5c — SOL (+13 more)

### Community 86 - "event_chart.py"
Cohesion: 0.17
Nodes (15): _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw, Deterministic PNG chart from persisted, timestamped price observations only., Auditable reference value and its actual, not nominal, UTC timestamp., _reference_markers() (+7 more)

### Community 87 - "build_alert_evidence_payloads"
Cohesion: 0.27
Nodes (25): build_alert_evidence_payloads(), _numeric_context_json(), _period(), parametrize, _row(), test_alert_evidence_uses_hashes_without_raw_alert_text(), test_alert_quality_clean_delivered_event_alert_stays_clean(), test_alert_quality_detects_old_24h_label_in_delivered_event_alert() (+17 more)

### Community 88 - "test_watchlist_ux.py"
Cohesion: 0.06
Nodes (46): build_watchlist_keyboard(), build_subscribe_message(), build_watchlist_render(), AsyncFalse, AsyncNoop, AsyncTrue, build_session(), CallbackQuery (+38 more)

### Community 89 - "collections_abc"
Cohesion: 0.09
Nodes (4): downgrade(), _is_sqlite(), upgrade(), collections_abc

### Community 90 - "Context Audit Report"
Cohesion: 0.07
Nodes (18): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+10 more)

### Community 91 - "LlmOperationOutcome"
Cohesion: 0.28
Nodes (7): LlmOperationOutcome, AsyncSession, LLM usage telemetry persistence. Belongs here: saving and updating…, Update a usage row when downstream JSON schema validation fails., Persist one sanitized terminal outcome for a logical LLM operation., save_llm_operation_outcome(), update_llm_usage_log_status()

### Community 92 - "watchlist.py"
Cohesion: 0.12
Nodes (49): _as_aware_utc(), can_deliver_market_heartbeat_now(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active() (+41 more)

### Community 93 - "utc_now"
Cohesion: 0.18
Nodes (18): datetime, Return timezone-aware UTC timestamp., utc_now(), asyncio, test_admin_llm_summary_is_compact_and_provider_details_are_separate(), test_failed_format_refresh_keeps_current_cache_and_throttles_retries(), test_outdated_cached_report_refreshes_once_globally_and_reuses_result(), _cached_report() (+10 more)

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.17
Nodes (11): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Log pattern counting, News-candidate signal (+3 more)

### Community 96 - "bot/config.py"
Cohesion: 0.06
Nodes (34): combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids(), Centralized configuration loaded from environment variables. Notes about key…, is_admin_update(), is_admin_user(), Update, sync_user_from_update() (+26 more)

### Community 97 - "resolve_alert_recipient_outcomes"
Cohesion: 0.20
Nodes (13): get_alert_recipients(), Resolve eligible recipients once for one market event., Resolve recipients and preserve queryable reasons for filtered users., RecipientOutcome, resolve_alert_recipient_outcomes(), FakeSession, asyncio, test_event_alert_eligibility_ignores_market_heartbeat_preference() (+5 more)

### Community 98 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.17
Nodes (17): ChartResult, prepare_chart_points(), Never extrapolate over missing time or label a partial day as 24h., Event-specific references are opt-in; Heartbeat is exactly the old chart., render_price_chart(), _observations(), Event Alert UX, chart evidence and single-send fallback contracts., test_chart_accepts_normal_30_minute_scheduler_jitter_but_rejects_stale() (+9 more)

### Community 99 - "Ops-Agent Service"
Cohesion: 0.18
Nodes (10): Boundaries, Bundle Publication Contract, Event Alert Regression Evidence, Final Report Flow, Forensic Correlation Evidence, Local References, Ops-Agent Service, Production Access Model (+2 more)

### Community 100 - "_test_A_C_survey.js"
Cohesion: 0.10
Nodes (20): ref_assert, ref_fs, ref_path, ref_vm, assert, callbacks, ctx, el() (+12 more)

### Community 101 - "ccwbot-ops-agent-collect"
Cohesion: 0.40
Nodes (8): ccwbot-ops-agent-collect script, fail_preflight(), interrupted(), is_utc_timestamp(), reject(), usage(), validate_period(), write_receipt()

### Community 103 - "Dev Ops Guide"
Cohesion: 0.12
Nodes (15): Dependency updates, Deploying Ops-Agent Changes, Dev Ops Guide, Environment Rules, Future approved deployment and incident recovery, Legacy wrapper installation (historical, not routine after operator cutover), Manual Production Deploy (exceptional releases only), Non-interactive, least-privilege bot deploys (+7 more)

### Community 104 - "Event Alert benchmark and historical diagnostics (PR 1)"
Cohesion: 0.17
Nodes (8): Event Alert benchmark and historical diagnostics (PR 1), Historical investigation: evidence status, Next-stage dependency and acceptance, Technical baseline, not product-quality scores, Audit scope, CCW-47 — Owner decision: retain original Refined v2 (2026-10-26), Frozen comparison and important limitations, Owner decision and precise dev implementation

### Community 105 - "_fixture"
Cohesion: 0.05
Nodes (44): _event_alert_render_market_metrics(), _event_analysis_percent(), _event_analysis_prompt_payload(), _finite_render_metric(), Bound model-visible percent precision without erasing a non-zero sign., Return the compact semantic model view without runtime or repeated static…, Pass only finite numeric market observations to prose rendering., Facts from the same input used for the Telegram header, not a new feed. (+36 more)

### Community 106 - "LLMJsonResult"
Cohesion: 0.25
Nodes (5): LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., test_backward_compatible_public_api(), CorrelatedFallbackNewsLlm, tuple

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.33
Nodes (17): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+9 more)

### Community 108 - "test_price_service.py"
Cohesion: 0.20
Nodes (16): clean_price_caches(), clear_price_caches(), isolate_http_client_construction(), asyncio, test_get_btc_market_data_does_not_request_unreliable_simple_price_7d(), test_get_coin_market_data_batch_accepts_gram_alias(), test_get_coin_market_data_batch_builds_supported_ids(), test_get_coin_market_data_batch_skips_missing_symbol() (+8 more)

### Community 109 - "Event Alert logic"
Cohesion: 0.09
Nodes (23): CCW-20: meaningful observed-price scenarios, Eight mandatory acceptance gates, Event Alert acceptance criteria (approved 2026-10-16), Event Alert chart reference markers (2026-10-26), Event Alert logic, Event Alert message quality contract, Execution and release gates, Independent evidence and evaluation (+15 more)

### Community 110 - "README.md"
Cohesion: 0.12
Nodes (10): Core, Development and operations, Documentation, Research, What is intentionally not here, Canonical ownership, Conflict resolution, No standing rules outside the repository (+2 more)

### Community 111 - "CCW-41 Reviewer C offline audit"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C offline audit, Compare only after sealing, Prepare frozen blind packets, Review and import

### Community 112 - "ccwbot-ops-agent-mark-report-success"
Cohesion: 0.70
Nodes (4): ccwbot-ops-agent-mark-report-success script, reject(), safe_relative_path(), usage()

### Community 113 - "db/prices.py"
Cohesion: 0.29
Nodes (15): PriceSnapshot, PriceState, UserSymbolAlertState, get_price_snapshots_since(), get_price_state(), get_reference_price_snapshot(), get_user_symbol_alert_state(), AsyncSession (+7 more)

### Community 114 - "Market Reports"
Cohesion: 0.25
Nodes (7): Guardrails, Market Data, Market Reports, News Selection, Restored analysis and cache content revision, Telegram Templates, summary()

### Community 115 - "Release Checklist"
Cohesion: 0.15
Nodes (12): Before Opening The PR, Future release-specific checklist, LLM routing v2 free-only rollout, Mandatory ops-agent image and host-wrapper steps, Observability changes, PR #296: Event Analysis medium reasoning, PR Description Must Include, Production Release: Minimal Safe Path (+4 more)

### Community 116 - "test-ci.md"
Cohesion: 0.40
Nodes (4): Output, Rules you enforce, Verification commands you may run, What you review

### Community 117 - "_AlertEvidenceFakeConnection"
Cohesion: 0.17
Nodes (3): _AlertEvidenceFakeConnection, _FakeResult, _FakeRow

### Community 118 - "CCWBot ChatGPT Project Instructions"
Cohesion: 0.40
Nodes (4): Canonical entry points, CCWBot ChatGPT Project Instructions, Execution priority, Required repository bootstrap

### Community 127 - "Product analytics"
Cohesion: 0.25
Nodes (7): Attribution payload, Create and inspect acquisition links, Direct Telegram Ads measurement, Funnel query, Onboarding v3 selector experiment, Onboarding value-delivery semantics, Product analytics

### Community 128 - "unittest_mock"
Cohesion: 0.18
Nodes (12): _db(), asyncio, parametrize, PR 2 regressions for confirmed semantic cooldown boundary defects. No provider,…, Two distinct event rows can pass prefilter before the first send finishes., test_incomplete_persisted_identity_uses_own_verified_market_move(), test_late_delivery_remains_in_semantic_cooldown_query(), test_stale_prefilter_cannot_bypass_in_lock_cooldown() (+4 more)

### Community 129 - "automatic_price_check"
Cohesion: 0.05
Nodes (69): directional_market_family(), Direction supported by the primary market window; not a significance threshold., _analysed_window_minutes_from_payload(), _build_event_analysis_id(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _raw_event_key_from_payload(), _semantic_family_from_payload() (+61 more)

### Community 130 - "architecture-guardian.md"
Cohesion: 0.50
Nodes (3): Hard rules you enforce, Output, What you review

### Community 131 - "code-quality.md"
Cohesion: 0.50
Nodes (3): Output, Rules you enforce, What you review

### Community 132 - "db-migration-guardian.md"
Cohesion: 0.50
Nodes (3): Hard rules you enforce, Output, What you review

### Community 133 - "devops-release.md"
Cohesion: 0.50
Nodes (3): Output, Rules you enforce, What you review

### Community 134 - "market-pipeline.md"
Cohesion: 0.50
Nodes (3): Output, Rules you enforce, What you review

### Community 135 - "test_ccw9_ccw10.py"
Cohesion: 0.22
Nodes (12): fetch(), asyncio, parametrize, Regression coverage for CCW-9 transient command screens and CCW-10 price cache., test_admin_settings_navigation_remembers_entry_origin(), test_close_deletes_entire_result_and_stale_callback_is_rejected(), test_coingecko_429_sets_provider_backoff_without_ui_rate_limit(), test_consecutive_commands_retire_all_prior_results_by_chat_and_user() (+4 more)

### Community 136 - "product-policy.md"
Cohesion: 0.50
Nodes (3): Output, Product rules you enforce, What you review

### Community 137 - "security-review.md"
Cohesion: 0.50
Nodes (3): Hard rules you enforce, Output, What you review

### Community 138 - "telegram-stars-payments.md"
Cohesion: 0.50
Nodes (3): Output, Rules you enforce, What you review

### Community 139 - "CCW-20 final Cloudflare Render A/B — 2026-10-26"
Cohesion: 0.25
Nodes (7): CCW-20 final Cloudflare Render A/B — 2026-10-26, Decision, Evaluation method, Factual findings, Frozen design, Results, Safety and operations

### Community 143 - "Project Context"
Cohesion: 0.29
Nodes (6): Current product behavior, Event Alerts, Manual command UX and price lookups, Market Heartbeat, Permanent guardrails, Project Context

### Community 144 - "db/premium.py"
Cohesion: 0.20
Nodes (34): UserPremiumSubscription, UserPremiumTrial, activate_premium_from_telegram_stars_payment(), _activate_premium_from_telegram_stars_payment_locked(), expire_due_premium_trials(), get_payment_by_provider_id(), get_user_premium_subscription(), get_user_premium_trial() (+26 more)

### Community 145 - "FakeResponse"
Cohesion: 0.19
Nodes (6): FakeClient, FakeResponse, test_get_coin_price_429_triggers_retry(), __init__(), test_get_with_retry_can_disable_stale_cache_after_429_retries(), test_get_with_retry_returns_stale_cache_after_429_retries()

### Community 147 - "RichDeliveryUncertain"
Cohesion: 0.28
Nodes (8): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert()

### Community 148 - "Development"
Cohesion: 0.25
Nodes (8): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.07
Nodes (54): MarketHeartbeatDecision, MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body(), sanitize_heartbeat_possible_action() (+46 more)

### Community 150 - "os"
Cohesion: 0.10
Nodes (18): asyncpg, bot_services, copy, ctypes, dotenv, openai, os, call() (+10 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.02
Nodes (149): _get_int_env(), api_key(), api_key_env(), base_url(), effective_max_tokens_for(), event_analysis_operation_budget_seconds(), _format_chain(), global_provider_priority() (+141 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "_parse_json"
Cohesion: 0.29
Nodes (6): _parse_json(), Parse a JSON-object response without relaxing schema validation., parametrize, test_event_analysis_prompt_preserves_subpercent_values_as_percentages(), test_parse_json_keeps_object_only_contract(), test_parse_json_handles_whitespace_and_invalid_text()

### Community 156 - "test_multicoin_alerts.py"
Cohesion: 0.12
Nodes (24): Return active market symbols independently of current recipient eligibility., resolve_symbols_to_check(), set_user_coin_subscription(), build_session_factory(), create_user(), asyncio, test_automatic_check_startup_log_shows_separated_symbol_first_delays(), now() (+16 more)

### Community 157 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 158 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 159 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 160 - "test_db_collector_failure_is_isolated_and_later_collectors_continue"
Cohesion: 0.11
Nodes (13): _quality_issues(), DbQuery, Assert every collector SQL statement is a read-only, single, unterminated…, validate_read_only_queries(), test_optional_related_news_is_not_telegram_quality_failure(), test_all_db_queries_are_read_only_and_parameterized(), test_db_collector_failure_is_isolated_and_later_collectors_continue(), _issues() (+5 more)

### Community 162 - "graphify reference: extra exports and benchmark"
Cohesion: 0.20
Nodes (9): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000) (+1 more)

### Community 164 - "build_llm_messages"
Cohesion: 0.33
Nodes (6): build_llm_messages(), graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), base(), prepare(), add()

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.15
Nodes (20): ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment(), _migration_config() (+12 more)

### Community 169 - "test_rich_403_preserves_safe_blocked_classification_without_raw_errors"
Cohesion: 0.11
Nodes (6): parametrize, test_integrity_conflict_preserves_terminal_delivery_reservation(), test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post(), test_rich_success_without_valid_receipt_is_uncertain(), post()

### Community 170 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 171 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 172 - "test_growth_analytics_migration.py"
Cohesion: 0.47
Nodes (5): alembic_config, _alembic_config(), Config, test_growth_analytics_upgrade_backfills_existing_users(), test_premium_trials_upgrade_preserves_existing_premium_and_payment_rows()

### Community 173 - "bot/reports.py"
Cohesion: 0.06
Nodes (62): MarketReportDecision, _build_daily_report_message(), _build_deterministic_report_decision(), _build_market_report_input(), _build_report_coin_payload(), _build_report_telegram_message(), _build_weekly_breadth(), _build_weekly_coin_context() (+54 more)

### Community 174 - "get_report_market_data_batch"
Cohesion: 0.40
Nodes (6): _extract_sparkline_prices(), get_report_market_data_batch(), _optional_float(), _optional_int(), _range_position(), Fetch richer market data for cached daily/weekly reports. This intentionally…

### Community 175 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 176 - "test_heartbeat_postgres.py"
Cohesion: 0.22
Nodes (12): automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, postgres_url(), asyncio, Real PostgreSQL locking checks; the SQLite process mutex cannot prove these…, test_postgres_lock_serializes_separate_workers_and_releases_on_cancellation() (+4 more)

### Community 177 - "0003_premium_watchlist_foundation.py"
Cohesion: 0.80
Nodes (4): _column_names(), downgrade(), _table_names(), upgrade()

### Community 178 - "test_price_handlers.py"
Cohesion: 0.45
Nodes (11): _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users(), test_price_maps_provider_errors_to_safe_user_messages(), test_price_normalizes_legacy_ton_alias_before_lookup(), test_price_rejects_unsupported_symbol_without_provider_call(), test_price_repeated_calls_are_not_ui_throttled() (+3 more)

### Community 180 - "/graphify"
Cohesion: 0.09
Nodes (18): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+10 more)

### Community 181 - "scope"
Cohesion: 0.47
Nodes (6): _confusion(), _delivered_precision(), _quality(), _ratio(), scope(), _technical()

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.33
Nodes (5): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps

### Community 183 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 184 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 186 - "test_report_llm_exhaustion_recovery.py"
Cohesion: 0.43
Nodes (6): asyncio, parametrize, Report availability must survive exhausted LLM providers, but not unrelated…, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload()

### Community 188 - "bot"
Cohesion: 0.50
Nodes (4): bot, Replay published CCW-20 final-copy candidates offline through actual assembly.…, _recorded_candidate_pairs(), test_ccw20_replay_all_20_recorded_candidate_final_pairs_without_llm_calls()

### Community 189 - "news_context.py"
Cohesion: 0.08
Nodes (44): _candidate_news_relevance_label(), classify_news_relevance(), filter_news_for_symbol(), _format_candidate_news(), _has_gram_crypto_context(), _is_clearly_market_wide_news(), is_generic_news_item(), is_material_news_item() (+36 more)

### Community 190 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 192 - "test_prod_diagnostic_fixes.py"
Cohesion: 0.70
Nodes (4): _period(), test_alert_evidence_projects_no_alert_market_context(), test_similarity_detector_ignores_analysis_only_no_alert_group(), test_similarity_detector_ignores_single_event_recipient_fanout()

### Community 193 - "0026_growth_analytics.py"
Cohesion: 0.90
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 194 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 195 - "0004_multicoin_delivery_idempotency.py"
Cohesion: 0.83
Nodes (3): downgrade(), _unique_constraint_names(), upgrade()

### Community 196 - "0005_telegram_stars_payments.py"
Cohesion: 0.83
Nodes (3): downgrade(), _table_names(), upgrade()

### Community 197 - "CCW-25 — Self-hosted LLM owner decision"
Cohesion: 0.25
Nodes (7): Actual local screen, CCW-25 — Self-hosted LLM owner decision, Low-risk next decision, Monthly EUR / DKK comparison, Specific candidates and serving stack, Volume sensitivity and break-even, What is measured

### Community 198 - "CCW-41 owner-reviewed significance reference v1"
Cohesion: 0.29
Nodes (6): Asset-specific labels, CCW-41 owner-reviewed significance reference v1, Historical bot against reference (selected benchmark only), How disputed labels changed, Using this reference for future model prompts, Warrant distributions

### Community 199 - "_working_code_backup.py"
Cohesion: 0.16
Nodes (30): event_alert_benchmark, _aggregate_markdown(), _cli(), compare_reviewers(), _field_exists(), _group_metrics(), import_results(), _label_counts() (+22 more)

### Community 201 - "CCW-29 Handoff — New CCW-43 Event Analysis Prompts"
Cohesion: 0.29
Nodes (6): Artifacts and cryptographic identity, CCW-29 Handoff — New CCW-43 Event Analysis Prompts, Current status, Exact prompt construction, Proposed bounded CCW-29 execution (requires separate owner approval), Provider-specific comparison settings to freeze

### Community 202 - "CCW-25 — Owner decision"
Cohesion: 0.33
Nodes (5): CCW-25 — Owner decision, Economics and next step, Evidence behind the decision, Models actually screened, What each option costs

### Community 203 - "CCWBot — итоги оценки alerts (16 октября 2026)"
Cohesion: 0.33
Nodes (5): CCWBot — итоги оценки alerts (16 октября 2026), Значимость, Полезность текста, Следующая инженерная работа, Файлы

### Community 204 - "CCWBot — blind owner disagreement-only replay"
Cohesion: 0.33
Nodes (5): CCWBot — blind owner disagreement-only replay, Limitations and next actions, Operational recommendation, Owner comparison, disagreement subset only, Per coin (TP/FP/FN/TN)

### Community 205 - "0007_unique_telegram_user_id.py"
Cohesion: 0.83
Nodes (3): _constraint_names(), downgrade(), upgrade()

### Community 206 - "Repository-backed Graphify"
Cohesion: 0.33
Nodes (5): Clones and local development, Repository-backed Graphify, Retention, Shared state in dev, Updates after migration

### Community 207 - "CCW-25 research evidence"
Cohesion: 0.40
Nodes (4): Billing assumptions, CCW-25 research evidence, Interpretation limits, Reproduce

### Community 208 - "0009_error_file_logging_toggle.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 209 - "operator_prompt.md"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C operator prompt, CCW-41 Reviewer C significance rubric v1, Frozen output schema, Frozen rubric

### Community 210 - "onboarding.py"
Cohesion: 0.13
Nodes (28): ensure_default_coin_subscriptions(), Ensure one subscription row per supported symbol for a user., build_first_run_brief_keyboard(), build_onboarding_keyboard(), build_premium_paywall_keyboard(), build_trial_offer_keyboard(), _as_aware_utc(), build_instant_brief() (+20 more)

### Community 213 - "0028_premium_trials.py"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 217 - "0031_onboarding_customize_event.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_event_name_check(), upgrade()

### Community 222 - "backfill_blocked_users.py"
Cohesion: 0.67
Nodes (3): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill()

### Community 223 - "build_review.py"
Cohesion: 0.13
Nodes (23): csv, main(), Convert complete HTML human reviews to PR1 pinned independent labels. Place…, review(), finalize_reconciled(), labels_for(), main(), normalize_yes_no() (+15 more)

### Community 224 - "0027_market_heartbeat_defaults.py"
Cohesion: 0.70
Nodes (4): downgrade(), _has_alert_frequency_column(), _set_default(), upgrade()

### Community 225 - "_extract_ton_coin_data_from_simple_price"
Cohesion: 0.50
Nodes (4): _extract_ton_coin_data_from_simple_price(), Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., test_ton_simple_price_extractor_accepts_only_current_gram_id(), test_ton_simple_price_extractor_rejects_arbitrary_symbol_candidates()

### Community 226 - "_coingecko_headers"
Cohesion: 0.67
Nodes (3): _coingecko_headers(), Return CoinGecko Demo API authentication headers when configured., test_coingecko_headers_are_empty_without_demo_key()

### Community 230 - "0006_payment_recurring_metadata.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 235 - "asyncio"
Cohesion: 0.09
Nodes (10): asyncio, test_event_chart_file_id_reused_across_recipients_in_one_dispatch(), test_heartbeat_falls_back_to_styled_html_if_rich_adapter_has_no_token(), test_heartbeat_uses_existing_shared_price_snapshot_chart(), read_snapshots(), test_rich_ambiguous_error_never_falls_back_or_retries(), test_rich_confirmed_bad_request_falls_back_once(), test_rich_httpx_transport_uncertainty_prevents_fallback() (+2 more)

## Knowledge Gaps
- **441 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+436 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1702 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **38 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `Observability Snippets` to `Ops-Agent Service`, `asyncio`, `CCWBot Ops-Agent Report Analysis`, `RichDeliveryUncertain`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `automatic_price_check`, `test_event_alert_rich_chart_ux.py`, `admin.py`, `test_rich_market_report_delivery.py`, `test_rich_403_preserves_safe_blocked_classification_without_raw_errors`, `asyncio`, `Observability Snippets`, `bot/alerts.py`, `bot/reports.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `CCWBot` connect `CCWBot` to `Observability Snippets`, `README.md`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 169 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 169 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 40 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 40 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _441 weakly-connected nodes found - possible documentation gaps or missing edges._