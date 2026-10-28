# Graph Report - CCWBot  (2026-10-28)

## Corpus Check
- 654 files · ~1,150,924 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 34 file(s) not represented in the graph (top: .toml 12, (none) 8, .csv 7)

## Summary
- 5797 nodes · 17131 edges · 209 communities (176 shown, 33 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1436 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6cc9a6c3`
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
- sqlalchemy
- test_openai_costs.py
- bot/alerts.py
- test_groq_budget.py
- types
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- event_alert_benchmark.py
- log
- pytest
- SessionFactoryRef
- test_heartbeat_silence.py
- LlmUsageLog
- event_text.py
- properties
- ProviderResult
- system_status.py
- validate_market_report_output
- properties
- event_analysis.py
- ccw41_reviewer_c_audit.py
- detectors.py
- admin.py
- button_router
- test_report_cooldowns.py
- Provider fallback (redundancy)
- logging
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- users.py
- Observability Snippets
- select
- NewsItem
- AIProviderRateLimitError
- news_intelligence_service.py
- db/news.py
- keyboards.py
- router.py
- coin_icons.py
- AISchemaValidationError
- test_news_ingestion.py
- test_event_alert_render_reliability.py
- test_llm_outage_detectors.py
- manifest.json
- CCWBot Growth Strategy: 0 -> 1 Premium
- database.py
- price_service.py
- MarketReport
- test_bundle_and_cli.py
- ai_agent_groq.py
- test_event_analysis_health.py
- refresh_report_cache_scheduled
- RedactionReport
- test_admin_cleanup.py
- User
- transient.py
- 0001_initial_schema.py
- validate_event_significance_output
- CCWBot
- calculate_price_change_percent
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
- OpenAICompatibleProvider
- get_or_create_user
- CCW-20 paired final messages
- event_chart.py
- test_event_alert_render_grounded_copy.py
- test_watchlist_ux.py
- alembic/env.py
- Context Audit Report
- llm_usage.py
- watchlist.py
- cli.py
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- bot/config.py
- audit
- test_event_alert_rich_chart_ux.py
- unknown
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- _fixture
- LLMJsonResult
- test_event_alert_chart_markers.py
- test_rich_success_without_valid_receipt_is_uncertain
- Event Alert logic
- Development
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
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
- generate_market_heartbeats
- architecture-guardian.md
- code-quality.md
- db-migration-guardian.md
- devops-release.md
- market-pipeline.md
- product-policy.md
- security-review.md
- telegram-stars-payments.md
- CCW-20 final Cloudflare Render A/B — 2026-10-26
- AGENTS.md
- agents/README.md
- codex_task_prompt_template.md
- Project Context
- db/premium.py
- test_market_heartbeat.py
- os
- test_llm_config_budgets.py
- ChatGPT / Bridge / Codex Workflow
- collectors/__init__.py
- ops_agent/__init__.py
- automatic_price_check
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- db.py
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: extra exports and benchmark
- pkgutil
- Repository Source of Truth
- reviewer-c-rubric.md
- What You Must Do When Invoked
- extraction-spec.md
- test_alembic_migrations.py
- test_rich_403_preserves_safe_blocked_classification_without_raw_errors
- CCW-41 exploratory Reviewer-C agreement/disagreement
- test_heartbeat_does_not_query_previous_event
- CCW-20 — Offline safety correction of retained Cloudflare final texts
- bot/reports.py
- _StructuredRecordBuffer
- test_heartbeat_postgres.py
- 0003_premium_watchlist_foundation.py
- test_price_handlers.py
- Base
- /graphify
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- 0008_database_comments.py
- CCW-43 — Evidence-based Event Analysis prompt redesign
- generate_report_cache
- P
- normalize_symbol
- 0025_llm_operation_correlation.py
- .__init__
- 0026_growth_analytics.py
- CCWBot Operational Report — Unverified (No Production Bundle)
- test_news_driven_alerts.py
- CCW-25 — Self-hosted LLM owner decision
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- CCWBot — blind owner disagreement-only replay
- Repository-backed Graphify
- CCW-25 research evidence
- operator_prompt.md
- display_symbol
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- README_RU.md
- fresh200_luna_wait_start.sh
- openai_luna_wait_start.sh
- build_review.py
- 0027_market_heartbeat_defaults.py
- test_transport_reuses_file_id_and_handles_valid_response
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
9. `EventAnalysisDecision` - 61 edges
10. `Alert` - 60 edges

## Surprising Connections (you probably didn't know these)
- `Finding / fix` --references--> `_build_event_alert_payload()`  [INFERRED]
  research/event_alerts/ccw20_final_render_ab_20261026/CCW20_OFFLINE_DIRECTION_GUARD_20261026.md → bot/alerts.py
- `Event Alert chart reference markers (2026-10-26)` --references--> `price()`  [INFERRED]
  docs/alert_logic.md → bot/handlers/price.py
- `Which 4xx responses fall back` --references--> `AIInvalidJsonError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Read-only local check` --references--> `load_frozen()`  [INFERRED]
  benchmarks/ccw15-v1/README.md → scripts/event_alert_benchmark.py
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (209 total, 33 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.14
Nodes (47): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), alert_analysis_result(), event_analysis_result(), factual_market_input() (+39 more)

### Community 1 - "json"
Cohesion: 0.03
Nodes (78): collections, copy, hashlib, html, html_parser, io, json, math (+70 more)

### Community 2 - "BundleWriter"
Cohesion: 0.11
Nodes (16): ops_agent, BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk. (+8 more)

### Community 3 - "test_onboarding.py"
Cohesion: 0.19
Nodes (32): ProductEvent, UserCoinSubscription, handle_onboarding_callback(), Update, Send a first-run BTC brief or a concise returning-user dashboard., send_start_experience(), inspect, build_session() (+24 more)

### Community 4 - "test_db_queries_and_detectors.py"
Cohesion: 0.05
Nodes (62): alembic_migration, alembic_operations, ops_agent_collectors, run_detectors(), Period, sqlite3, _AlertEvidenceFakeEngine, _assert_malformed_numeric_context_is_safe() (+54 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.07
Nodes (83): _get_int_env(), _backoff_schedule(), breaker_snapshot(), _BreakerState, _failure_threshold(), is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing… (+75 more)

### Community 6 - "telemetry.py"
Cohesion: 0.06
Nodes (80): _json_response_validator(), _validate(), Provider interface and the shared OpenAI-compatible provider implementation.…, AIInvalidJsonError, LLMRateLimitBackoffActive, RuntimeError, Provider-agnostic LLM error types shared across the provider router. These were…, Raised when a provider/model is already in temporary rate-limit backoff. (+72 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.09
Nodes (46): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report(), market_report_change_chart() (+38 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.10
Nodes (54): Payment, build_premium_activation_keyboard(), build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date(), _get_payment_attr() (+46 more)

### Community 9 - "common.py"
Cohesion: 0.10
Nodes (28): decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, Best-effort deletion of a user's slash command in a private chat., _role_label() (+20 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.17
Nodes (49): PriceState, build_admin_llm_diagnostics_text(), build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health., builtins, build_session_factory(), _event_analysis() (+41 more)

### Community 11 - "sqlalchemy"
Cohesion: 0.03
Nodes (25): alembic, downgrade(), _unique_constraint_names(), upgrade(), downgrade(), _table_names(), upgrade(), _constraint_names() (+17 more)

### Community 12 - "test_openai_costs.py"
Cohesion: 0.06
Nodes (86): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., _cost(), monthly_budget_usd(), OpenAIBudget, OpenAIBudgetExhausted, OpenAIBudgetLease, _positive_decimal_env() (+78 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.03
Nodes (100): bot_alerting, alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.… (+92 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.15
Nodes (23): BudgetLease, _Charge, GroqBudget, GroqBudgetExhausted, datetime, Conservative zero-cost Groq admission control, shared across all call types. A…, Test-only reset; production restarts reload persisted usage., GroqProvider (+15 more)

### Community 15 - "types"
Cohesion: 0.06
Nodes (62): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+54 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (67): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+59 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.07
Nodes (57): ask_event_analysis_raw(), ask_market_report_raw(), _parse_json(), Parse a JSON-object response without relaxing schema validation., parametrize, _set_groq_client(), test_event_alert_render_schema_only_contains_model_generated_fields(), test_event_analysis_prompt_makes_llm_the_market_significance_decider() (+49 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (79): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+71 more)

### Community 19 - "event_alert_benchmark.py"
Cohesion: 0.06
Nodes (71): _groq_json_mode_enabled(), importlib_util, random, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, CCW-29 fresh private holdout: collect real POST-200 market cases via…, choose(), Freeze fresh 200 real CCWBot market cases, excluding both earlier sets;…, scripts (+63 more)

### Community 20 - "log"
Cohesion: 0.06
Nodes (57): AbstractEventLoop, AppRunner, asyncio, expire_due_premium_trials(), process_due_trial_expiries(), Application, DEFAULT_TYPE, Independent scheduling for durable Premium-trial lifecycle transitions. (+49 more)

### Community 21 - "pytest"
Cohesion: 0.08
Nodes (27): bot, pytest, asyncio, parametrize, Execute the production aggregate SQL using synthetic final Telegram messages., test_final_section_sql_handles_newlines_fanout_and_missing_sections(), _market(), parametrize (+19 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.14
Nodes (25): can_deliver_market_heartbeat_now(), pytest_asyncio, add_delivery(), delivery_db(), asyncio, parametrize, test_concurrent_checks_send_one_heartbeat_and_reset_timer(), test_delayed_success_uses_completion_not_reservation() (+17 more)

### Community 24 - "LlmUsageLog"
Cohesion: 0.11
Nodes (34): LlmUsageLog, Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider… (+26 more)

### Community 25 - "event_text.py"
Cohesion: 0.06
Nodes (67): _action_price_levels_supported(), compact_event_alert_possible_action(), compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback(), _has_persistent_snapshot_direction() (+59 more)

### Community 26 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 27 - "ProviderResult"
Cohesion: 0.09
Nodes (31): ABC, _create_market_heartbeat(), _schema_check(), ask_event_alert_render_raw(), ask_event_significance_raw(), ask_market_heartbeat_raw(), ask_news_intelligence_raw(), Return JSON mode and provider-specific schemas for verified model attempts. (+23 more)

### Community 28 - "system_status.py"
Cohesion: 0.12
Nodes (37): _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, _container_started_at(), _delivery_failure_category(), _delivery_health() (+29 more)

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "event_analysis.py"
Cohesion: 0.07
Nodes (64): CanonicalEventKey, canonicalize_event_key(), _claim_clause(), _claimed_percent(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal() (+56 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.10
Nodes (60): _aggregate_markdown(), _cli(), compare_reviewers(), _field_exists(), _group_metrics(), import_results(), _label_counts(), _load_manifest() (+52 more)

### Community 33 - "detectors.py"
Cohesion: 0.11
Nodes (34): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+26 more)

### Community 34 - "admin.py"
Cohesion: 0.12
Nodes (54): acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_admin_llm_diagnostics_text(), _build_admin_openai_costs_text(), _build_admin_system_status_text(), _build_error_logging_status_text() (+46 more)

### Community 35 - "button_router"
Cohesion: 0.10
Nodes (40): _automatic_market_check_job_name(), schedule_automatic_market_check(), _format_admin_alert_settings(), send_admin_callback_response(), _standalone_settings_origin(), button_router(), DEFAULT_TYPE, Update (+32 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.17
Nodes (32): reports(), _build_report_telegram_message(), get_or_generate_report(), One shared refresh on old content; never fan out LLM/RSS per recipient., AsyncClock, build_session_factory(), _daily_message(), _empty_report_news_context() (+24 more)

### Community 37 - "Provider fallback (redundancy)"
Cohesion: 0.18
Nodes (10): Admin OpenAI Platform Costs monitoring (optional, read-only), CCW-20 owner-selected Event Alert provider order, Event Analysis timeout and operation budget, Groq free-tier admission control (Event Analysis), Historical Gemini 429 quota classification and backoff, LLM Usage Reporting, Ops-Agent LLM Usage Evidence, Optional OpenAI activation and spend cap (+2 more)

### Community 38 - "logging"
Cohesion: 0.08
Nodes (48): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports(), _collect_secret_values() (+40 more)

### Community 39 - "LLMRouter"
Cohesion: 0.15
Nodes (57): AllProvidersFailedError, Raised when every provider in the fallback chain has been exhausted.…, LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider (+49 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.05
Nodes (69): EventAnalysisDecision, observed_event_alert_level_action(), Specific safe scenarios for the next interval, not buy/sell signals., _as_news_only_rejected_decision(), _build_event_alert_html_message(), _build_event_alert_payload(), _create_event_analysis_decision(), _render_schema_check() (+61 more)

### Community 42 - "users.py"
Cohesion: 0.12
Nodes (23): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), backfill_blocked_users_from_alerts(), get_active_users_with_alert_preferences(), get_active_users_with_chat_ids(), get_user_by_telegram_chat_id(), get_user_role() (+15 more)

### Community 43 - "Observability Snippets"
Cohesion: 0.10
Nodes (20): consecutive_failures(), Compact admin LLM overview, Duplicate/Suppressed Analysis, Event Alert Exact Context Reuse, Event Alert LLM Cadence Estimate, Event Alert section diagnostics and on-demand heartbeat cache, Event Alerts With Market Events, Event Analysis Health (+12 more)

### Community 44 - "select"
Cohesion: 0.06
Nodes (99): filter_news_for_symbol(), _get_or_create_event_alert_market_event(), attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery(), get_event_ai_analysis(), get_last_sent_alert() (+91 more)

### Community 45 - "NewsItem"
Cohesion: 0.13
Nodes (38): _collapse_whitespace(), make_news_key(), NewsItem, _normalize_news_link(), Normalize repeated spaces so keys stay stable across feed formatting., Return a stable URL string for news identity checks., Build a stable key for a news item. Links are preferred because RSS titles can…, _dedupe_report_news() (+30 more)

### Community 46 - "AIProviderRateLimitError"
Cohesion: 0.14
Nodes (28): global_provider_priority(), _parse_priority_list(), provider_priority(), Parse a comma-separated provider list, warning about names that are not…, Resolve the ordered provider chain for a call type. Per-call-type override env…, AIProviderRateLimitError, Raised when a provider refuses a request because the account is rate limited., Startup configuration log (+20 more)

### Community 47 - "news_intelligence_service.py"
Cohesion: 0.11
Nodes (30): _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text(), _dedup_hint_is_specific_to_title(), _dedup_terms() (+22 more)

### Community 48 - "db/news.py"
Cohesion: 0.12
Nodes (29): SeenNews, cleanup_seen_news(), count_recent_news_intelligence_llm_calls(), get_cached_news_item_analysis(), get_cooling_failed_news_keys(), get_news_item_by_key(), get_recent_seen_news(), get_retryable_failed_news_items() (+21 more)

### Community 49 - "keyboards.py"
Cohesion: 0.17
Nodes (21): log_custom_emoji_ids(), price(), DEFAULT_TYPE, Update, Manual price lookup and text-message utility handlers., build_admin_back_keyboard(), build_admin_keyboard(), build_admin_logs_keyboard() (+13 more)

### Community 50 - "router.py"
Cohesion: 0.07
Nodes (46): bot_services_llm, CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions…, get_provider(), Groq provider (primary). OpenAI-compatible chat-completions API., get_provider(), OpenAI paid fallback, guarded by an explicit kill switch and durable budget. (+38 more)

### Community 51 - "coin_icons.py"
Cohesion: 0.17
Nodes (15): _build_event_alert_rich_html(), _build_market_heartbeat_rich_html(), _coin_fallback_emoji(), Presentation only; heartbeat timing and eligibility stay unchanged., Compact, legible rich-message metrics. Keep labels and values contiguous., _rich_metric_html(), build_coin_icon_html(), build_coin_icon_prefix() (+7 more)

### Community 52 - "AISchemaValidationError"
Cohesion: 0.14
Nodes (25): AISchemaValidationError, datetime, Exception, Raised when validated JSON does not match the expected schema. ``raw_content``…, call_render(), FakeProvider, good_render(), input_payload() (+17 more)

### Community 53 - "test_news_ingestion.py"
Cohesion: 0.12
Nodes (13): feedparser, _entry(), _feed(), asyncio, datetime, Regression tests for the independent, bounded RSS ingestion path., test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap() (+5 more)

### Community 54 - "test_event_alert_render_reliability.py"
Cohesion: 0.18
Nodes (21): _event_alert_change_label(), _format_analysed_window_label(), _event_alert_market_context_lines(), _format_optional_price(), build_event_alert_render_prompt(), _payload(), asyncio, parametrize (+13 more)

### Community 55 - "test_llm_outage_detectors.py"
Cohesion: 0.19
Nodes (23): _detector(), _evidence(), parametrize, Detectors and evidence quality for an LLM-side Event Analysis outage. Covers…, Mimic the collector: newest bucket first, each bucket capped by remaining…, _row(), _simulate_row_cap(), test_a_failure_storm_no_longer_starves_delivered_analyses_of_the_row_cap() (+15 more)

### Community 56 - "manifest.json"
Cohesion: 0.06
Nodes (35): batch_size, batches, path, sha256, case_count, cases, dataset_sha256, operator_prompt_sha256 (+27 more)

### Community 57 - "CCWBot Growth Strategy: 0 -> 1 Premium"
Cohesion: 0.15
Nodes (12): Acquisition limitation, CCWBot Growth Strategy: 0 -> 1 Premium, Change, Current comparable cohort, Decision rule, Experiment 1 - Premium-only onboarding selector, Handoff prompt for a new chat, Primary metric (+4 more)

### Community 58 - "database.py"
Cohesion: 0.11
Nodes (28): AppSettings, datetime, Database infrastructure for optional PostgreSQL runtime storage., Run Alembic migrations without blocking the active event loop., Return timezone-aware UTC timestamp., run_async_upgrade(), _run_upgrade(), UserSettings (+20 more)

### Community 59 - "price_service.py"
Cohesion: 0.05
Nodes (61): _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), _extract_sparkline_prices(), _extract_ton_coin_data_from_simple_price(), get_btc_market_data(), get_btc_price(), _get_cached_price() (+53 more)

### Community 60 - "MarketReport"
Cohesion: 0.17
Nodes (20): MarketReport, get_latest_market_report(), AsyncSession, datetime, Save one cached market report generation attempt., Return the newest cached market report for a cadence., save_market_report(), _get_fresh_cached_report() (+12 more)

### Community 61 - "test_bundle_and_cli.py"
Cohesion: 0.06
Nodes (46): _mark_report_success(), load_state(), parse_timestamp(), Any, datetime, Path, record_collection(), record_report_success() (+38 more)

### Community 62 - "ai_agent_groq.py"
Cohesion: 0.04
Nodes (88): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Ground-truth evidence and limitations, Read-only local check, Versioned artifacts, AnalysedWindowReference, _build_event_instance_key(), _build_exact_event_context_fingerprint() (+80 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.10
Nodes (27): _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, evaluate_state(), failure_escalation_threshold(), max_success_age_seconds(), datetime, In-process health signal for Event Analysis. Event Alerts were fully dead for…, Return ``(state, last_success_age_seconds)`` for the Event Analysis health… (+19 more)

### Community 64 - "refresh_report_cache_scheduled"
Cohesion: 0.12
Nodes (22): schedule_report_cache_generation(), Market report use-case entrypoints., generate_daily_report_cache_job(), generate_weekly_report_cache_job(), _is_report_provider_backoff_active(), Scheduled cache refresh: regenerate unless the cache stays fresh past the grace…, One recovery attempt after a scheduled failure; no recurring retry storm., refresh_report_cache_scheduled() (+14 more)

### Community 65 - "RedactionReport"
Cohesion: 0.06
Nodes (72): dataclasses, httpx, collect_health(), Any, collect_local_state(), Any, collect_logs(), _empty_counts() (+64 more)

### Community 66 - "test_admin_cleanup.py"
Cohesion: 0.14
Nodes (16): AsyncFalse, AsyncTrue, _callback_update(), _callback_values(), FakeMessage, FakeQuery, asyncio, test_admin_alert_settings_keyboard_has_no_threshold_controls() (+8 more)

### Community 67 - "User"
Cohesion: 0.09
Nodes (44): AlertRecipient, _automatic_delivery_lock(), _count_suppression(), _deliver_market_event_alert(), _delivery_error_class_name(), _disable_recipient_if_bot_blocked(), EventRecipientFilterResult, _filter_event_recipients_for_cooldown() (+36 more)

### Community 68 - "transient.py"
Cohesion: 0.08
Nodes (28): enter_callback(), enter_command(), private_key(), Manage command-generated Telegram replies without touching passive…, Manual rich sends bypass PTB's normal send_message override., Track acknowledged rich output for Close and next-command cleanup., Intercept only messages sent in the scope of a manual command/callback., register_rich_reply() (+20 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "validate_event_significance_output"
Cohesion: 0.17
Nodes (16): empirical_absolute_move_percentile(), EventSignificanceDecision, Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., validate_event_significance_output(), _significance_schema_check(), _payload(), parametrize (+8 more)

### Community 71 - "CCWBot"
Cohesion: 0.10
Nodes (20): Admin System Status, CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables (+12 more)

### Community 72 - "calculate_price_change_percent"
Cohesion: 0.27
Nodes (10): calculate_price_change_percent(), is_cooldown_active(), datetime, Decimal, Core alert-rule helpers used by automatic market checks., Calculate a percent change without mixing binary floats and ``Decimal`` values., Return True while a previous alert is still inside the cooldown window., test_calculate_price_change_percent_accepts_mixed_decimal_and_float_operands() (+2 more)

### Community 73 - "bot/health.py"
Cohesion: 0.10
Nodes (24): aiohttp, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any, datetime, Authoritative last successful Event Analysis time, or None when unavailable.…, Event Analysis health, as a nested block that never changes the top-level… (+16 more)

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
Cohesion: 0.21
Nodes (18): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, test_specific_next_observation_is_not_generic(), _decision(), _market(), parametrize, Regressions from 2026-10-13 delivered Event Alerts. These assertions inspect…, _render() (+10 more)

### Community 78 - "test_news_intelligence_schema.py"
Cohesion: 0.25
Nodes (17): _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), schema_check(), asyncio, parametrize, Offline News Intelligence symbol-contract regression tests; no provider calls. (+9 more)

### Community 79 - "news_service.py"
Cohesion: 0.14
Nodes (24): fetch_crypto_news(), headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Merge available feeds by publication age *before* applying the batch limit. A…, Low-cost, word-boundary-aware prefilter; not an alert decision. (+16 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.20
Nodes (37): LlmOperationOutcome, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., build_session(), FakeNewsLlm, asyncio, Exception, _raw_item() (+29 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "datetime"
Cohesion: 0.04
Nodes (71): argparse, concurrent_futures, datetime, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., Audit only aggregated benchmark budget and next-call feasibility (no inference). (+63 more)

### Community 83 - "OpenAICompatibleProvider"
Cohesion: 0.15
Nodes (9): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., GeminiProvider, get_provider(), Gemini provider (second fallback). Reached through Google's OpenAI-compatible… (+1 more)

### Community 84 - "get_or_create_user"
Cohesion: 0.44
Nodes (12): get_or_create_user(), Create or update profile fields for the current Telegram interaction., build_session(), asyncio, test_get_or_create_user_allows_missing_username(), test_get_or_create_user_demotes_existing_admin_removed_from_allowlist(), test_get_or_create_user_keeps_non_admin_role_with_allowlist(), test_get_or_create_user_marks_second_admin_id_from_allowlist() (+4 more)

### Community 85 - "CCW-20 paired final messages"
Cohesion: 0.09
Nodes (21): 10. ev_3c7f3da2e73e4b90 — ETH, 11. ev_7804adc277bd3333 — GRAM, 12. ev_345fc49db8255adf — GRAM, 13. ev_7b3325d2f2609480 — GRAM, 14. ev_1b39a518ede3c14f — GRAM, 15. ev_6500c5ad9f5364bc — GRAM, 16. ev_4bba21dd01bc8372 — SOL, 17. ev_1ea4cea05b78ed5c — SOL (+13 more)

### Community 86 - "event_chart.py"
Cohesion: 0.18
Nodes (15): ChartResult, _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw, Deterministic PNG chart from persisted, timestamped price observations only., Auditable reference value and its actual, not nominal, UTC timestamp. (+7 more)

### Community 87 - "test_event_alert_render_grounded_copy.py"
Cohesion: 0.36
Nodes (11): decision_for(), final_action(), market_down(), Evidence-backed Stage-2 Render guards and final-copy regression tests. All…, test_conditionals_do_not_hide_false_observed_direction(), test_render_does_not_invent_a_path_from_missing_or_gapped_snapshots(), test_render_evidence_exposes_grounded_recent_path_not_only_direction(), test_same_conditional_copy_is_not_forced_on_distinct_paths() (+3 more)

### Community 88 - "test_watchlist_ux.py"
Cohesion: 0.07
Nodes (46): build_watchlist_keyboard(), build_subscribe_message(), build_watchlist_message(), build_watchlist_render(), AsyncFalse, AsyncNoop, AsyncTrue, build_session() (+38 more)

### Community 89 - "alembic/env.py"
Cohesion: 0.39
Nodes (7): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), Connection, logging_config

### Community 90 - "Context Audit Report"
Cohesion: 0.07
Nodes (18): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+10 more)

### Community 91 - "llm_usage.py"
Cohesion: 0.29
Nodes (6): AsyncSession, LLM usage telemetry persistence. Belongs here: saving and updating…, Update a usage row when downstream JSON schema validation fails., Persist one sanitized terminal outcome for a logical LLM operation., save_llm_operation_outcome(), update_llm_usage_log_status()

### Community 92 - "watchlist.py"
Cohesion: 0.10
Nodes (53): _as_aware_utc(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active(), is_user_trial_active() (+45 more)

### Community 93 - "cli.py"
Cohesion: 0.14
Nodes (32): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+24 more)

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.17
Nodes (11): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Log pattern counting, News-candidate signal (+3 more)

### Community 96 - "bot/config.py"
Cohesion: 0.12
Nodes (20): combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids(), Centralized configuration loaded from environment variables. Notes about key…, is_admin_user(), sync_user_from_update(), test_admin_user_ids_ignore_empty_whitespace_and_invalid_values(), test_multi_admin_user_ids_parse_comma_list() (+12 more)

### Community 97 - "audit"
Cohesion: 0.23
Nodes (13): audit(), positive_age_minutes(), ranking(), main(), _number(), Read-only assessment of sanitized Event Analysis decisions; NOT an LLM replay.…, _time(), Production timeline review tests: decision counts are not ground-truth FP/FN. (+5 more)

### Community 98 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.20
Nodes (14): prepare_chart_points(), Never extrapolate over missing time or label a partial day as 24h., Event-specific references are opt-in; Heartbeat is exactly the old chart., render_price_chart(), _observations(), Event Alert UX, chart evidence and single-send fallback contracts., test_chart_accepts_normal_30_minute_scheduler_jitter_but_rejects_stale(), test_chart_downtime_selects_latest_gap_free_run_without_inventing_prices() (+6 more)

### Community 99 - "unknown"
Cohesion: 0.11
Nodes (19): Output, Rules you enforce, What you review, Admin System Status, Delivery Outcome Tracking, Event Alert Suppression Reasons, Event Alert User-Facing Copy Checks, Boundaries (+11 more)

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
Cohesion: 0.06
Nodes (40): Clear all breaker state (tests and controlled restarts)., reset_breakers(), Clear in-memory provider/model backoffs for tests and controlled restarts., reset_llm_rate_limit_backoffs(), _real_socket, socket, _guarded_create_connection(), _guarded_getaddrinfo() (+32 more)

### Community 106 - "LLMJsonResult"
Cohesion: 0.29
Nodes (5): LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., test_backward_compatible_public_api(), CorrelatedFallbackNewsLlm, tuple

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.33
Nodes (17): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+9 more)

### Community 109 - "Event Alert logic"
Cohesion: 0.09
Nodes (22): CCW-20: meaningful observed-price scenarios, Eight mandatory acceptance gates, Event Alert acceptance criteria (approved 2026-10-16), Event Alert chart reference markers (2026-10-26), Event Alert logic, Event Alert message quality contract, Execution and release gates, Independent evidence and evaluation (+14 more)

### Community 110 - "Development"
Cohesion: 0.11
Nodes (13): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries (+5 more)

### Community 111 - "CCW-41 Reviewer C offline audit"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C offline audit, Compare only after sealing, Prepare frozen blind packets, Review and import

### Community 112 - "ccwbot-ops-agent-mark-report-success"
Cohesion: 0.70
Nodes (4): ccwbot-ops-agent-mark-report-success script, reject(), safe_relative_path(), usage()

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

### Community 129 - "generate_market_heartbeats"
Cohesion: 0.07
Nodes (35): _build_market_heartbeat_id(), Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain (+27 more)

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
Cohesion: 0.19
Nodes (36): UserPremiumSubscription, UserPremiumTrial, activate_premium_from_telegram_stars_payment(), _activate_premium_from_telegram_stars_payment_locked(), ensure_default_coin_subscriptions(), expire_due_premium_trials(), get_payment_by_provider_id(), get_user_premium_subscription() (+28 more)

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.07
Nodes (59): MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body(), validate_market_heartbeat_output(), _build_market_heartbeat_html_message() (+51 more)

### Community 150 - "os"
Cohesion: 0.08
Nodes (20): asyncpg, bot_services, build_llm_messages(), graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), ctypes, dotenv, openai (+12 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.03
Nodes (124): api_key(), api_key_env(), base_url(), effective_max_tokens_for(), event_analysis_operation_budget_seconds(), _format_chain(), is_reasoning_model(), is_thinking_model() (+116 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 156 - "automatic_price_check"
Cohesion: 0.07
Nodes (52): _build_event_analysis_id(), AlertRecipientResolution, automatic_price_check(), _build_news_candidates(), _classify_news_context(), _coin_is_secondary_context(), get_alert_recipients(), _get_previous_event_alert_id() (+44 more)

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
Cohesion: 0.12
Nodes (16): _alert_evidence_windows(), _collect_alert_repetition_rows(), collect_db(), _collector_error(), _jsonable(), Any, datetime, Exception (+8 more)

### Community 162 - "graphify reference: extra exports and benchmark"
Cohesion: 0.20
Nodes (9): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000) (+1 more)

### Community 164 - "Repository Source of Truth"
Cohesion: 0.33
Nodes (5): Canonical ownership, Conflict resolution, No standing rules outside the repository, Repository bootstrap, Repository Source of Truth

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.11
Nodes (25): alembic_config, ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment() (+17 more)

### Community 169 - "test_rich_403_preserves_safe_blocked_classification_without_raw_errors"
Cohesion: 0.11
Nodes (6): parametrize, test_integrity_conflict_preserves_terminal_delivery_reservation(), test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post(), test_rich_confirmed_telegram_rejections(), post()

### Community 170 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 171 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 172 - "CCW-20 — Offline safety correction of retained Cloudflare final texts"
Cohesion: 0.33
Nodes (5): CCW-20 — Offline safety correction of retained Cloudflare final texts, Concrete verified example — ETH (`ev_0ab71234c9080ecc`), Finding / fix, Reproducible offline check, What this test does not prove

### Community 173 - "bot/reports.py"
Cohesion: 0.09
Nodes (37): MarketReportDecision, _build_daily_report_message(), _build_deterministic_report_decision(), _build_market_report_input(), _build_report_coin_payload(), _build_weekly_breadth(), _build_weekly_coin_context(), _build_weekly_context() (+29 more)

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
Cohesion: 0.32
Nodes (14): CoinGeckoRateLimitError, Exception, Raised when CoinGecko returns HTTP 429., _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users(), test_price_maps_provider_errors_to_safe_user_messages() (+6 more)

### Community 179 - "Base"
Cohesion: 0.15
Nodes (20): alembic_script, Base, Base class for all SQLAlchemy models., Save one LLM usage telemetry row., save_llm_usage_log(), DeclarativeBase, _alembic_head(), _load_comments_migration() (+12 more)

### Community 180 - "/graphify"
Cohesion: 0.09
Nodes (18): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+10 more)

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.33
Nodes (5): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps

### Community 183 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 184 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 186 - "generate_report_cache"
Cohesion: 0.16
Nodes (14): _freshness_seconds(), generate_report_cache(), _schema_check(), Exception, Collapse a validation message to one log-safe token. Validation messages are…, Generate one market-wide LLM report and cache the completed or failed attempt., _sanitize_schema_failure_detail(), _start_report_provider_backoff() (+6 more)

### Community 189 - "normalize_symbol"
Cohesion: 0.04
Nodes (89): _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _calculate_price_change(), _candidate_news_relevance_label(), classify_news_relevance(), _coin_name(), _format_candidate_news(), _has_gram_crypto_context() (+81 more)

### Community 190 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 193 - "0026_growth_analytics.py"
Cohesion: 0.90
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 194 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 196 - "test_news_driven_alerts.py"
Cohesion: 0.47
Nodes (5): _load_news_driven_alert_candidates(), asyncio, Regression coverage for the disabled standalone-news Event Alert path., test_news_driven_alerts_warning_logs_once_not_per_cycle(), test_news_driven_flag_cannot_bypass_product_policy()

### Community 197 - "CCW-25 — Self-hosted LLM owner decision"
Cohesion: 0.25
Nodes (7): Actual local screen, CCW-25 — Self-hosted LLM owner decision, Low-risk next decision, Monthly EUR / DKK comparison, Specific candidates and serving stack, Volume sensitivity and break-even, What is measured

### Community 198 - "CCW-41 owner-reviewed significance reference v1"
Cohesion: 0.29
Nodes (6): Asset-specific labels, CCW-41 owner-reviewed significance reference v1, Historical bot against reference (selected benchmark only), How disputed labels changed, Using this reference for future model prompts, Warrant distributions

### Community 199 - "_working_code_backup.py"
Cohesion: 0.12
Nodes (36): event_alert_benchmark, hashfile(), main(), metrics(), Versioned private calibration reference from owner's 66 A/C re-decisions.…, write(), _aggregate_markdown(), _cli() (+28 more)

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

### Community 206 - "Repository-backed Graphify"
Cohesion: 0.33
Nodes (5): Clones and local development, Repository-backed Graphify, Retention, Shared state in dev, Updates after migration

### Community 207 - "CCW-25 research evidence"
Cohesion: 0.40
Nodes (4): Billing assumptions, CCW-25 research evidence, Interpretation limits, Reproduce

### Community 209 - "operator_prompt.md"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C operator prompt, CCW-41 Reviewer C significance rubric v1, Frozen output schema, Frozen rubric

### Community 210 - "display_symbol"
Cohesion: 0.12
Nodes (29): coin_display_name(), display_symbol(), is_supported_symbol(), premium_symbols_display(), Supported coin metadata shared by price checks and Premium watchlists., supported_symbols_display(), build_onboarding_customize_keyboard(), Premium-only onboarding selector. BTC stays as the free default during… (+21 more)

### Community 223 - "build_review.py"
Cohesion: 0.13
Nodes (23): csv, main(), Convert complete HTML human reviews to PR1 pinned independent labels. Place…, review(), finalize_reconciled(), labels_for(), main(), normalize_yes_no() (+15 more)

### Community 224 - "0027_market_heartbeat_defaults.py"
Cohesion: 0.70
Nodes (4): downgrade(), _has_alert_frequency_column(), _set_default(), upgrade()

### Community 230 - "0006_payment_recurring_metadata.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 235 - "asyncio"
Cohesion: 0.12
Nodes (8): asyncio, test_event_chart_file_id_reused_across_recipients_in_one_dispatch(), test_heartbeat_falls_back_to_styled_html_if_rich_adapter_has_no_token(), test_heartbeat_uses_existing_shared_price_snapshot_chart(), read_snapshots(), test_rich_ambiguous_error_never_falls_back_or_retries(), test_rich_confirmed_bad_request_falls_back_once(), test_rich_httpx_transport_uncertainty_prevents_fallback()

## Knowledge Gaps
- **439 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+434 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1698 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `unknown` to `generate_market_heartbeats`, `Observability Snippets`, `asyncio`, `CCWBot Ops-Agent Report Analysis`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `generate_market_heartbeats` to `test_event_alert_rich_chart_ux.py`, `button_router`, `unknown`, `test_rich_market_report_delivery.py`, `asyncio`, `test_rich_success_without_valid_receipt_is_uncertain`, `bot/alerts.py`, `bot/reports.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `query()` connect `/graphify` to `test_event_alert_rich_chart_ux.py`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 169 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 169 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 40 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 40 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _439 weakly-connected nodes found - possible documentation gaps or missing edges._