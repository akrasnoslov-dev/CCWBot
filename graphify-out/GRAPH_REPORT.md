# Graph Report - CCWBot  (2026-10-29)

## Corpus Check
- 656 files · ~1,153,597 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 34 file(s) not represented in the graph (top: .toml 12, (none) 8, .csv 7)

## Summary
- 5836 nodes · 17241 edges · 225 communities (187 shown, 38 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1440 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `051b3c4f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- json
- ai_agent_groq.py
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
- test_product_analytics.py
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- replay_event_significance.py
- bot/health.py
- test_event_alert_historical_diagnostics.py
- cli.py
- test_heartbeat_silence.py
- LlmUsageLog
- event_text.py
- properties
- test_event_analysis_cloudflare_schema.py
- llm/config.py
- validate_market_report_output
- properties
- domain/premium.py
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
- User
- Observability Snippets
- select
- bot/news.py
- AIProviderRateLimitError
- news_intelligence_service.py
- db/news.py
- pytest
- router.py
- normalize_symbol
- test_event_alert_render_provider_chain.py
- test_report_and_hourly_ingestion_share_serial_llm_budget_gate
- _create_event_analysis_decision
- test_llm_outage_detectors.py
- manifest.json
- CCWBot Growth Strategy: 0 -> 1 Premium
- _deliver_market_event_alert
- price_service.py
- system_status.py
- test_bundle_and_cli.py
- _RecordingProvider
- test_event_analysis_health.py
- test_ai_agent_groq.py
- RedactionReport
- test_admin_cleanup.py
- _filter_event_recipients_for_cooldown
- model_for
- 0001_initial_schema.py
- validate_event_significance_output
- CCWBot
- OpsAgentConfig
- provider_attempts
- 0024_gram_symbol.py
- test_event_alert_composition_investigation.py
- test_agent_workflow_contract.py
- test_event_alert_delivery_quality_regressions.py
- llm/env.py
- news_service.py
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- datetime
- event_analysis.py
- event_alert_benchmark.py
- CCW-20 paired final messages
- event_chart.py
- test_event_alert_postrelease_regressions.py
- test_watchlist_ux.py
- _build_news_candidates
- Context Audit Report
- _fixture
- watchlist.py
- refresh_report_cache_scheduled
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- conftest.py
- test_alert_recipients.py
- test_event_alert_rich_chart_ux.py
- Ops-Agent Service
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- reset_breakers
- telegram_error
- test_event_alert_chart_markers.py
- test_price_service.py
- Event Alert logic
- README.md
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
- db/prices.py
- Market Reports
- Future release-specific checklist
- test-ci.md
- _AlertEvidenceFakeConnection
- CCWBot ChatGPT Project Instructions
- backup_postgres.sh
- application/__init__.py
- bot/__init__.py
- observability/__init__.py
- Product analytics
- bot/config.py
- decimal
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
- _deliver_news_driven_alert_for_symbol
- TransientSessions
- RichDeliveryUncertain
- Development
- test_market_heartbeat.py
- os
- test_llm_config_budgets.py
- ChatGPT / Bridge / Codex Workflow
- test_network_guard.py
- collectors/__init__.py
- ops_agent/__init__.py
- Base
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- db.py
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: extra exports and benchmark
- pkgutil
- utc_now
- reviewer-c-rubric.md
- What You Must Do When Invoked
- extraction-spec.md
- test_alembic_migrations.py
- test_rich_403_preserves_safe_blocked_classification_without_raw_errors
- CCW-41 exploratory Reviewer-C agreement/disagreement
- test_heartbeat_does_not_query_previous_event
- classify_ai_error_reason
- bot/reports.py
- _runner_private.py
- _StructuredRecordBuffer
- .reserve
- SessionFactoryRef
- test_price_handlers.py
- FakeAsyncClient
- /graphify
- build_event_significance_prompt
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- 0008_database_comments.py
- CCW-43 — Evidence-based Event Analysis prompt redesign
- _parse_json
- test_news_driven_alerts.py
- P
- 0027_market_heartbeat_defaults.py
- news_context.py
- schedule_automatic_btc_check
- .__init__
- types
- test_scheduled_ingestion_persists_only_through_existing_intelligence
- CCWBot Operational Report — Unverified (No Production Bundle)
- 0006_payment_recurring_metadata.py
- test_expected_models_match_bot_defaults.py
- CCW-25 — Self-hosted LLM owner decision
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- CCWBot — blind owner disagreement-only replay
- .reset
- Repository-backed Graphify
- CCW-25 research evidence
- operator_prompt.md
- onboarding.py
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- README_RU.md
- fresh200_luna_wait_start.sh
- openai_luna_wait_start.sh
- build_review.py
- db/settings.py
- CCW20_FINAL_MESSAGE_BASELINE_20261026.md
- convert_human_reviews.py
- database.py
- asyncio
- CCW-20 — Offline safety correction of retained Cloudflare final texts

## God Nodes (most connected - your core abstractions)
1. `select()` - 173 edges
2. `Period` - 115 edges
3. `Base` - 100 edges
4. `LLMRouter` - 98 edges
5. `normalize_symbol()` - 88 edges
6. `User` - 68 edges
7. `EventAnalysisDecision` - 65 edges
8. `utc_now()` - 64 edges
9. `run_detectors()` - 64 edges
10. `Alert` - 60 edges

## Surprising Connections (you probably didn't know these)
- `Finding / fix` --references--> `_build_event_alert_payload()`  [INFERRED]
  research/event_alerts/ccw20_final_render_ab_20261026/CCW20_OFFLINE_DIRECTION_GUARD_20261026.md → bot/alerts.py
- `Event Alert chart reference markers (2026-10-26)` --references--> `price()`  [INFERRED]
  docs/alert_logic.md → bot/handlers/price.py
- `Startup configuration log` --references--> `AIProviderRateLimitError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Which 4xx responses fall back` --references--> `AIInvalidJsonError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (225 total, 38 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.14
Nodes (47): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), alert_analysis_result(), event_analysis_result(), factual_market_input() (+39 more)

### Community 1 - "json"
Cohesion: 0.03
Nodes (54): collections, csv, html_parser, json, math, pathlib, re, main() (+46 more)

### Community 2 - "ai_agent_groq.py"
Cohesion: 0.04
Nodes (80): Ground-truth evidence and limitations, Versioned artifacts, AnalysedWindowReference, _build_event_instance_key(), _canonical_decimal_string(), _canonical_event_analysis_context(), _event_analysis_datetime(), _event_analysis_news_age_hours() (+72 more)

### Community 3 - "test_onboarding.py"
Cohesion: 0.19
Nodes (32): ProductEvent, UserCoinSubscription, build_instant_brief(), Render a brief from persisted PriceState only; never call LLMs or providers., Send a first-run BTC brief or a concise returning-user dashboard., send_start_experience(), inspect, build_session() (+24 more)

### Community 4 - "test_db_queries_and_detectors.py"
Cohesion: 0.04
Nodes (64): alembic_migration, alembic_operations, ops_agent_collectors, DbQuery, run_detectors(), Period, sqlite3, _AlertEvidenceFakeEngine (+56 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.08
Nodes (70): _backoff_schedule(), breaker_snapshot(), _BreakerState, _failure_threshold(), is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics. (+62 more)

### Community 6 - "telemetry.py"
Cohesion: 0.07
Nodes (62): asyncio, _json_response_validator(), _validate(), Provider interface and the shared OpenAI-compatible provider implementation.…, BudgetLease, Conservative zero-cost Groq admission control, shared across all call types. A…, current_llm_operation_id(), active_rate_limit_backoff() (+54 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.07
Nodes (56): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report(), market_report_change_chart() (+48 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.09
Nodes (54): Payment, build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date(), _get_payment_attr(), _is_private_update() (+46 more)

### Community 9 - "common.py"
Cohesion: 0.12
Nodes (25): decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, Best-effort deletion of a user's slash command in a private chat., _role_label() (+17 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.17
Nodes (49): PriceState, build_admin_llm_diagnostics_text(), build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health., builtins, build_session_factory(), _event_analysis() (+41 more)

### Community 11 - "sqlalchemy"
Cohesion: 0.03
Nodes (38): alembic, _column_names(), downgrade(), _table_names(), upgrade(), downgrade(), _unique_constraint_names(), upgrade() (+30 more)

### Community 12 - "test_openai_costs.py"
Cohesion: 0.05
Nodes (92): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., _openai_budget_status_line(), Return an admin-safe current UTC-month paid-provider budget summary., _cost(), monthly_budget_usd(), OpenAIBudget, OpenAIBudgetExhausted (+84 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.03
Nodes (110): alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.…, SeverityEvaluation (+102 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.28
Nodes (17): GroqBudget, GroqBudgetExhausted, asyncio, Regression checks for zero-cost Groq pacing, day quota, symbol fairness and…, Other Groq model budgets remain separate from Event Analysis reservations., test_ambiguous_provider_failure_keeps_estimated_token_reservation(), test_day_token_limit_reserves_before_request_and_uses_actual_usage(), test_exhausted_120b_fair_share_does_not_restrict_20b_or_qwen() (+9 more)

### Community 15 - "test_product_analytics.py"
Cohesion: 0.06
Nodes (61): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+53 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (67): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+59 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.11
Nodes (50): generate_report_cache(), _schema_check(), Generate one market-wide LLM report and cache the completed or failed attempt., ask_event_analysis_raw(), ask_market_report_raw(), AISchemaValidationError, Raised when validated JSON does not match the expected schema. ``raw_content``…, _configure() (+42 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (79): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+71 more)

### Community 19 - "replay_event_significance.py"
Cohesion: 0.08
Nodes (53): _groq_json_mode_enabled(), GroqProvider, scripts, blind_packet(), compare_recorded_run(), Compare recorded, already-validated model results without an API call. A…, reconcile(), report() (+45 more)

### Community 20 - "bot/health.py"
Cohesion: 0.10
Nodes (23): aiohttp, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any, datetime, Authoritative last successful Event Analysis time, or None when unavailable.…, Event Analysis health, as a nested block that never changes the top-level… (+15 more)

### Community 21 - "test_event_alert_historical_diagnostics.py"
Cohesion: 0.16
Nodes (24): _build_exact_event_context_fingerprint(), _payload(), parametrize, test_ccw349_invalid_headline_does_not_hide_second_valid_headline(), test_ccw349_news_priority_changes_model_visible_context_and_fingerprint(), test_decimal_json_is_full_precision_json_number_not_float_or_string(), test_exact_context_does_not_reuse_the_ambiguous_change_field_contract(), test_exact_context_ignores_previous_title_not_sent_to_model() (+16 more)

### Community 22 - "cli.py"
Cohesion: 0.13
Nodes (33): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+25 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.11
Nodes (26): pytest_asyncio, add_delivery(), asyncio, parametrize, test_cache_expiring_before_lock_acquisition_is_not_sent(), test_concurrent_checks_send_one_heartbeat_and_reset_timer(), test_delayed_success_uses_completion_not_reservation(), test_event_resets_timer_during_generation_market_fetch() (+18 more)

### Community 24 - "LlmUsageLog"
Cohesion: 0.12
Nodes (32): LlmUsageLog, Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider… (+24 more)

### Community 25 - "event_text.py"
Cohesion: 0.05
Nodes (80): _action_price_levels_supported(), _action_without_negated_technical_levels(), compact_event_alert_possible_action(), compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback() (+72 more)

### Community 26 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 27 - "test_event_analysis_cloudflare_schema.py"
Cohesion: 0.13
Nodes (28): _create_market_heartbeat(), ask_event_alert_render_raw(), ask_event_significance_raw(), ask_market_heartbeat_raw(), ask_news_intelligence_raw(), Return JSON mode and provider-specific schemas for verified model attempts., _structured_response_formats(), llm_operation_scope() (+20 more)

### Community 28 - "llm/config.py"
Cohesion: 0.10
Nodes (30): api_key(), base_url(), event_analysis_operation_budget_seconds(), _format_chain(), is_thinking_model(), _model_from_env(), openai_enabled(), provider_is_configured() (+22 more)

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "domain/premium.py"
Cohesion: 0.21
Nodes (25): _enabled_subscription_by_symbol(), _get_due_market_heartbeat_recipients(), Resolve recipients and preserve queryable reasons for filtered users., resolve_alert_recipient_outcomes(), _as_aware_utc(), can_deliver_market_heartbeat_now(), get_user_plan(), get_user_trial() (+17 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.07
Nodes (72): audit(), positive_age_minutes(), ranking(), main(), _number(), _time(), _aggregate_markdown(), _cli() (+64 more)

### Community 33 - "detectors.py"
Cohesion: 0.12
Nodes (32): consecutive_zero_success_runs(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query(), _incomplete_files_gap() (+24 more)

### Community 34 - "handlers/__init__.py"
Cohesion: 0.13
Nodes (48): acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_admin_system_status_text(), _build_error_logging_status_text(), chat_id(), error_logging_off() (+40 more)

### Community 35 - "admin.py"
Cohesion: 0.10
Nodes (44): schedule_automatic_market_check(), _build_admin_llm_diagnostics_text(), _build_admin_openai_costs_text(), _format_acquisition_link(), _format_admin_alert_settings(), _llm_diagnostics_menu(), _premium_grant_usage_text(), _premium_revoke_usage_text() (+36 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.17
Nodes (31): reports(), _build_report_telegram_message(), send_daily_report_message(), AsyncClock, build_session_factory(), _daily_message(), _empty_report_news_context(), FakeTarget (+23 more)

### Community 37 - "Provider fallback (redundancy)"
Cohesion: 0.17
Nodes (11): Admin OpenAI Platform Costs monitoring (optional, read-only), Current Event Alert Luna-only policy (owner update 2026-10-29), Event Analysis timeout and operation budget, Groq free-tier admission control (Event Analysis), Historical CCW-20 Event Alert provider order (superseded), Historical Gemini 429 quota classification and backoff, LLM Usage Reporting, Ops-Agent LLM Usage Evidence (+3 more)

### Community 38 - "error_file_logging.py"
Cohesion: 0.08
Nodes (47): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports(), _collect_secret_values() (+39 more)

### Community 39 - "LLMRouter"
Cohesion: 0.15
Nodes (57): api_key_env(), LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider, _http_error() (+49 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.04
Nodes (78): EventAnalysisDecision, _event_input_hash(), is_news_centered_event_action(), observed_event_alert_level_action(), Keep trading-oriented guidance conditional and proportionate., Keep monitoring copy focused on market evidence, not supporting headlines., Reject direct trading instructions in every user-visible Event Alert field., Specific safe scenarios for the next interval, not buy/sell signals. (+70 more)

### Community 42 - "User"
Cohesion: 0.15
Nodes (31): User, backfill_blocked_users_from_alerts(), get_active_users_with_alert_preferences(), get_or_create_user(), get_user_by_telegram_chat_id(), get_user_role(), is_telegram_chat_delivery_enabled(), mark_user_bot_blocked() (+23 more)

### Community 43 - "Observability Snippets"
Cohesion: 0.08
Nodes (29): consecutive_failures(), Output, Rules you enforce, What you review, Admin System Status, Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis (+21 more)

### Community 44 - "select"
Cohesion: 0.05
Nodes (99): attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery(), get_event_ai_analysis(), get_last_sent_alert(), get_last_sent_alert_at(), get_last_sent_event_alert_at_for_event_key() (+91 more)

### Community 45 - "bot/news.py"
Cohesion: 0.13
Nodes (35): make_news_key(), Build a stable key for a news item. Links are preferred because RSS titles can…, _dedupe_report_news(), fetch_news_context(), fetch_report_news_context(), within_window(), _has_report_news_identity(), _item_link() (+27 more)

### Community 46 - "AIProviderRateLimitError"
Cohesion: 0.13
Nodes (23): ABC, BaseProvider, ProviderResult, Normalized successful chat-completion result returned by every provider., Common interface for all LLM providers., True when this provider has all configuration required for an attempt., Run one chat completion and return a :class:`ProviderResult` on success.…, AIProviderRateLimitError (+15 more)

### Community 47 - "news_intelligence_service.py"
Cohesion: 0.08
Nodes (47): _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text(), _dedup_hint_is_specific_to_title(), _dedup_terms() (+39 more)

### Community 48 - "db/news.py"
Cohesion: 0.13
Nodes (28): SeenNews, cleanup_seen_news(), count_recent_news_intelligence_llm_calls(), get_cached_news_item_analysis(), get_cooling_failed_news_keys(), get_news_item_by_key(), get_recent_seen_news(), get_retryable_failed_news_items() (+20 more)

### Community 49 - "pytest"
Cohesion: 0.06
Nodes (61): AbstractEventLoop, AppRunner, cleanup_seen_news_job(), DEFAULT_TYPE, schedule_market_heartbeat_generation(), schedule_seen_news_cleanup(), Alert and heartbeat use-case entrypoints., expire_due_premium_trials() (+53 more)

### Community 50 - "router.py"
Cohesion: 0.06
Nodes (46): AsyncOpenAI, bot_services_llm, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., CloudflareProvider, get_provider() (+38 more)

### Community 51 - "normalize_symbol"
Cohesion: 0.16
Nodes (26): _automatic_market_check_job_name(), get_analysed_window_minutes(), _coin_name(), _build_event_analysis_input(), _build_news_driven_event_decision(), _build_news_driven_event_input(), _get_previous_event_alert_for_input(), coin_display_name() (+18 more)

### Community 52 - "test_event_alert_render_provider_chain.py"
Cohesion: 0.26
Nodes (19): call_render(), FakeProvider, good_render(), input_payload(), install(), patch_significance_and_storage(), ProviderError, asyncio (+11 more)

### Community 54 - "_create_event_analysis_decision"
Cohesion: 0.09
Nodes (38): _as_news_only_rejected_decision(), _create_event_analysis_decision(), _render_schema_check(), _significance_schema_check(), _event_alert_render_result_for_validation(), _event_alert_render_validation_reason(), _get_previous_event_alert_id(), _no_alert_decision_from_significance() (+30 more)

### Community 55 - "test_llm_outage_detectors.py"
Cohesion: 0.19
Nodes (23): _detector(), _evidence(), parametrize, Detectors and evidence quality for an LLM-side Event Analysis outage. Covers…, Mimic the collector: newest bucket first, each bucket capped by remaining…, _row(), _simulate_row_cap(), test_a_failure_storm_no_longer_starves_delivered_analyses_of_the_row_cap() (+15 more)

### Community 56 - "manifest.json"
Cohesion: 0.06
Nodes (35): batch_size, batches, path, sha256, case_count, cases, dataset_sha256, operator_prompt_sha256 (+27 more)

### Community 57 - "CCWBot Growth Strategy: 0 -> 1 Premium"
Cohesion: 0.15
Nodes (12): Acquisition limitation, CCWBot Growth Strategy: 0 -> 1 Premium, Change, Current comparable cohort, Decision rule, Experiment 1 - Premium-only onboarding selector, Handoff prompt for a new chat, Primary metric (+4 more)

### Community 58 - "_deliver_market_event_alert"
Cohesion: 0.10
Nodes (41): AlertRecipient, _automatic_delivery_lock(), _deliver_market_event_alert(), _delivery_error_class_name(), _delivery_retry_delay_seconds(), _disable_recipient_if_bot_blocked(), _is_permanent_telegram_delivery_error(), _is_transient_telegram_delivery_error() (+33 more)

### Community 59 - "price_service.py"
Cohesion: 0.12
Nodes (28): _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), _extract_sparkline_prices(), get_btc_market_data(), get_btc_price(), _get_cached_price(), get_coin_price() (+20 more)

### Community 60 - "system_status.py"
Cohesion: 0.11
Nodes (37): _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, ComponentStatus, _container_started_at(), _delivery_failure_category() (+29 more)

### Community 61 - "test_bundle_and_cli.py"
Cohesion: 0.06
Nodes (47): _mark_report_success(), load_state(), parse_timestamp(), Any, datetime, Path, record_collection(), record_report_success() (+39 more)

### Community 62 - "_RecordingProvider"
Cohesion: 0.11
Nodes (18): _CapturingClient, _CapturingCompletions, _mock_openai_admission(), _provider_payload(), asyncio, Captures the kwargs the router passes, without making any provider call., _RecordingProvider, _route() (+10 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.09
Nodes (28): _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, bot_observability, evaluate_state(), failure_escalation_threshold(), max_success_age_seconds(), datetime, In-process health signal for Event Analysis. Event Alerts were fully dead for… (+20 more)

### Community 64 - "test_ai_agent_groq.py"
Cohesion: 0.20
Nodes (8): _set_groq_client(), test_event_alert_render_schema_only_contains_model_generated_fields(), test_event_analysis_prompt_makes_llm_the_market_significance_decider(), test_event_analysis_raw_uses_strict_groq_schema_and_returns_provider_attribution(), test_event_analysis_unknown_groq_model_keeps_json_object_mode(), test_market_heartbeat_raw_uses_strict_groq_schema(), test_market_report_raw_uses_strict_groq_schema(), test_market_report_unknown_groq_model_keeps_json_object_mode()

### Community 65 - "RedactionReport"
Cohesion: 0.07
Nodes (58): dataclasses, collect_health(), Any, collect_local_state(), Any, collect_logs(), _empty_counts(), _line_patterns() (+50 more)

### Community 66 - "test_admin_cleanup.py"
Cohesion: 0.13
Nodes (17): bot_handlers, AsyncFalse, AsyncTrue, _callback_update(), _callback_values(), FakeMessage, FakeQuery, asyncio (+9 more)

### Community 67 - "_filter_event_recipients_for_cooldown"
Cohesion: 0.14
Nodes (19): _count_suppression(), EventRecipientFilterResult, _filter_event_recipients_for_cooldown(), RecipientOutcome, asyncio, test_numeric_family_drift_never_bypasses_four_hour_cooldown(), asyncio, The production 2026-10-12/13 numeric-key path omitted both stored families. (+11 more)

### Community 68 - "model_for"
Cohesion: 0.10
Nodes (24): effective_max_tokens_for(), is_reasoning_model(), model_for(), Resolve the model for a (provider, call_type) pair from env, with defaults., Return the completion budget for one concrete provider attempt. The public…, True when this model identifier is known to accept ``reasoning_effort``., Resolve ``reasoning_effort`` for a (model, call_type) pair, or ``None`` when…, reasoning_effort_for() (+16 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "validate_event_significance_output"
Cohesion: 0.18
Nodes (15): empirical_absolute_move_percentile(), EventSignificanceDecision, Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., validate_event_significance_output(), _payload(), parametrize, test_empirical_absolute_move_percentile_returns_none_for_insufficient_or_missing_data() (+7 more)

### Community 71 - "CCWBot"
Cohesion: 0.10
Nodes (20): Admin System Status, CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables (+12 more)

### Community 72 - "OpsAgentConfig"
Cohesion: 0.08
Nodes (29): ops_agent, BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk. (+21 more)

### Community 73 - "provider_attempts"
Cohesion: 0.10
Nodes (23): global_provider_priority(), _parse_priority_list(), provider_attempts(), provider_priority(), Parse a comma-separated provider list, warning about names that are not…, Resolve the ordered provider chain for a call type. Per-call-type override env…, Return the ordered concrete provider/model attempts for one logical LLM…, Case schema (+15 more)

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
Cohesion: 0.19
Nodes (19): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, test_specific_next_observation_is_not_generic(), _decision(), _market(), parametrize, Regressions from 2026-10-13 delivered Event Alerts. These assertions inspect…, _render() (+11 more)

### Community 78 - "llm/env.py"
Cohesion: 0.13
Nodes (18): _get_int_env(), Substrings that mark a model identifier as reasoning-capable (overridable via…, reasoning_model_markers(), get_choice_env(), get_int_env(), _is_secret_name(), _looks_like_secret_value(), Environment parsing helpers for the LLM subsystem that fail loudly. The… (+10 more)

### Community 79 - "news_service.py"
Cohesion: 0.13
Nodes (23): headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Low-cost, word-boundary-aware prefilter; not an alert decision., Bound provider latency/response size; parse only successfully fetched bytes., Return one usable publisher feed; never fetch the mirror on primary success. (+15 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.15
Nodes (49): LlmOperationOutcome, NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., _entry(), _feed(), asyncio, datetime (+41 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "datetime"
Cohesion: 0.06
Nodes (49): argparse, concurrent_futures, datetime, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., Audit only aggregated benchmark budget and next-call feasibility (no inference). (+41 more)

### Community 83 - "event_analysis.py"
Cohesion: 0.07
Nodes (63): CanonicalEventKey, canonicalize_event_key(), _claim_clause(), _claimed_percent(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal() (+55 more)

### Community 84 - "event_alert_benchmark.py"
Cohesion: 0.07
Nodes (31): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Read-only local check, importlib_util, random, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, Private CCW16 summary: downloads only restricted experiment ledger, never keys…, CCW-29 fresh private holdout: collect real POST-200 market cases via… (+23 more)

### Community 85 - "CCW-20 paired final messages"
Cohesion: 0.09
Nodes (21): 10. ev_3c7f3da2e73e4b90 — ETH, 11. ev_7804adc277bd3333 — GRAM, 12. ev_345fc49db8255adf — GRAM, 13. ev_7b3325d2f2609480 — GRAM, 14. ev_1b39a518ede3c14f — GRAM, 15. ev_6500c5ad9f5364bc — GRAM, 16. ev_4bba21dd01bc8372 — SOL, 17. ev_1ea4cea05b78ed5c — SOL (+13 more)

### Community 86 - "event_chart.py"
Cohesion: 0.11
Nodes (29): bot, bot_alerting, ChartResult, _connectable_now_segment(), _draw_reference_shape(), _font(), _observed(), datetime (+21 more)

### Community 87 - "test_event_alert_postrelease_regressions.py"
Cohesion: 0.22
Nodes (10): parametrize, Production-pattern regression fixtures; synthetic inputs, never recipient data., test_absent_current_move_does_not_invent_price_direction(), test_current_market_move_anchors_directional_identity(), test_documented_weak_move_cases_are_context_not_automatic_triggers(), test_identical_generic_possible_action_is_replaced_by_grounded_fallback(), test_production_style_numeric_directional_keys_collapse_to_semantic_family(), test_significance_prompt_calibrates_materiality_before_novelty_without_a_threshold() (+2 more)

### Community 88 - "test_watchlist_ux.py"
Cohesion: 0.07
Nodes (44): build_subscribe_message(), build_watchlist_message(), build_watchlist_render(), _subscription_by_symbol(), AsyncFalse, AsyncNoop, AsyncTrue, build_session() (+36 more)

### Community 89 - "_build_news_candidates"
Cohesion: 0.24
Nodes (10): _build_news_candidates(), _classify_news_context(), _coin_is_secondary_context(), _news_relevance_reason(), test_btc_is_weak_when_bitcoin_is_secondary_fund_flow_context(), test_btc_soluna_revenue_article_is_weak(), test_direct_btc_support_article_is_user_visible(), test_generic_sentiment_news_is_weak_not_material() (+2 more)

### Community 90 - "Context Audit Report"
Cohesion: 0.07
Nodes (18): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+10 more)

### Community 91 - "_fixture"
Cohesion: 0.14
Nodes (20): _test_verified_groq_routing(), _estimate_tokens(), _fixture(), _measurement(), _production_shape_fixture(), parametrize, Deterministic, clearly labeled fallback: one token per four UTF-8 characters., Regression measurements for the Event Analysis prompt's compact representation. (+12 more)

### Community 92 - "watchlist.py"
Cohesion: 0.18
Nodes (27): is_admin_update(), Update, build_plan_message(), build_user_settings_render(), _current_telegram_user_id(), edit_myplan_message(), edit_user_settings_message(), edit_watchlist_message() (+19 more)

### Community 93 - "refresh_report_cache_scheduled"
Cohesion: 0.13
Nodes (21): schedule_report_cache_generation(), Market report use-case entrypoints., generate_daily_report_cache_job(), generate_weekly_report_cache_job(), Scheduled cache refresh: regenerate unless the cache stays fresh past the grace…, One recovery attempt after a scheduled failure; no recurring retry storm., refresh_report_cache_scheduled(), _schedule_failed_report_retry() (+13 more)

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.17
Nodes (11): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Log pattern counting, News-candidate signal (+3 more)

### Community 96 - "conftest.py"
Cohesion: 0.36
Nodes (7): _real_socket, _guarded_create_connection(), _guarded_getaddrinfo(), _GuardedSocket, _is_loopback(), _is_loopback_address(), _raise_external_network_block()

### Community 97 - "test_alert_recipients.py"
Cohesion: 0.24
Nodes (9): FakeSession, asyncio, test_event_alert_eligibility_ignores_market_heartbeat_preference(), fake_get_active_users_with_alert_preferences(), test_event_recipient_resolution_is_isolated_from_trial_expiry_failures(), test_get_alert_recipients_deduplicates_active_db_users(), fake_get_active_users_with_alert_preferences(), test_get_alert_recipients_skips_non_btc_events() (+1 more)

### Community 98 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.16
Nodes (16): prepare_chart_points(), Never extrapolate over missing time or label a partial day as 24h., Event-specific references are opt-in; Heartbeat is exactly the old chart., render_price_chart(), _observations(), Event Alert UX, chart evidence and single-send fallback contracts., test_chart_accepts_normal_30_minute_scheduler_jitter_but_rejects_stale(), test_chart_downtime_selects_latest_gap_free_run_without_inventing_prices() (+8 more)

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

### Community 105 - "reset_breakers"
Cohesion: 0.50
Nodes (4): Clear all breaker state (tests and controlled restarts)., reset_breakers(), _isolate_llm_breaker_state(), _reset_state()

### Community 106 - "telegram_error"
Cohesion: 0.31
Nodes (8): handle_application_error(), Global python-telegram-bot error handler. Log-only: never sends anything to…, telegram_error, asyncio, parametrize, Global PTB error handler: concise WARNING for transient network errors, ERROR…, test_non_network_error_logs_error_with_traceback(), test_transient_network_error_logs_one_concise_warning()

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.33
Nodes (17): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+9 more)

### Community 108 - "test_price_service.py"
Cohesion: 0.09
Nodes (31): _extract_ton_coin_data_from_simple_price(), get_coin_market_data_batch(), Fetch market data for supported symbols with one CoinGecko request. Missing…, Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., _set_cached_price(), clean_price_caches(), clear_price_caches(), FakeClient (+23 more)

### Community 109 - "Event Alert logic"
Cohesion: 0.08
Nodes (24): CCW-20: meaningful observed-price scenarios, Eight mandatory acceptance gates, Event Alert 24h metric and title (2026-10-29), Event Alert acceptance criteria (approved 2026-10-16), Event Alert chart reference markers (2026-10-26), Event Alert logic, Event Alert message quality contract, Execution and release gates (+16 more)

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
Cohesion: 0.22
Nodes (18): _prepare_event_alert_chart(), Build one shared PNG before fanout. No recipient data enters this image., _resolve_window_market_context(), _save_price_state(), PriceSnapshot, UserSymbolAlertState, get_price_snapshots_since(), get_price_state() (+10 more)

### Community 114 - "Market Reports"
Cohesion: 0.25
Nodes (7): Guardrails, Market Data, Market Reports, News Selection, Restored analysis and cache content revision, Telegram Templates, summary()

### Community 115 - "Future release-specific checklist"
Cohesion: 0.14
Nodes (13): Before Opening The PR, Event Alert Luna-only release (owner-approved 2026-10-29), Future release-specific checklist, LLM routing v2 free-only rollout, Mandatory ops-agent image and host-wrapper steps, Observability changes, PR #296: Event Analysis medium reasoning, PR Description Must Include (+5 more)

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

### Community 128 - "bot/config.py"
Cohesion: 0.13
Nodes (11): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids(), Centralized configuration loaded from environment variables. Notes about key…, test_admin_user_ids_ignore_empty_whitespace_and_invalid_values() (+3 more)

### Community 129 - "decimal"
Cohesion: 0.24
Nodes (11): calculate_price_change_percent(), is_cooldown_active(), datetime, Decimal, Core alert-rule helpers used by automatic market checks., Calculate a percent change without mixing binary floats and ``Decimal`` values., Return True while a previous alert is still inside the cooldown window., decimal (+3 more)

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
Cohesion: 0.14
Nodes (18): Intercept only messages sent in the scope of a manual command/callback., _tracking(), TransientBot, with_close_button(), ExtBot, fetch(), asyncio, parametrize (+10 more)

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
Cohesion: 0.18
Nodes (37): UserPremiumSubscription, UserPremiumTrial, activate_premium_from_telegram_stars_payment(), _activate_premium_from_telegram_stars_payment_locked(), ensure_default_coin_subscriptions(), expire_due_premium_trials(), get_payment_by_provider_id(), get_user_premium_subscription() (+29 more)

### Community 145 - "_deliver_news_driven_alert_for_symbol"
Cohesion: 0.31
Nodes (9): _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _news_driven_identity(), _deliver_news_driven_alert_for_symbol(), _get_or_create_news_driven_market_event(), _heartbeat_related_news(), _news_driven_numeric_context(), _primary_suppression_reason() (+1 more)

### Community 147 - "RichDeliveryUncertain"
Cohesion: 0.16
Nodes (10): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert() (+2 more)

### Community 148 - "Development"
Cohesion: 0.25
Nodes (8): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.06
Nodes (70): _build_market_heartbeat_id(), MarketHeartbeatDecision, MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body() (+62 more)

### Community 150 - "os"
Cohesion: 0.08
Nodes (21): asyncpg, bot_services, build_llm_messages(), graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), copy, ctypes, dotenv (+13 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.11
Nodes (33): log_resolved_configuration(), max_tokens_for(), Resolve the completion-token budget for a call type. The current ``LLM_*`` name…, Log the resolved LLM configuration once, at startup. This is the signal that…, parametrize, Per-call-type token budgets, reasoning effort, loud env parsing, and the…, _startup_log_messages(), test_bad_value_warns_once_not_once_per_call() (+25 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "test_network_guard.py"
Cohesion: 0.22
Nodes (4): socket, parametrize, Guards the test-suite network safety net installed in tests/conftest.py. If…, test_fallback_provider_hosts_are_blocked()

### Community 156 - "Base"
Cohesion: 0.12
Nodes (37): _build_event_analysis_id(), AlertRecipientResolution, automatic_price_check(), get_alert_recipients(), _get_or_create_event_alert_market_event(), _merge_existing_event_analysis_payload(), Return active market symbols independently of current recipient eligibility., Resolve eligible recipients once for one market event. (+29 more)

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
Cohesion: 0.27
Nodes (13): _alert_evidence_windows(), _collect_alert_repetition_rows(), collect_db(), _collector_error(), _jsonable(), Any, datetime, Exception (+5 more)

### Community 162 - "graphify reference: extra exports and benchmark"
Cohesion: 0.20
Nodes (9): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000) (+1 more)

### Community 164 - "utc_now"
Cohesion: 0.12
Nodes (32): MarketReport, datetime, Return timezone-aware UTC timestamp., utc_now(), get_latest_market_report(), AsyncSession, datetime, Market report cache persistence. Belongs here: daily/weekly market report cache… (+24 more)

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.06
Nodes (47): alembic_config, alembic_script, ast, automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, importlib (+39 more)

### Community 169 - "test_rich_403_preserves_safe_blocked_classification_without_raw_errors"
Cohesion: 0.11
Nodes (6): parametrize, test_integrity_conflict_preserves_terminal_delivery_reservation(), test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post(), test_rich_confirmed_telegram_rejections(), post()

### Community 170 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 171 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 172 - "classify_ai_error_reason"
Cohesion: 0.06
Nodes (45): AIInvalidJsonError, AllProvidersFailedError, LLMRateLimitBackoffActive, datetime, Exception, RuntimeError, Provider-agnostic LLM error types shared across the provider router. These were…, Raised when a provider/model is already in temporary rate-limit backoff. (+37 more)

### Community 173 - "bot/reports.py"
Cohesion: 0.07
Nodes (47): MarketReportDecision, _build_daily_report_message(), _build_deterministic_report_decision(), _build_market_report_input(), _build_report_coin_payload(), _build_weekly_breadth(), _build_weekly_coin_context(), _build_weekly_context() (+39 more)

### Community 174 - "_runner_private.py"
Cohesion: 0.28
Nodes (15): call_once(), classify(), fail(), main(), persist(), datetime, quota_allows(), Finite direct-provider CCW-16 canary runner; Python stdlib only. This script… (+7 more)

### Community 175 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 178 - "test_price_handlers.py"
Cohesion: 0.32
Nodes (14): CoinGeckoRateLimitError, Exception, Raised when CoinGecko returns HTTP 429., _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users(), test_price_maps_provider_errors_to_safe_user_messages() (+6 more)

### Community 180 - "/graphify"
Cohesion: 0.09
Nodes (18): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+10 more)

### Community 181 - "build_event_significance_prompt"
Cohesion: 0.13
Nodes (19): build_event_significance_prompt(), Stage verified model-visible pilot calls into isolated CCW-16 workspace. No…, CCW-43 offline source verification, paired scoring, and restricted case error…, build_prompt(), check_production_parity(), inspect_private_frozen(), instruction(), main() (+11 more)

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.33
Nodes (5): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps

### Community 183 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 184 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 185 - "_parse_json"
Cohesion: 0.29
Nodes (6): _parse_json(), Parse a JSON-object response without relaxing schema validation., parametrize, test_event_analysis_prompt_preserves_subpercent_values_as_percentages(), test_parse_json_keeps_object_only_contract(), test_parse_json_handles_whitespace_and_invalid_text()

### Community 186 - "test_news_driven_alerts.py"
Cohesion: 0.47
Nodes (5): _load_news_driven_alert_candidates(), asyncio, Regression coverage for the disabled standalone-news Event Alert path., test_news_driven_alerts_warning_logs_once_not_per_cycle(), test_news_driven_flag_cannot_bypass_product_policy()

### Community 188 - "0027_market_heartbeat_defaults.py"
Cohesion: 0.70
Nodes (4): downgrade(), _has_alert_frequency_column(), _set_default(), upgrade()

### Community 189 - "news_context.py"
Cohesion: 0.11
Nodes (32): _candidate_news_relevance_label(), classify_news_relevance(), filter_news_for_symbol(), _format_candidate_news(), _has_gram_crypto_context(), _is_clearly_market_wide_news(), is_generic_news_item(), is_material_news_item() (+24 more)

### Community 190 - "schedule_automatic_btc_check"
Cohesion: 0.40
Nodes (3): Compatibility wrapper for older imports; schedules the market-wide check., schedule_automatic_btc_check(), test_legacy_automatic_btc_scheduler_alias_uses_market_job_name()

### Community 192 - "types"
Cohesion: 0.17
Nodes (17): is_admin_user(), sync_user_from_update(), asyncio, SessionContext, test_admin_check_ignores_invalid_user_id(), test_db_admin_check_accepts_second_admin_from_combined_allowlist(), test_db_admin_check_rejects_db_admin_when_env_id_does_not_match(), test_db_admin_check_rejects_env_admin_without_db_admin_role() (+9 more)

### Community 194 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 195 - "0006_payment_recurring_metadata.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 197 - "CCW-25 — Self-hosted LLM owner decision"
Cohesion: 0.25
Nodes (7): Actual local screen, CCW-25 — Self-hosted LLM owner decision, Low-risk next decision, Monthly EUR / DKK comparison, Specific candidates and serving stack, Volume sensitivity and break-even, What is measured

### Community 198 - "CCW-41 owner-reviewed significance reference v1"
Cohesion: 0.29
Nodes (6): Asset-specific labels, CCW-41 owner-reviewed significance reference v1, Historical bot against reference (selected benchmark only), How disputed labels changed, Using this reference for future model prompts, Warrant distributions

### Community 199 - "_working_code_backup.py"
Cohesion: 0.15
Nodes (31): event_alert_benchmark, _aggregate_markdown(), _cli(), compare_reviewers(), _field_exists(), _group_metrics(), import_results(), _label_counts() (+23 more)

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

### Community 210 - "onboarding.py"
Cohesion: 0.09
Nodes (40): build_admin_back_keyboard(), build_admin_keyboard(), build_admin_logs_keyboard(), build_admin_premium_keyboard(), build_first_run_brief_keyboard(), build_my_plan_keyboard(), build_onboarding_customize_keyboard(), build_onboarding_keyboard() (+32 more)

### Community 223 - "build_review.py"
Cohesion: 0.32
Nodes (11): candidate(), canon(), context(), csvwrite(), main(), Private read-only CCWBot market benchmark and independent review CSV exporter., run_psql(), safe() (+3 more)

### Community 226 - "db/settings.py"
Cohesion: 0.42
Nodes (9): AppSettings, UserSettings, _get_app_settings_row(), get_or_create_app_settings(), get_or_create_user_settings(), AsyncSession, Global and legacy per-user settings persistence. Belongs here: app-wide alert…, update_app_settings() (+1 more)

### Community 233 - "convert_human_reviews.py"
Cohesion: 0.42
Nodes (8): finalize_reconciled(), labels_for(), main(), normalize_yes_no(), Convert two completed independent reviewer CSV sets to PR1 benchmark labels.…, rows(), score_disagreements(), validate_phase()

### Community 234 - "database.py"
Cohesion: 0.06
Nodes (32): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), _collapse_whitespace(), _normalize_news_link(), Database infrastructure for optional PostgreSQL runtime storage. (+24 more)

### Community 235 - "asyncio"
Cohesion: 0.11
Nodes (8): asyncio, test_event_chart_file_id_reused_across_recipients_in_one_dispatch(), test_heartbeat_falls_back_to_styled_html_if_rich_adapter_has_no_token(), test_rich_ambiguous_error_never_falls_back_or_retries(), test_rich_confirmed_bad_request_falls_back_once(), test_rich_httpx_transport_uncertainty_prevents_fallback(), test_transport_reuses_file_id_and_handles_valid_response(), post()

### Community 238 - "CCW-20 — Offline safety correction of retained Cloudflare final texts"
Cohesion: 0.33
Nodes (5): CCW-20 — Offline safety correction of retained Cloudflare final texts, Concrete verified example — ETH (`ev_0ab71234c9080ecc`), Finding / fix, Reproducible offline check, What this test does not prove

## Knowledge Gaps
- **443 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+438 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1707 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **38 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `Observability Snippets` to `Ops-Agent Service`, `asyncio`, `CCWBot Ops-Agent Report Analysis`, `RichDeliveryUncertain`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `test_event_alert_rich_chart_ux.py`, `test_rich_market_report_delivery.py`, `asyncio`, `Observability Snippets`, `bot/alerts.py`, `bot/reports.py`, `_deliver_market_event_alert`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `select()` connect `select` to `test_onboarding.py`, `test_telegram_stars_payments.py`, `test_system_status.py`, `test_openai_costs.py`, `test_product_analytics.py`, `db/premium.py`, `test_market_heartbeat.py`, `test_heartbeat_silence.py`, `LlmUsageLog`, `Base`, `utc_now`, `test_report_cooldowns.py`, `test_event_alert_pipeline.py`, `User`, `bot/news.py`, `news_intelligence_service.py`, `db/news.py`, `.reserve`, `router.py`, `_deliver_market_event_alert`, `system_status.py`, `test_news_intelligence_service.py`, `test_watchlist_ux.py`, `build_review.py`, `db/settings.py`, `db/prices.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 170 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 170 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _443 weakly-connected nodes found - possible documentation gaps or missing edges._