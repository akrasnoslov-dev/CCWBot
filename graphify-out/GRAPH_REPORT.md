# Graph Report - CCWBot  (2026-10-26)

## Corpus Check
- 324 files · ~297,058 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 27 file(s) not represented in the graph (top: .toml 12, (none) 8, .example 2)

## Summary
- 5004 nodes · 15121 edges · 212 communities (181 shown, 31 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1215 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4699a66d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_analysis_validation.py
- replay_event_significance.py
- LlmUsageLog
- test_onboarding.py
- Period
- test_llm_breaker.py
- telemetry.py
- test_rich_market_report_delivery.py
- test_telegram_stars_payments.py
- logging
- test_system_status.py
- sqlalchemy
- test_openai_budget.py
- bot/alerts.py
- test_groq_budget.py
- ensure_default_coin_subscriptions
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- test_event_alert_real_benchmark.py
- bootstrap.py
- test_news_intelligence_schema.py
- types
- test_heartbeat_silence.py
- test_bundle_and_cli.py
- event_alert_presentation_fallback
- test_seen_news_dedup.py
- bot/reports.py
- _StructuredRecordBuffer
- validate_market_report_output
- properties
- test_watchlist_ux.py
- ccw41_reviewer_c_audit.py
- detectors.py
- handlers/__init__.py
- Observability Snippets
- test_report_cooldowns.py
- LLMRateLimitBackoffActive
- error_file_logging.py
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- model_for
- test_multicoin_alerts.py
- db/alerts.py
- bot/news.py
- User
- build_event_significance_prompt
- make_news_key
- test_report_scheduled_refresh.py
- router.py
- display_symbol
- AISchemaValidationError
- ai_agent_groq.py
- test_event_alert_delivery_quality_regressions.py
- test_llm_outage_detectors.py
- llm/config.py
- CCWBot Growth Strategy: 0 -> 1 Premium
- system_status.py
- price_service.py
- test_product_analytics.py
- cli.py
- test_ccw41_reviewer_c_audit.py
- test_event_analysis_health.py
- handlers/settings.py
- RedactionReport
- /graphify
- test_heartbeat_postgres.py
- MarketReportDecision
- 0001_initial_schema.py
- EventAnalysisValidationError
- CCWBot
- decimal
- event_analysis.py
- 0024_gram_symbol.py
- AIInvalidJsonError
- test_agent_workflow_contract.py
- admin.py
- AIProviderRateLimitError
- canonicalize_event_key
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- json
- _fixture
- event_identity.py
- bot/config.py
- event_chart.py
- test_event_alert_historical_diagnostics.py
- event_text.py
- button_router
- ContractTests
- test_health_counts_no_alert_as_a_successful_analysis
- get_coin_price
- Development
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- openai_budget.py
- validate_market_heartbeat_output
- llm/env.py
- unknown
- test_event_alert_postrelease_regressions.py
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- reasoning_effort_for
- graphify reference: extra exports and benchmark
- test_event_alert_chart_markers.py
- test_news_ingestion.py
- Event Alert logic
- README.md
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
- test_event_alert_render_reliability.py
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
- _build_event_analysis_input
- onboarding.py
- architecture-guardian.md
- code-quality.md
- db-migration-guardian.md
- devops-release.md
- market-pipeline.md
- _RecordingProvider
- product-policy.md
- security-review.md
- telegram-stars-payments.md
- What You Must Do When Invoked
- AGENTS.md
- agents/README.md
- codex_task_prompt_template.md
- Project Context
- db/premium.py
- news_service.py
- _build_exact_event_context_fingerprint
- alembic/env.py
- test_event_alert_composition_investigation.py
- test_market_heartbeat.py
- _deliver_market_event_alert
- test_llm_config_budgets.py
- ChatGPT / Bridge / Codex Workflow
- test_event_alert_rich_chart_ux.py
- collectors/__init__.py
- ops_agent/__init__.py
- event_analysis_health.py
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- db.py
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- pkgutil
- news_intelligence_service.py
- reviewer-c-rubric.md
- 0008_database_comments.py
- extraction-spec.md
- test_alembic_migrations.py
- Repository Source of Truth
- LLMJsonResult
- clean_news_title
- test_rich_403_preserves_safe_blocked_classification_without_raw_errors
- test_exhausted_provider_chain_uses_verified_data_fallback
- 0003_premium_watchlist_foundation.py
- TransientSessions
- handlers/reports.py
- test_ccw9_ccw10.py
- FakeAsyncClient
- test_provider_sampling_parameters_are_model_compatible
- provider_priority
- log
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- test_heartbeat_does_not_query_previous_event
- 0004_multicoin_delivery_idempotency.py
- schedule_report_cache_generation
- 0006_payment_recurring_metadata.py
- RichDeliveryUncertain
- db/reports.py
- normalize_symbol
- 0025_llm_operation_correlation.py
- .__init__
- get_report_market_data_batch
- test_price_handlers.py
- test_prod_runtime_diagnostic_fixes.py
- bot/health.py
- Base
- NoopAsyncClient
- .__init__
- event_alert_benchmark
- test_trial_lifecycle.py
- test_price_service.py
- database.py
- test_expected_models_match_bot_defaults.py
- CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21)
- Repository-backed Graphify
- 0031_onboarding_customize_event.py
- backfill_blocked_users.py
- Event Alert acceptance criteria (approved 2026-10-16)

## God Nodes (most connected - your core abstractions)
1. `Period` - 114 edges
2. `LLMRouter` - 96 edges
3. `Base` - 91 edges
4. `normalize_symbol()` - 88 edges
5. `User` - 68 edges
6. `utc_now()` - 64 edges
7. `run_detectors()` - 64 edges
8. `EventAnalysisDecision` - 56 edges
9. `automatic_price_check()` - 56 edges
10. `RedactionReport` - 56 edges

## Surprising Connections (you probably didn't know these)
- `Event Alert chart reference markers (2026-10-26)` --references--> `price()`  [INFERRED]
  docs/alert_logic.md → bot/handlers/price.py
- `Startup configuration log` --references--> `AIProviderRateLimitError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Read-only local check` --references--> `load_frozen()`  [INFERRED]
  benchmarks/ccw15-v1/README.md → scripts/event_alert_benchmark.py
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py
- `Production Read-Only Setup` --references--> `unknown()`  [INFERRED]
  ops_agent/README.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (212 total, 31 thin omitted)

### Community 0 - "test_event_analysis_validation.py"
Cohesion: 0.13
Nodes (44): Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), alert_analysis_result(), event_analysis_result(), factual_market_input(), parametrize, test_alert_accepts_gram_display_symbol_for_backend_gram(), test_alert_possible_action_advice_like_wording_no_longer_blocks_schema() (+36 more)

### Community 1 - "replay_event_significance.py"
Cohesion: 0.09
Nodes (36): GroqProvider, collections, scripts, blind_packet(), classify_replay_error(), effort_budget(), groq_significance_response_format(), live_report() (+28 more)

### Community 2 - "LlmUsageLog"
Cohesion: 0.12
Nodes (32): LlmUsageLog, Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider… (+24 more)

### Community 3 - "test_onboarding.py"
Cohesion: 0.20
Nodes (30): ProductEvent, UserCoinSubscription, Send a first-run BTC brief or a concise returning-user dashboard., send_start_experience(), inspect, build_session(), create_user(), FakeMessage (+22 more)

### Community 4 - "Period"
Cohesion: 0.05
Nodes (63): alembic_migration, alembic_operations, importlib_util, ops_agent_collectors, run_detectors(), Period, sqlite3, _AlertEvidenceFakeEngine (+55 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.08
Nodes (75): _backoff_schedule(), breaker_snapshot(), _BreakerState, _failure_threshold(), is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics. (+67 more)

### Community 6 - "telemetry.py"
Cohesion: 0.07
Nodes (65): asyncio, _create_market_heartbeat(), _validate(), Provider interface and the shared OpenAI-compatible provider implementation.…, BudgetLease, Conservative zero-cost Groq admission control, shared across all call types. A…, LLM provider fallback package. Groq stays the primary provider; disabled-by-…, current_llm_operation_id() (+57 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.08
Nodes (48): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report(), market_report_change_chart() (+40 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.10
Nodes (54): Payment, build_premium_activation_keyboard(), build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date(), _get_payment_attr() (+46 more)

### Community 9 - "logging"
Cohesion: 0.11
Nodes (26): _callback_command_update(), decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, _telegram_user_id() (+18 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.18
Nodes (46): build_admin_llm_diagnostics_text(), build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health., build_session_factory(), _event_analysis(), _final_failed_alert(), _now() (+38 more)

### Community 11 - "sqlalchemy"
Cohesion: 0.03
Nodes (27): alembic, downgrade(), _table_names(), upgrade(), _constraint_names(), downgrade(), upgrade(), _column_names() (+19 more)

### Community 12 - "test_openai_budget.py"
Cohesion: 0.16
Nodes (27): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., OpenAIBudget, OpenAIBudgetExhausted, RuntimeError, OpenAI was skipped before HTTP because safe authorization was unavailable., budget_db(), asyncio (+19 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.05
Nodes (69): bot_alerting, alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.… (+61 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.15
Nodes (21): _Charge, GroqBudget, GroqBudgetExhausted, datetime, Test-only reset; production restarts reload persisted usage., asyncio, Regression checks for zero-cost Groq pacing, day quota, symbol fairness and…, Other Groq model budgets remain separate from Event Analysis reservations. (+13 more)

### Community 15 - "ensure_default_coin_subscriptions"
Cohesion: 0.07
Nodes (31): ensure_default_coin_subscriptions(), Ensure one subscription row per supported symbol for a user., is_symbol_free(), handle_watchlist_callback(), make_user(), test_coin_unlock_rules(), test_is_symbol_free_only_btc(), test_is_user_premium_active_uses_active_until() (+23 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (65): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+57 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.12
Nodes (42): ask_event_analysis_raw(), _configure(), ContentProvider, _empty_report_news_context(), _grounded_alert(), _grounding_market(), _grounding_schema_check(), _install_report_inputs() (+34 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (79): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+71 more)

### Community 19 - "test_event_alert_real_benchmark.py"
Cohesion: 0.16
Nodes (32): canonical_json(), _check_private_data(), compare_recorded_run(), _confusion(), _delivered_precision(), digest(), load_frozen(), Path (+24 more)

### Community 20 - "bootstrap.py"
Cohesion: 0.10
Nodes (30): AbstractEventLoop, AppRunner, bot_handlers, Application, register_bot_handlers(), start_health_server(), handle_health(), stop_health_server() (+22 more)

### Community 21 - "test_news_intelligence_schema.py"
Cohesion: 0.27
Nodes (16): _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), asyncio, parametrize, Offline News Intelligence symbol-contract regression tests; no provider calls., _router() (+8 more)

### Community 22 - "types"
Cohesion: 0.14
Nodes (13): Runtime state and startup helpers., close_database(), initialize_database(), Any, Dispose database resources created during startup., SessionFactoryRef, _sync_package_database_engine(), asyncio (+5 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.10
Nodes (30): get_last_sent_alert_at(), Return latest successful delivery time for the user and coin., save_alert(), update_alert_delivery_status(), pytest_asyncio, fake_get_active_users_with_alert_preferences(), add_delivery(), asyncio (+22 more)

### Community 24 - "test_bundle_and_cli.py"
Cohesion: 0.05
Nodes (52): ops_agent, BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk. (+44 more)

### Community 25 - "event_alert_presentation_fallback"
Cohesion: 0.15
Nodes (22): compact_event_alert_situation(), ensure_useful_situation(), event_alert_presentation_fallback(), Keep Event Alert explanations useful instead of repeating the metric block., Return display-only context from supplied evidence, never alert eligibility.…, Replace a bare percentage restatement with why the event crossed significance., parametrize, Grounded Event Alert copy: test scenarios without recipient or LLM calls. (+14 more)

### Community 26 - "test_seen_news_dedup.py"
Cohesion: 0.12
Nodes (36): attach_analysis_to_market_event(), count_market_events(), get_event_ai_analysis(), get_latest_success_event_ai_analysis(), get_or_create_market_event(), Return the number of stored market events, optionally for one symbol., Return the market event for event_instance_key, creating it when needed., Return an existing AI analysis for the event/input pair if present. (+28 more)

### Community 27 - "bot/reports.py"
Cohesion: 0.08
Nodes (54): MarketReport, Mark news items as seen in PostgreSQL after they were used by the bot., remember_news_context(), _build_deterministic_report_decision(), _build_market_report_input(), _build_report_coin_payload(), _build_weekly_breadth(), _build_weekly_coin_context() (+46 more)

### Community 28 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 29 - "validate_market_report_output"
Cohesion: 0.16
Nodes (37): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+29 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "test_watchlist_ux.py"
Cohesion: 0.10
Nodes (52): build_my_plan_keyboard(), build_watchlist_keyboard(), is_admin_update(), Update, build_plan_message(), build_subscribe_message(), build_user_settings_message(), build_user_settings_render() (+44 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.13
Nodes (35): random, _aggregate_markdown(), _cli(), compare_reviewers(), _field_exists(), _group_metrics(), _label_counts(), _load_manifest() (+27 more)

### Community 33 - "detectors.py"
Cohesion: 0.12
Nodes (31): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+23 more)

### Community 34 - "handlers/__init__.py"
Cohesion: 0.17
Nodes (39): acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_error_logging_status_text(), chat_id(), error_logging_off(), error_logging_on() (+31 more)

### Community 35 - "Observability Snippets"
Cohesion: 0.12
Nodes (16): Compact admin LLM overview, Duplicate/Suppressed Analysis, Event Alert Exact Context Reuse, Event Alert LLM Cadence Estimate, Event Alert section diagnostics and on-demand heartbeat cache, Event Alerts With Market Events, Event Key Frequency, Final delivered Event Alert text quality (+8 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.17
Nodes (31): reports(), _build_report_telegram_message(), send_daily_report_message(), AsyncClock, build_session_factory(), _daily_message(), _empty_report_news_context(), FakeTarget (+23 more)

### Community 37 - "LLMRateLimitBackoffActive"
Cohesion: 0.11
Nodes (24): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., LLMRateLimitBackoffActive, Raised when a provider/model is already in temporary rate-limit backoff., GeminiProvider (+16 more)

### Community 38 - "error_file_logging.py"
Cohesion: 0.08
Nodes (48): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., bot_observability, _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports() (+40 more)

### Community 39 - "LLMRouter"
Cohesion: 0.15
Nodes (54): api_key_env(), LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider, _http_error() (+46 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.05
Nodes (75): EventAnalysisDecision, with_canonical_event_key(), is_news_centered_event_action(), Keep trading-oriented guidance conditional and proportionate., Keep monitoring copy focused on market evidence, not supporting headlines., Reject direct trading instructions in every user-visible Event Alert field., sanitize_financial_instruction(), soften_possible_action() (+67 more)

### Community 42 - "model_for"
Cohesion: 0.09
Nodes (26): model_for(), _model_from_env(), provider_attempts(), Reject blank or retired identifiers from env and internal override paths., Resolve a model identifier, treating invalid overrides as unset.…, Validate a non-environment runtime override against retired model policy., Resolve the model for a (provider, call_type) pair from env, with defaults., Return the ordered concrete provider/model attempts for one logical LLM… (+18 more)

### Community 43 - "test_multicoin_alerts.py"
Cohesion: 0.13
Nodes (26): AlertRecipientResolution, Return active market symbols independently of current recipient eligibility., resolve_symbols_to_check(), set_user_coin_subscription(), build_session_factory(), create_user(), asyncio, test_automatic_fallback_state_persists_decimal_prices() (+18 more)

### Community 44 - "db/alerts.py"
Cohesion: 0.07
Nodes (50): count_recent_market_events_for_symbol(), get_alert_delivery(), get_last_sent_alert(), get_last_sent_event_alert_at_for_event_key(), get_latest_event_analysis_attempt(), get_latest_event_analysis_by_statuses(), get_latest_event_analysis_success_at(), get_latest_market_heartbeat() (+42 more)

### Community 45 - "bot/news.py"
Cohesion: 0.16
Nodes (29): _dedupe_report_news(), fetch_report_news_context(), within_window(), _has_report_news_identity(), _item_link(), _item_published_at(), _item_related_symbols(), _news_row_rank() (+21 more)

### Community 46 - "User"
Cohesion: 0.14
Nodes (32): User, backfill_blocked_users_from_alerts(), get_active_users_with_alert_preferences(), get_active_users_with_chat_ids(), get_or_create_user(), get_user_by_telegram_chat_id(), get_user_role(), is_telegram_chat_delivery_enabled() (+24 more)

### Community 47 - "build_event_significance_prompt"
Cohesion: 0.20
Nodes (18): build_event_significance_prompt(), _event_significance_prompt_payload(), Return the small always-on model view used only for significance., hashlib, build_prompt(), check_production_parity(), inspect_private_frozen(), instruction() (+10 more)

### Community 48 - "make_news_key"
Cohesion: 0.10
Nodes (34): LlmOperationOutcome, make_news_key(), Build a stable key for a news item. Links are preferred because RSS titles can…, SeenNews, cleanup_seen_news(), count_recent_news_intelligence_llm_calls(), get_cached_news_item_analysis(), get_cooling_failed_news_keys() (+26 more)

### Community 49 - "test_report_scheduled_refresh.py"
Cohesion: 0.35
Nodes (11): _cached_report(), asyncio, Scheduled report cache refresh: cadence, grace window, and explicit skip…, test_daily_cache_fresh_by_seconds_at_fire_time_regenerates(), test_expired_weekly_cache_triggers_regeneration(), test_failed_memory_refresh_preserves_still_valid_report(), test_failed_scheduled_job_schedules_one_retry_and_no_retry_storm(), test_failed_scheduled_refresh_backs_off_before_next_poll() (+3 more)

### Community 50 - "router.py"
Cohesion: 0.07
Nodes (42): get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions…, get_provider(), Groq provider (primary). OpenAI-compatible chat-completions API., get_provider(), OpenAIProvider, OpenAI paid fallback, guarded by an explicit kill switch and durable budget., _default_registry() (+34 more)

### Community 51 - "display_symbol"
Cohesion: 0.09
Nodes (37): Escape all model/news wording; only safely link explicit HTTP(S) sources., _report_coin_icon_html(), _safe_rich_line(), _build_event_alert_rich_html(), _build_market_heartbeat_html_message(), _build_market_heartbeat_payload(), _build_market_heartbeat_rich_html(), _coin_fallback_emoji() (+29 more)

### Community 52 - "AISchemaValidationError"
Cohesion: 0.13
Nodes (27): _schema_check(), ProviderResult, Normalized successful chat-completion result returned by every provider., AISchemaValidationError, Raised when validated JSON does not match the expected schema. ``raw_content``…, call_render(), FakeProvider, good_render() (+19 more)

### Community 53 - "ai_agent_groq.py"
Cohesion: 0.07
Nodes (48): ask_event_alert_render_raw(), ask_event_significance_raw(), ask_market_heartbeat_raw(), ask_market_report_raw(), ask_news_intelligence_raw(), build_event_alert_render_prompt(), build_event_analysis_prompt(), build_market_heartbeat_prompt() (+40 more)

### Community 54 - "test_event_alert_delivery_quality_regressions.py"
Cohesion: 0.17
Nodes (21): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, _event_alert_render_prompt_payload(), Return only a supported sign; no rounded or raw market numbers reach Render., _render_market_direction(), test_specific_next_observation_is_not_generic(), _decision(), _market() (+13 more)

### Community 55 - "test_llm_outage_detectors.py"
Cohesion: 0.19
Nodes (23): _detector(), _evidence(), parametrize, Detectors and evidence quality for an LLM-side Event Analysis outage. Covers…, Mimic the collector: newest bucket first, each bucket capped by remaining…, _row(), _simulate_row_cap(), test_a_failure_storm_no_longer_starves_delivered_analyses_of_the_row_cap() (+15 more)

### Community 56 - "llm/config.py"
Cohesion: 0.13
Nodes (24): api_key(), base_url(), event_analysis_operation_budget_seconds(), _format_chain(), is_thinking_model(), openai_enabled(), provider_is_configured(), Environment-driven configuration for the LLM provider fallback chain. All… (+16 more)

### Community 57 - "CCWBot Growth Strategy: 0 -> 1 Premium"
Cohesion: 0.15
Nodes (12): Acquisition limitation, CCWBot Growth Strategy: 0 -> 1 Premium, Change, Current comparable cohort, Decision rule, Experiment 1 - Premium-only onboarding selector, Handoff prompt for a new chat, Primary metric (+4 more)

### Community 58 - "system_status.py"
Cohesion: 0.13
Nodes (35): _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, ComponentStatus, _delivery_failure_category(), _delivery_health() (+27 more)

### Community 59 - "price_service.py"
Cohesion: 0.15
Nodes (22): _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), get_btc_market_data(), get_btc_price(), _get_cached_price(), _get_stale_cached_price(), _get_with_retry() (+14 more)

### Community 60 - "test_product_analytics.py"
Cohesion: 0.07
Nodes (52): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+44 more)

### Community 61 - "cli.py"
Cohesion: 0.08
Nodes (59): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+51 more)

### Community 62 - "test_ccw41_reviewer_c_audit.py"
Cohesion: 0.22
Nodes (27): import_results(), _case(), _dataset(), _labels(), prepared(), MonkeyPatch, Path, _result_rows() (+19 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.12
Nodes (17): _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, evaluate_state(), failure_escalation_threshold(), max_success_age_seconds(), Return ``(state, last_success_age_seconds)`` for the Event Analysis health…, Event Analysis health: /health reporting, log escalation, and suppression…, test_a_long_failure_streak_is_degraded() (+9 more)

### Community 64 - "handlers/settings.py"
Cohesion: 0.22
Nodes (14): _format_admin_alert_settings(), Best-effort deletion of a user's slash command in a private chat., safe_delete_command_invocation(), DEFAULT_TYPE, Update, User settings command handler., settings(), asyncio (+6 more)

### Community 65 - "RedactionReport"
Cohesion: 0.08
Nodes (52): datetime, httpx, collect_health(), Any, collect_local_state(), Any, collect_logs(), _empty_counts() (+44 more)

### Community 66 - "/graphify"
Cohesion: 0.09
Nodes (17): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+9 more)

### Community 67 - "test_heartbeat_postgres.py"
Cohesion: 0.20
Nodes (13): automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, importlib, postgres_url(), asyncio, Real PostgreSQL locking checks; the SQLite process mutex cannot prove these… (+5 more)

### Community 68 - "MarketReportDecision"
Cohesion: 0.19
Nodes (13): MarketReportDecision, _build_daily_report_message(), _build_weekly_report_message(), _format_report_coin_watchpoints(), _format_weekly_breadth(), Bound LLM verbosity without replacing or manufacturing market claims., One price/change table, plus model watchpoints with no repeated quotes., Non-repeated per-coin watchpoints carry useful weekly analysis. (+5 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "EventAnalysisValidationError"
Cohesion: 0.17
Nodes (19): empirical_absolute_move_percentile(), EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., _required_choice(), validate_event_significance_output() (+11 more)

### Community 71 - "CCWBot"
Cohesion: 0.10
Nodes (20): Admin System Status, CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables (+12 more)

### Community 72 - "decimal"
Cohesion: 0.10
Nodes (22): calculate_price_change_percent(), is_cooldown_active(), datetime, Decimal, Core alert-rule helpers used by automatic market checks., Calculate a percent change without mixing binary floats and ``Decimal`` values., Return True while a previous alert is still inside the cooldown window., _event_alert_change_label() (+14 more)

### Community 73 - "event_analysis.py"
Cohesion: 0.15
Nodes (33): _claim_clause(), _claimed_percent(), _decimal_market_value(), _direction_for_claim(), directional_market_family(), _duration_minutes(), _duration_minutes_from_claim(), _elapsed_minutes() (+25 more)

### Community 74 - "0024_gram_symbol.py"
Cohesion: 0.33
Nodes (13): _coerce_related_symbols(), _column_names(), downgrade(), _has_table_and_symbol(), _has_table_columns(), _merge_price_state(), _merge_user_coin_subscriptions(), _merge_user_symbol_alert_state() (+5 more)

### Community 75 - "AIInvalidJsonError"
Cohesion: 0.13
Nodes (12): AIInvalidJsonError, datetime, Exception, RuntimeError, Raised when the provider response is not valid JSON., Circuit breaker, Event Analysis timeout and operation budget, Historical Gemini 429 quota classification and backoff (+4 more)

### Community 76 - "test_agent_workflow_contract.py"
Cohesion: 0.19
Nodes (10): _adapter_path(), _agent_names(), _agent_paths(), _load_toml(), Path, test_agent_definitions_have_matching_claude_adapters(), test_agent_definitions_have_required_schema(), test_agent_routing_references_existing_agents() (+2 more)

### Community 77 - "admin.py"
Cohesion: 0.10
Nodes (39): AcquisitionLinkMetadata, build_acquisition_telegram_url(), Validated Telegram deep-link acquisition attribution., Allowlisted, bounded metadata stored behind an opaque acquisition link., Return safe operator metadata or reject values outside the attribution…, Build a Telegram deep link only from a valid configured bot username and opaque…, validate_acquisition_link_metadata(), _build_admin_llm_diagnostics_text() (+31 more)

### Community 78 - "AIProviderRateLimitError"
Cohesion: 0.17
Nodes (21): ABC, BaseProvider, Common interface for all LLM providers., True when this provider has all configuration required for an attempt., Run one chat completion and return a :class:`ProviderResult` on success.…, AIProviderRateLimitError, Provider-agnostic LLM error types shared across the provider router. These were…, Raised when a provider refuses a request because the account is rate limited. (+13 more)

### Community 79 - "canonicalize_event_key"
Cohesion: 0.10
Nodes (28): CanonicalEventKey, canonicalize_event_key(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal(), _fallback_event_key(), _is_random_event_key() (+20 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.23
Nodes (37): NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap(), build_session(), FakeNewsLlm, asyncio (+29 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "json"
Cohesion: 0.10
Nodes (23): argparse, http_server, json, pathlib, audit(), positive_age_minutes(), ranking(), main() (+15 more)

### Community 83 - "_fixture"
Cohesion: 0.06
Nodes (39): _event_analysis_percent(), _event_analysis_prompt_payload(), Bound model-visible percent precision without erasing a non-zero sign., Return the compact semantic model view without runtime or repeated static…, Clear all breaker state (tests and controlled restarts)., reset_breakers(), math, _real_socket (+31 more)

### Community 84 - "event_identity.py"
Cohesion: 0.06
Nodes (56): _analysed_window_minutes_from_payload(), _automatic_market_check_job_name(), _build_event_analysis_id(), _build_event_instance_key(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _canonical_decimal_string(), _canonical_event_analysis_context() (+48 more)

### Community 85 - "bot/config.py"
Cohesion: 0.11
Nodes (21): combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids(), Centralized configuration loaded from environment variables. Notes about key…, is_admin_user(), sync_user_from_update(), dotenv, test_admin_user_ids_ignore_empty_whitespace_and_invalid_values() (+13 more)

### Community 86 - "event_chart.py"
Cohesion: 0.18
Nodes (15): ChartResult, _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw, Deterministic PNG chart from persisted, timestamped price observations only., Auditable reference value and its actual, not nominal, UTC timestamp. (+7 more)

### Community 87 - "test_event_alert_historical_diagnostics.py"
Cohesion: 0.22
Nodes (13): bot, copy, _market(), asyncio, parametrize, Historical alert defect contracts: never call an external provider or Telegram.…, test_contradictory_period_alignment_is_never_delivered_as_factual_claim(), test_exact_reuse_excludes_changed_micro_moves_and_news() (+5 more)

### Community 88 - "event_text.py"
Cohesion: 0.18
Nodes (20): compact_elapsed_since(), _concise_explanation_clause(), _decimal_market_value(), _has_persistent_snapshot_direction(), _is_safe_llm_situation(), _is_safe_structured_market_interpretation(), _market_numeric_values(), _parse_datetime() (+12 more)

### Community 89 - "button_router"
Cohesion: 0.10
Nodes (34): button_router(), DEFAULT_TYPE, Update, build_admin_alert_settings_keyboard(), build_admin_back_keyboard(), build_admin_keyboard(), build_admin_logs_keyboard(), build_admin_premium_keyboard() (+26 more)

### Community 91 - "test_health_counts_no_alert_as_a_successful_analysis"
Cohesion: 0.15
Nodes (7): asyncio, test_a_slow_database_degrades_the_block_instead_of_stalling_health(), test_health_counts_no_alert_as_a_successful_analysis(), _logical_success(), test_health_payload_carries_no_secrets_or_environment_values(), test_health_reports_unknown_rather_than_ok_without_evidence(), test_health_still_degrades_safely_when_the_whole_lookup_fails()

### Community 92 - "get_coin_price"
Cohesion: 0.18
Nodes (16): get_coin_market_data_batch(), get_coin_price(), Populate price cache from persisted runtime state on startup., Get current coin price and 24h change from CoinGecko. Unsupported symbols raise…, Fetch market data for supported symbols with one CoinGecko request. Missing…, _set_cached_price(), warm_up_price_cache(), asyncio (+8 more)

### Community 93 - "Development"
Cohesion: 0.25
Nodes (8): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.17
Nodes (11): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Log pattern counting, News-candidate signal (+3 more)

### Community 96 - "openai_budget.py"
Cohesion: 0.17
Nodes (17): _cost(), monthly_budget_usd(), OpenAIBudgetLease, _positive_decimal_env(), _positive_int_env(), pricing_usd_per_million(), datetime, Decimal (+9 more)

### Community 97 - "validate_market_heartbeat_output"
Cohesion: 0.22
Nodes (14): MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body(), validate_market_heartbeat_output(), heartbeat_result() (+6 more)

### Community 98 - "llm/env.py"
Cohesion: 0.13
Nodes (18): _get_int_env(), Substrings that mark a model identifier as reasoning-capable (overridable via…, reasoning_model_markers(), get_choice_env(), get_int_env(), _is_secret_name(), _looks_like_secret_value(), Environment parsing helpers for the LLM subsystem that fail loudly. The… (+10 more)

### Community 99 - "unknown"
Cohesion: 0.11
Nodes (19): Output, Rules you enforce, What you review, Admin System Status, Delivery Outcome Tracking, Event Alert Suppression Reasons, Event Alert User-Facing Copy Checks, Boundaries (+11 more)

### Community 100 - "test_event_alert_postrelease_regressions.py"
Cohesion: 0.15
Nodes (17): compact_event_alert_possible_action(), Keep Event Alert actions short, conditional, and non-prescriptive., asyncio, parametrize, Production-pattern regression fixtures; synthetic inputs, never recipient data., The production 2026-10-12/13 numeric-key path omitted both stored families., test_absent_current_move_does_not_invent_price_direction(), test_current_market_move_anchors_directional_identity() (+9 more)

### Community 101 - "ccwbot-ops-agent-collect"
Cohesion: 0.40
Nodes (8): ccwbot-ops-agent-collect script, fail_preflight(), interrupted(), is_utc_timestamp(), reject(), usage(), validate_period(), write_receipt()

### Community 103 - "Dev Ops Guide"
Cohesion: 0.12
Nodes (15): Dependency updates, Deploying Ops-Agent Changes, Dev Ops Guide, Environment Rules, Future approved deployment and incident recovery, Legacy wrapper installation (historical, not routine after operator cutover), Manual Production Deploy (exceptional releases only), Non-interactive, least-privilege bot deploys (+7 more)

### Community 104 - "Event Alert benchmark and historical diagnostics (PR 1)"
Cohesion: 0.29
Nodes (4): Event Alert benchmark and historical diagnostics (PR 1), Historical investigation: evidence status, Next-stage dependency and acceptance, Technical baseline, not product-quality scores

### Community 105 - "reasoning_effort_for"
Cohesion: 0.14
Nodes (17): effective_max_tokens_for(), is_reasoning_model(), Return the completion budget for one concrete provider attempt. The public…, True when this model identifier is known to accept ``reasoning_effort``., Resolve ``reasoning_effort`` for a (model, call_type) pair, or ``None`` when…, reasoning_effort_for(), test_builtin_reasoning_markers_survive_legacy_extension_value(), test_empty_marker_list_falls_back_instead_of_silently_disabling() (+9 more)

### Community 106 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.33
Nodes (17): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+9 more)

### Community 108 - "test_news_ingestion.py"
Cohesion: 0.08
Nodes (25): expire_due_premium_trials(), process_due_trial_expiries(), Application, DEFAULT_TYPE, Independent scheduling for durable Premium-trial lifecycle transitions., Lazy import keeps the scheduler independent of database compatibility exports., Record due expiry transitions without coupling them to alert processing., schedule_premium_trial_expiry() (+17 more)

### Community 109 - "Event Alert logic"
Cohesion: 0.12
Nodes (16): Event Alert chart reference markers (2026-10-26), Event Alert logic, Event Alert message quality contract, Render evidence and backend guard behavior, Rich notification layout follow-up (2026-10-17), Step 10 - Send once, Step 1 - Read the market, Step 2 - Build the evidence (+8 more)

### Community 110 - "README.md"
Cohesion: 0.18
Nodes (5): Core, Development and operations, Documentation, Research, What is intentionally not here

### Community 111 - "CCW-41 Reviewer C offline audit"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C offline audit, Compare only after sealing, Prepare frozen blind packets, Review and import

### Community 112 - "ccwbot-ops-agent-mark-report-success"
Cohesion: 0.70
Nodes (4): ccwbot-ops-agent-mark-report-success script, reject(), safe_relative_path(), usage()

### Community 113 - "test_event_alert_render_reliability.py"
Cohesion: 0.31
Nodes (12): _payload(), asyncio, parametrize, Regression contracts for production Event Alert Render rejection categories.…, test_flat_news_led_input_cannot_be_recovered_as_market_alert(), test_invalid_provider_chain_exhaustion_uses_validated_evidence_fallback(), test_mixed_transport_and_invalid_output_does_not_claim_success(), test_render_cannot_invent_or_escalate_urgency() (+4 more)

### Community 114 - "Market Reports"
Cohesion: 0.29
Nodes (6): Guardrails, Market Data, Market Reports, News Selection, Restored analysis and cache content revision, Telegram Templates

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

### Community 128 - "_build_event_analysis_input"
Cohesion: 0.09
Nodes (30): AnalysedWindowReference, _calculate_price_change(), get_analysed_window_minutes(), _select_analysed_window_reference(), _build_event_analysis_input(), _build_market_heartbeat_input(), _compact_event_snapshot(), _compact_event_snapshots() (+22 more)

### Community 129 - "onboarding.py"
Cohesion: 0.12
Nodes (39): _as_aware_utc(), can_deliver_market_heartbeat_now(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active() (+31 more)

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

### Community 135 - "_RecordingProvider"
Cohesion: 0.19
Nodes (13): _provider_payload(), asyncio, Captures the kwargs the router passes, without making any provider call., _RecordingProvider, _route(), test_openai_adapter_kill_switch_blocks_before_client_or_http(), test_request_payload_includes_reasoning_effort_when_set(), test_request_payload_omits_reasoning_effort_when_unset() (+5 more)

### Community 136 - "product-policy.md"
Cohesion: 0.50
Nodes (3): Output, Product rules you enforce, What you review

### Community 137 - "security-review.md"
Cohesion: 0.50
Nodes (3): Hard rules you enforce, Output, What you review

### Community 138 - "telegram-stars-payments.md"
Cohesion: 0.50
Nodes (3): Output, Rules you enforce, What you review

### Community 139 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 143 - "Project Context"
Cohesion: 0.29
Nodes (6): Current product behavior, Event Alerts, Manual command UX and price lookups, Market Heartbeat, Permanent guardrails, Project Context

### Community 144 - "db/premium.py"
Cohesion: 0.20
Nodes (34): UserPremiumSubscription, UserPremiumTrial, activate_premium_from_telegram_stars_payment(), _activate_premium_from_telegram_stars_payment_locked(), expire_due_premium_trials(), get_payment_by_provider_id(), get_user_premium_subscription(), get_user_premium_trial() (+26 more)

### Community 145 - "news_service.py"
Cohesion: 0.18
Nodes (13): headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Low-cost, word-boundary-aware prefilter; not an alert decision., Bound provider latency/response size; parse only successfully fetched bytes., _read_rss_feed() (+5 more)

### Community 146 - "_build_exact_event_context_fingerprint"
Cohesion: 0.36
Nodes (12): _build_exact_event_context_fingerprint(), _payload(), parametrize, test_exact_context_does_not_reuse_the_ambiguous_change_field_contract(), test_exact_context_ignores_previous_title_not_sent_to_model(), test_exact_context_ignores_runtime_metadata_and_normalizes_decimal_representation(), test_exact_context_includes_last_message_time_for_grounding_reuse(), test_exact_context_invalidates_any_real_market_or_news_change() (+4 more)

### Community 147 - "alembic/env.py"
Cohesion: 0.33
Nodes (8): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), Connection, logging_config, sqlalchemy_engine

### Community 148 - "test_event_alert_composition_investigation.py"
Cohesion: 0.20
Nodes (26): market_direction_claims_supported(), Check explicit period directions and the direction implied by relationships., market(), parametrize, Synthetic regressions for the October alert-composition investigation., test_alignment_fallback_names_direction_and_verified_size_relationship(), test_alignment_without_monotonic_snapshots_survives_compaction(), test_consistent_with_describes_alignment_not_snapshot_persistence() (+18 more)

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.11
Nodes (36): Alert, MarketHeartbeat, telegram_constants, test_failed_telegram_send_does_not_reset_clock(), build_session_factory(), create_heartbeat(), create_user(), fake_app() (+28 more)

### Community 150 - "_deliver_market_event_alert"
Cohesion: 0.07
Nodes (51): AlertRecipient, _automatic_delivery_lock(), _deliver_market_event_alert(), _delivery_error_class_name(), _delivery_retry_delay_seconds(), _disable_recipient_if_bot_blocked(), get_alert_recipients(), _is_permanent_telegram_delivery_error() (+43 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.12
Nodes (28): log_resolved_configuration(), max_tokens_for(), Resolve the completion-token budget for a call type. The current ``LLM_*`` name…, Log the resolved LLM configuration once, at startup. This is the signal that…, Per-call-type token budgets, reasoning effort, loud env parsing, and the…, _startup_log_messages(), test_bad_value_warns_once_not_once_per_call(), test_budget_warning_is_silent_for_a_provider_with_no_api_key() (+20 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.21
Nodes (16): prepare_chart_points(), Never extrapolate over missing time or label a partial day as 24h., Event-specific references are opt-in; Heartbeat is exactly the old chart., render_price_chart(), _observations(), Event Alert UX, chart evidence and single-send fallback contracts., test_chart_accepts_normal_30_minute_scheduler_jitter_but_rejects_stale(), test_chart_downtime_selects_latest_gap_free_run_without_inventing_prices() (+8 more)

### Community 156 - "event_analysis_health.py"
Cohesion: 0.18
Nodes (14): consecutive_failures(), datetime, In-process health signal for Event Analysis. Event Alerts were fully dead for…, A successful event analysis clears the failure streak., Count one failed event analysis and return the new consecutive-failure count., Sanitized view for diagnostics: counters and timestamps only, never payload…, record_failure(), record_success() (+6 more)

### Community 157 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 158 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 159 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 160 - "db.py"
Cohesion: 0.09
Nodes (20): dataclasses, _alert_evidence_windows(), _collect_alert_repetition_rows(), collect_db(), _collector_error(), _jsonable(), Any, datetime (+12 more)

### Community 164 - "news_intelligence_service.py"
Cohesion: 0.11
Nodes (32): _budget_priority_score(), build_llm_messages(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text(), _dedup_hint_is_specific_to_title() (+24 more)

### Community 166 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.11
Nodes (25): alembic_config, ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment() (+17 more)

### Community 169 - "Repository Source of Truth"
Cohesion: 0.33
Nodes (5): Canonical ownership, Conflict resolution, No standing rules outside the repository, Repository bootstrap, Repository Source of Truth

### Community 170 - "LLMJsonResult"
Cohesion: 0.33
Nodes (4): LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., CorrelatedFallbackNewsLlm, tuple

### Community 171 - "clean_news_title"
Cohesion: 0.32
Nodes (10): _format_event_related_context(), _format_market_heartbeat_related_context(), _format_related_context(), _safe_telegram_link_url(), _utf16_length(), clean_news_title(), clean_related_news_text(), test_clean_news_title_preserves_non_matching_titles() (+2 more)

### Community 172 - "test_rich_403_preserves_safe_blocked_classification_without_raw_errors"
Cohesion: 0.11
Nodes (9): asyncio, parametrize, test_heartbeat_falls_back_to_styled_html_if_rich_adapter_has_no_token(), test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post(), test_rich_ambiguous_error_never_falls_back_or_retries(), test_rich_confirmed_bad_request_falls_back_once(), test_transport_reuses_file_id_and_handles_valid_response() (+1 more)

### Community 173 - "test_exhausted_provider_chain_uses_verified_data_fallback"
Cohesion: 0.50
Nodes (5): asyncio, parametrize, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload()

### Community 174 - "0003_premium_watchlist_foundation.py"
Cohesion: 0.80
Nodes (4): _column_names(), downgrade(), _table_names(), upgrade()

### Community 176 - "handlers/reports.py"
Cohesion: 0.21
Nodes (11): daily_report(), DEFAULT_TYPE, Update, Market report command handlers., weekly_report(), send_weekly_report_message(), Groq free-tier admission control (Event Analysis), LLM Usage Reporting (+3 more)

### Community 177 - "test_ccw9_ccw10.py"
Cohesion: 0.14
Nodes (17): Intercept only messages sent in the scope of a manual command/callback., _tracking(), TransientBot, with_close_button(), bot_services, ExtBot, asyncio, parametrize (+9 more)

### Community 179 - "test_provider_sampling_parameters_are_model_compatible"
Cohesion: 0.18
Nodes (6): CloudflareProvider, _CapturingClient, _CapturingCompletions, _mock_openai_admission(), test_openai_adapter_uses_verified_openai_compatible_reasoning_contract(), test_provider_sampling_parameters_are_model_compatible()

### Community 180 - "provider_priority"
Cohesion: 0.20
Nodes (12): global_provider_priority(), _parse_priority_list(), provider_priority(), Parse a comma-separated provider list, warning about names that are not…, Resolve the ordered provider chain for a call type. Per-call-type override env…, test_event_default_adds_optional_cloudflare_without_changing_other_tasks(), test_explicit_global_and_event_priority_remain_authoritative(), test_retired_provider_cannot_be_enabled_even_with_legacy_keys() (+4 more)

### Community 181 - "log"
Cohesion: 0.18
Nodes (20): _build_market_heartbeat_id(), cleanup_seen_news_job(), _decimal_numeric_context_value(), _deliver_market_heartbeat(), _enabled_subscription_by_symbol(), generate_market_heartbeats(), _get_due_market_heartbeat_recipients(), _heartbeat_numeric_context() (+12 more)

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.17
Nodes (10): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps, Data handling, Event Alert research archive, Existing evidence (+2 more)

### Community 183 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 184 - "0004_multicoin_delivery_idempotency.py"
Cohesion: 0.83
Nodes (3): downgrade(), _unique_constraint_names(), upgrade()

### Community 185 - "schedule_report_cache_generation"
Cohesion: 0.27
Nodes (7): schedule_report_cache_generation(), Market report use-case entrypoints., generate_daily_report_cache_job(), generate_weekly_report_cache_job(), One recovery attempt after a scheduled failure; no recurring retry storm., _schedule_failed_report_retry(), test_report_cache_scheduler_replaces_weekly_direct_send_and_strong_signal()

### Community 186 - "0006_payment_recurring_metadata.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 187 - "RichDeliveryUncertain"
Cohesion: 0.28
Nodes (8): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert()

### Community 188 - "db/reports.py"
Cohesion: 0.32
Nodes (7): get_latest_market_report(), AsyncSession, datetime, Market report cache persistence. Belongs here: daily/weekly market report cache…, Save one cached market report generation attempt., Return the newest cached market report for a cadence., save_market_report()

### Community 189 - "normalize_symbol"
Cohesion: 0.07
Nodes (50): _candidate_news_relevance_label(), classify_news_relevance(), _coin_name(), filter_news_for_symbol(), _format_candidate_news(), _has_gram_crypto_context(), _is_clearly_market_wide_news(), is_generic_news_item() (+42 more)

### Community 190 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 192 - "get_report_market_data_batch"
Cohesion: 0.29
Nodes (8): _extract_sparkline_prices(), get_report_market_data_batch(), _optional_float(), _optional_int(), _range_position(), Fetch richer market data for cached daily/weekly reports. This intentionally…, test_get_report_market_data_batch_keeps_btc_alert_cache_unchanged(), test_get_report_market_data_batch_uses_markets_endpoint()

### Community 193 - "test_price_handlers.py"
Cohesion: 0.18
Nodes (23): log_custom_emoji_ids(), price(), DEFAULT_TYPE, Update, Manual price lookup and text-message utility handlers., build_price_result_keyboard(), build_supported_symbols_message(), send_manual_rate_limit_message() (+15 more)

### Community 195 - "bot/health.py"
Cohesion: 0.20
Nodes (15): aiohttp, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any, datetime, Authoritative last successful Event Analysis time, or None when unavailable.…, Event Analysis health, as a nested block that never changes the top-level… (+7 more)

### Community 196 - "Base"
Cohesion: 0.14
Nodes (27): alembic_script, Base, PriceSnapshot, PriceState, Base class for all SQLAlchemy models., UserSymbolAlertState, get_price_snapshots_since(), get_price_state() (+19 more)

### Community 201 - "test_trial_lifecycle.py"
Cohesion: 0.40
Nodes (3): asyncio, SessionContext, test_trial_expiry_job_contains_lifecycle_failures()

### Community 202 - "test_price_service.py"
Cohesion: 0.13
Nodes (15): _extract_ton_coin_data_from_simple_price(), Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., clean_price_caches(), clear_price_caches(), FakeClient, FakeResponse, isolate_http_client_construction(), test_get_coin_price_429_triggers_retry() (+7 more)

### Community 203 - "database.py"
Cohesion: 0.06
Nodes (47): AppSettings, _collapse_whitespace(), _normalize_news_link(), datetime, Database infrastructure for optional PostgreSQL runtime storage., Run Alembic migrations without blocking the active event loop., Return timezone-aware UTC timestamp., Normalize repeated spaces so keys stay stable across feed formatting. (+39 more)

### Community 205 - "CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21)"
Cohesion: 0.33
Nodes (5): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Ground-truth evidence and limitations, Read-only local check, Versioned artifacts

### Community 206 - "Repository-backed Graphify"
Cohesion: 0.33
Nodes (5): One-time migration from existing Windows graph, Repository-backed Graphify, Retention, Shared state in dev, Updates after migration

### Community 208 - "0031_onboarding_customize_event.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_event_name_check(), upgrade()

### Community 209 - "backfill_blocked_users.py"
Cohesion: 0.67
Nodes (3): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill()

### Community 210 - "Event Alert acceptance criteria (approved 2026-10-16)"
Cohesion: 0.50
Nodes (4): Eight mandatory acceptance gates, Event Alert acceptance criteria (approved 2026-10-16), Execution and release gates, Independent evidence and evaluation

## Knowledge Gaps
- **272 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+267 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1330 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `unknown` to `test_rich_403_preserves_safe_blocked_classification_without_raw_errors`, `CCWBot Ops-Agent Report Analysis`, `RichDeliveryUncertain`, `event_analysis_health.py`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `unknown`, `test_rich_market_report_delivery.py`, `test_rich_403_preserves_safe_blocked_classification_without_raw_errors`, `bot/alerts.py`, `_deliver_market_event_alert`, `test_event_alert_rich_chart_ux.py`, `bot/reports.py`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `query()` connect `/graphify` to `test_event_alert_rich_chart_ux.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 74 inferred relationships involving `LLMRouter` (e.g. with `AIInvalidJsonError` and `AIProviderRateLimitError`) actually correct?**
  _`LLMRouter` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 36 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _272 weakly-connected nodes found - possible documentation gaps or missing edges._