# Graph Report - CCWBot  (2026-10-30)

## Corpus Check
- 657 files · ~1,153,940 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 34 file(s) not represented in the graph (top: .toml 12, (none) 8, .csv 7)

## Summary
- 5872 nodes · 17360 edges · 226 communities (191 shown, 35 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1444 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2be29e9e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- json
- event_identity.py
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
- test_acquisition_link_workflow.py
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- event_alert_benchmark.py
- EventAnalysisDecision
- types
- cli.py
- test_heartbeat_silence.py
- LlmUsageLog
- event_text.py
- properties
- ai_agent_groq.py
- test_product_analytics.py
- validate_market_report_output
- properties
- onboarding.py
- ccw41_reviewer_c_audit.py
- detectors.py
- admin.py
- schedule_automatic_market_check
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
- test_event_analysis_free_fallback.py
- news_intelligence_service.py
- db/news.py
- callbacks.py
- test_llm_rate_limit_backoff.py
- normalize_symbol
- test_event_alert_render_provider_chain.py
- log
- test_event_alert_render_reliability.py
- test_llm_outage_detectors.py
- manifest.json
- CCWBot Growth Strategy: 0 -> 1 Premium
- User
- price_service.py
- system_status.py
- test_bundle_and_cli.py
- test_seen_news_dedup.py
- test_event_analysis_health.py
- test_news_intelligence_schema.py
- RedactionReport
- button_router
- test_event_alert_pr2_cooldown.py
- canonicalize_event_key
- 0001_initial_schema.py
- validate_event_significance_output
- CCWBot
- BundleWriter
- datetime
- 0024_gram_symbol.py
- test_event_alert_composition_investigation.py
- test_agent_workflow_contract.py
- test_event_alert_delivery_quality_regressions.py
- test_heartbeat_postgres.py
- news_service.py
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- time
- event_analysis.py
- get_or_create_user
- CCW-20 paired final messages
- event_chart.py
- test_event_alert_owner_copy_news_regressions.py
- asyncio
- FakeResponse
- Context Audit Report
- _fixture
- test_watchlist_ux.py
- utc_now
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- test_event_alert_render_grounded_copy.py
- automatic_price_check
- test_event_alert_rich_chart_ux.py
- Ops-Agent Service
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- user.py
- RichDeliveryUncertain
- test_event_alert_chart_markers.py
- test_price_service.py
- Event Alert logic
- Documentation
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
- _build_event_analysis_input
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
- 0028_premium_trials.py
- TransientSessions
- LLMJsonResult
- Development
- test_market_heartbeat.py
- os
- test_llm_config_budgets.py
- ChatGPT / Bridge / Codex Workflow
- save_llm_usage_log
- collectors/__init__.py
- ops_agent/__init__.py
- test_multicoin_alerts.py
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- schemas.py
- graphify reference: GitHub clone and cross-repo merge
- price.py
- pkgutil
- db/reports.py
- reviewer-c-rubric.md
- What You Must Do When Invoked
- extraction-spec.md
- test_alembic_migrations.py
- asyncio
- CCW-41 exploratory Reviewer-C agreement/disagreement
- test_heartbeat_does_not_query_previous_event
- .__init__
- bot/reports.py
- _runner_private.py
- _StructuredRecordBuffer
- build_llm_messages
- runtime/state.py
- test_price_handlers.py
- FakeAsyncClient
- /graphify
- _event_significance_prompt_payload
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- 0008_database_comments.py
- CCW-43 — Evidence-based Event Analysis prompt redesign
- test_report_llm_exhaustion_recovery.py
- test_news_driven_alerts.py
- check_owner_html.py
- 0025_llm_operation_correlation.py
- news_context.py
- Repository Source of Truth
- .__init__
- unittest_mock
- test_news_ingestion.py
- CCWBot Operational Report — Unverified (No Production Bundle)
- 0003_premium_watchlist_foundation.py
- 0026_growth_analytics.py
- CCW-25 — Self-hosted LLM owner decision
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- CCWBot — blind owner disagreement-only replay
- save_llm_operation_outcome
- Repository-backed Graphify
- CCW-25 research evidence
- .__init__
- operator_prompt.md
- handlers/reports.py
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- README_RU.md
- fresh200_luna_wait_start.sh
- openai_luna_wait_start.sh
- build_review.py
- db/settings.py
- CCW20_FINAL_MESSAGE_BASELINE_20261026.md
- enrich_quality_first_history.py
- database.py
- test_transport_reuses_file_id_and_handles_valid_response
- CCW-20 — Offline safety correction of retained Cloudflare final texts

## God Nodes (most connected - your core abstractions)
1. `select()` - 173 edges
2. `Period` - 115 edges
3. `Base` - 100 edges
4. `LLMRouter` - 98 edges
5. `normalize_symbol()` - 89 edges
6. `User` - 68 edges
7. `EventAnalysisValidationError` - 66 edges
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
- `Read-only local check` --references--> `load_frozen()`  [INFERRED]
  benchmarks/ccw15-v1/README.md → scripts/event_alert_benchmark.py

## Import Cycles
- None detected.

## Communities (226 total, 35 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.14
Nodes (47): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), alert_analysis_result(), event_analysis_result(), factual_market_input() (+39 more)

### Community 1 - "json"
Cohesion: 0.04
Nodes (35): collections, json, math, pathlib, re, main(), Verify completed research, reconcile metrics and fill the decision reports., sha() (+27 more)

### Community 2 - "event_identity.py"
Cohesion: 0.04
Nodes (57): AnalysedWindowReference, _canonical_decimal_string(), _event_analysis_datetime(), _event_analysis_news_age_hours(), _json_dumps(), datetime, Decimal, Pure Event Alert identity, precision, and scheduling helpers. (+49 more)

### Community 3 - "test_onboarding.py"
Cohesion: 0.16
Nodes (39): ProductEvent, UserCoinSubscription, build_instant_brief(), build_onboarding_message(), build_returning_user_message(), handle_onboarding_callback(), _premium_intent_count(), InlineKeyboardMarkup (+31 more)

### Community 4 - "test_db_queries_and_detectors.py"
Cohesion: 0.04
Nodes (65): alembic_migration, alembic_operations, ops_agent_collectors, _alert_evidence_windows(), datetime, run_detectors(), Period, sqlite3 (+57 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.06
Nodes (82): _backoff_schedule(), breaker_snapshot(), _BreakerState, _failure_threshold(), is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics. (+74 more)

### Community 6 - "telemetry.py"
Cohesion: 0.05
Nodes (88): ABC, _validate(), bot_services_llm, BaseProvider, Provider interface and the shared OpenAI-compatible provider implementation.…, Common interface for all LLM providers., True when this provider has all configuration required for an attempt., AIInvalidJsonError (+80 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.12
Nodes (33): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), market_report_change_chart(), _percent_label(), ImageDraw (+25 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.09
Nodes (56): Payment, Application, register_bot_handlers(), build_premium_activation_keyboard(), build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime() (+48 more)

### Community 9 - "common.py"
Cohesion: 0.09
Nodes (36): _format_admin_alert_settings(), _callback_command_update(), decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,… (+28 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.17
Nodes (47): PriceState, build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., builtins, build_session_factory(), _event_analysis(), _final_failed_alert(), _now() (+39 more)

### Community 11 - "sqlalchemy"
Cohesion: 0.03
Nodes (26): alembic, downgrade(), _unique_constraint_names(), upgrade(), downgrade(), _table_names(), upgrade(), _column_names() (+18 more)

### Community 12 - "test_openai_costs.py"
Cohesion: 0.05
Nodes (91): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., _build_admin_openai_costs_text(), _cost(), monthly_budget_usd(), OpenAIBudget, OpenAIBudgetExhausted, OpenAIBudgetLease (+83 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.04
Nodes (93): alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.…, SeverityEvaluation (+85 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.13
Nodes (25): BudgetLease, _Charge, GroqBudget, GroqBudgetExhausted, datetime, Conservative zero-cost Groq admission control, shared across all call types. A…, Test-only reset; production restarts reload persisted usage., GroqProvider (+17 more)

### Community 15 - "test_acquisition_link_workflow.py"
Cohesion: 0.10
Nodes (32): create_acquisition_link(), _is_acquisition_link_code_collision(), Create one collision-safe, validated operator acquisition link., AcquisitionLink, AcquisitionLinkMetadata, AttributionLinkToken, build_acquisition_telegram_url(), generate_acquisition_link_code() (+24 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (67): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+59 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.11
Nodes (49): _schema_check(), generate_report_cache(), _schema_check(), Generate one market-wide LLM report and cache the completed or failed attempt., AISchemaValidationError, Raised when validated JSON does not match the expected schema. ``raw_content``…, _configure(), ContentProvider (+41 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (79): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+71 more)

### Community 19 - "event_alert_benchmark.py"
Cohesion: 0.06
Nodes (70): random, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, CCW-29 fresh private holdout: collect real POST-200 market cases via…, choose(), Freeze fresh 200 real CCWBot market cases, excluding both earlier sets;…, scripts, blind_packet(), canonical_json() (+62 more)

### Community 20 - "EventAnalysisDecision"
Cohesion: 0.09
Nodes (43): EventAnalysisDecision, with_canonical_event_key(), _event_instance_key_for_decision(), _stable_related_news_ids(), _as_news_only_rejected_decision(), _build_event_alert_html_message(), _build_event_alert_payload(), _render_schema_check() (+35 more)

### Community 21 - "types"
Cohesion: 0.09
Nodes (36): _build_exact_event_context_fingerprint(), build_event_significance_prompt(), _payload(), parametrize, test_ccw349_invalid_headline_does_not_hide_second_valid_headline(), test_ccw349_news_priority_changes_model_visible_context_and_fingerprint(), test_decimal_json_is_full_precision_json_number_not_float_or_string(), test_exact_context_does_not_reuse_the_ambiguous_change_field_contract() (+28 more)

### Community 22 - "cli.py"
Cohesion: 0.14
Nodes (30): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+22 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.10
Nodes (29): save_alert(), pytest_asyncio, fake_get_active_users_with_alert_preferences(), add_delivery(), delivery_db(), asyncio, parametrize, test_cache_expiring_before_lock_acquisition_is_not_sent() (+21 more)

### Community 24 - "LlmUsageLog"
Cohesion: 0.11
Nodes (33): LlmUsageLog, Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider… (+25 more)

### Community 25 - "event_text.py"
Cohesion: 0.06
Nodes (65): _action_price_levels_supported(), compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback(), _has_final_reference_disclaimer(), _has_persistent_snapshot_direction() (+57 more)

### Community 26 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 27 - "ai_agent_groq.py"
Cohesion: 0.05
Nodes (61): _create_market_heartbeat(), ask_event_alert_render_raw(), ask_event_analysis_raw(), ask_event_significance_raw(), ask_market_heartbeat_raw(), ask_market_report_raw(), ask_news_intelligence_raw(), build_event_analysis_prompt() (+53 more)

### Community 28 - "test_product_analytics.py"
Cohesion: 0.13
Nodes (28): AcquisitionAttribution, capture_first_touch_attribution(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence., List a bounded set of links which may currently attribute a start., Resolve an active opaque deep-link token into configured attribution. (+20 more)

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "onboarding.py"
Cohesion: 0.13
Nodes (31): _as_aware_utc(), can_deliver_market_heartbeat_now(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active() (+23 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.07
Nodes (73): audit(), positive_age_minutes(), ranking(), main(), _number(), Read-only assessment of sanitized Event Analysis decisions; NOT an LLM replay.…, _time(), _aggregate_markdown() (+65 more)

### Community 33 - "detectors.py"
Cohesion: 0.11
Nodes (34): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+26 more)

### Community 34 - "admin.py"
Cohesion: 0.17
Nodes (42): acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_admin_llm_diagnostics_text(), _build_admin_system_status_text(), _build_error_logging_status_text(), chat_id() (+34 more)

### Community 35 - "schedule_automatic_market_check"
Cohesion: 0.08
Nodes (34): _automatic_market_check_job_name(), cleanup_seen_news_job(), _delivery_retry_delay_seconds(), _is_permanent_telegram_delivery_error(), _is_transient_telegram_delivery_error(), Application, BaseException, DEFAULT_TYPE (+26 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.17
Nodes (35): MarketReport, reports(), _build_report_telegram_message(), get_or_generate_report(), _is_completed_report(), One shared refresh on old content; never fan out LLM/RSS per recipient., send_daily_report_message(), AsyncClock (+27 more)

### Community 37 - "Provider fallback (redundancy)"
Cohesion: 0.17
Nodes (11): Admin OpenAI Platform Costs monitoring (optional, read-only), Current Event Alert Luna-only policy (owner update 2026-10-29), Event Analysis timeout and operation budget, Groq free-tier admission control (Event Analysis), Historical CCW-20 Event Alert provider order (superseded), Historical Gemini 429 quota classification and backoff, LLM Usage Reporting, Ops-Agent LLM Usage Evidence (+3 more)

### Community 38 - "error_file_logging.py"
Cohesion: 0.06
Nodes (58): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., bot_observability, _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports() (+50 more)

### Community 39 - "LLMRouter"
Cohesion: 0.15
Nodes (57): AllProvidersFailedError, Raised when every provider in the fallback chain has been exhausted.…, LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider (+49 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.06
Nodes (55): _event_input_hash(), _create_event_analysis_decision(), _event_alert_presentation_title(), _event_alert_render_validation_reason(), _event_context_fingerprint(), _get_recent_event_analysis_decision_by_exact_context(), _has_non_flat_analysed_market_context(), _llm_no_alert_decision_reason() (+47 more)

### Community 42 - "users.py"
Cohesion: 0.16
Nodes (19): backfill_blocked_users_from_alerts(), get_active_users_with_alert_preferences(), get_active_users_with_chat_ids(), get_user_by_telegram_chat_id(), get_user_role(), is_telegram_chat_delivery_enabled(), mark_user_bot_blocked(), AsyncSession (+11 more)

### Community 43 - "Observability Snippets"
Cohesion: 0.08
Nodes (29): consecutive_failures(), Output, Rules you enforce, What you review, Admin System Status, Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis (+21 more)

### Community 44 - "select"
Cohesion: 0.08
Nodes (66): _save_market_heartbeat_attempt(), attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery(), get_last_sent_alert(), get_last_sent_alert_at(), get_last_sent_event_alert_at_for_event_key() (+58 more)

### Community 45 - "bot/news.py"
Cohesion: 0.13
Nodes (32): _dedupe_report_news(), fetch_report_news_context(), within_window(), _has_report_news_identity(), _incident_phase(), _item_link(), _item_published_at(), _item_related_symbols() (+24 more)

### Community 46 - "test_event_analysis_free_fallback.py"
Cohesion: 0.37
Nodes (13): _configure(), _event_call(), _http_error(), asyncio, parametrize, Event Analysis provider redundancy, no live external requests., StubProvider, test_cloudflare_credentials_are_optional() (+5 more)

### Community 47 - "news_intelligence_service.py"
Cohesion: 0.09
Nodes (38): get_cached_news_item_analysis(), Return a reusable structured news analysis for the exact model-aware input hash., _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text() (+30 more)

### Community 48 - "db/news.py"
Cohesion: 0.13
Nodes (27): SeenNews, cleanup_seen_news(), count_recent_news_intelligence_llm_calls(), get_cooling_failed_news_keys(), get_news_item_by_key(), get_recent_seen_news(), get_retryable_failed_news_items(), mark_news_items_seen() (+19 more)

### Community 49 - "callbacks.py"
Cohesion: 0.08
Nodes (43): AbstractEventLoop, asyncio, bot_handlers, Central callback-query router for Telegram inline keyboards., send_manual_rate_limit_message(), send_price_message(), bot_runtime, initialize_runtime() (+35 more)

### Community 50 - "test_llm_rate_limit_backoff.py"
Cohesion: 0.06
Nodes (44): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions… (+36 more)

### Community 51 - "normalize_symbol"
Cohesion: 0.09
Nodes (40): _build_event_instance_key(), _build_market_heartbeat_id(), _build_news_driven_event_instance_key(), _event_instance_bucket(), _stable_float(), Escape all model/news wording; only safely link explicit HTTP(S) sources., _report_coin_icon_html(), _safe_rich_line() (+32 more)

### Community 52 - "test_event_alert_render_provider_chain.py"
Cohesion: 0.26
Nodes (19): call_render(), FakeProvider, good_render(), input_payload(), install(), patch_significance_and_storage(), ProviderError, asyncio (+11 more)

### Community 53 - "log"
Cohesion: 0.09
Nodes (23): expire_due_premium_trials(), process_due_trial_expiries(), Application, DEFAULT_TYPE, Independent scheduling for durable Premium-trial lifecycle transitions., Lazy import keeps the scheduler independent of database compatibility exports., Record due expiry transitions without coupling them to alert processing., schedule_premium_trial_expiry() (+15 more)

### Community 54 - "test_event_alert_render_reliability.py"
Cohesion: 0.24
Nodes (17): build_event_alert_render_prompt(), _payload(), asyncio, parametrize, Regression contracts for production Event Alert Render rejection categories.…, test_ccw20_render_copy_asks_for_meaningful_price_scenarios(), test_ccw20_render_prompt_missing_context_fails_closed(), test_flat_news_led_input_cannot_be_recovered_as_market_alert() (+9 more)

### Community 55 - "test_llm_outage_detectors.py"
Cohesion: 0.19
Nodes (23): _detector(), _evidence(), parametrize, Detectors and evidence quality for an LLM-side Event Analysis outage. Covers…, Mimic the collector: newest bucket first, each bucket capped by remaining…, _row(), _simulate_row_cap(), test_a_failure_storm_no_longer_starves_delivered_analyses_of_the_row_cap() (+15 more)

### Community 56 - "manifest.json"
Cohesion: 0.06
Nodes (35): batch_size, batches, path, sha256, case_count, cases, dataset_sha256, operator_prompt_sha256 (+27 more)

### Community 57 - "CCWBot Growth Strategy: 0 -> 1 Premium"
Cohesion: 0.15
Nodes (12): Acquisition limitation, CCWBot Growth Strategy: 0 -> 1 Premium, Change, Current comparable cohort, Decision rule, Experiment 1 - Premium-only onboarding selector, Handoff prompt for a new chat, Primary metric (+4 more)

### Community 58 - "User"
Cohesion: 0.21
Nodes (16): User, build_session_factory(), create_market_event(), create_user(), asyncio, test_backfill_marks_historical_blocked_users_and_is_idempotent(), test_bad_request_delivery_failure_is_not_retried(), test_blocked_telegram_error_disables_user_and_keeps_failed_alert() (+8 more)

### Community 59 - "price_service.py"
Cohesion: 0.12
Nodes (30): _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), _extract_sparkline_prices(), get_btc_market_data(), get_btc_price(), _get_cached_price(), get_coin_price() (+22 more)

### Community 60 - "system_status.py"
Cohesion: 0.10
Nodes (44): _age_label(), _ai_health(), _as_utc(), build_admin_llm_diagnostics_text(), build_admin_llm_summary_html(), ComponentHealth, ComponentStatus, _container_started_at() (+36 more)

### Community 61 - "test_bundle_and_cli.py"
Cohesion: 0.05
Nodes (64): ops_agent, _mark_report_success(), _validate_bundle(), OpsAgentLimits, load_state(), parse_timestamp(), Any, datetime (+56 more)

### Community 62 - "test_seen_news_dedup.py"
Cohesion: 0.13
Nodes (32): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), get_event_ai_analysis(), get_or_create_market_event(), Decimal, Return the market event for event_instance_key, creating it when needed., Return an existing AI analysis for the event/input pair if present. (+24 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.05
Nodes (53): aiohttp, AppRunner, _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any (+45 more)

### Community 64 - "test_news_intelligence_schema.py"
Cohesion: 0.13
Nodes (19): ProviderResult, Normalized successful chat-completion result returned by every provider., Run one chat completion and return a :class:`ProviderResult` on success.…, _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), asyncio (+11 more)

### Community 65 - "RedactionReport"
Cohesion: 0.07
Nodes (62): httpx, _collect_alert_repetition_rows(), collect_db(), _collector_error(), _jsonable(), Any, Exception, _successful_alert_repetition_buckets() (+54 more)

### Community 66 - "button_router"
Cohesion: 0.08
Nodes (40): button_router(), DEFAULT_TYPE, Update, build_admin_back_keyboard(), build_admin_keyboard(), build_admin_logs_keyboard(), build_admin_premium_keyboard(), build_first_run_brief_keyboard() (+32 more)

### Community 67 - "test_event_alert_pr2_cooldown.py"
Cohesion: 0.33
Nodes (9): bot, _db(), asyncio, parametrize, PR 2 regressions for confirmed semantic cooldown boundary defects. No provider,…, Two distinct event rows can pass prefilter before the first send finishes., test_incomplete_persisted_identity_uses_own_verified_market_move(), test_late_delivery_remains_in_semantic_cooldown_query() (+1 more)

### Community 68 - "canonicalize_event_key"
Cohesion: 0.13
Nodes (20): CanonicalEventKey, canonicalize_event_key(), _collapse_event_key(), _fallback_event_key(), _is_random_event_key(), _normalize_event_key_text(), Return a stable backend key for semantic event identity., _semantic_event_key() (+12 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "validate_event_significance_output"
Cohesion: 0.16
Nodes (17): empirical_absolute_move_percentile(), Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., validate_event_significance_output(), _significance_schema_check(), schema_check(), validate(), _payload() (+9 more)

### Community 71 - "CCWBot"
Cohesion: 0.10
Nodes (20): Admin System Status, CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables (+12 more)

### Community 72 - "BundleWriter"
Cohesion: 0.12
Nodes (15): BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk., sha256_file() (+7 more)

### Community 73 - "datetime"
Cohesion: 0.11
Nodes (7): datetime, Audit only aggregated benchmark budget and next-call feasibility (no inference)., CCW-29 direct model adjudication. Nonblinded exploratory, NOT a human reference., CCW-45 offline matched scorer. Does not generate, rerun or request any model…, Stage only sanitized case inputs, checkpoint ledgers and approved API…, shutil, tempfile

### Community 74 - "0024_gram_symbol.py"
Cohesion: 0.33
Nodes (13): _coerce_related_symbols(), _column_names(), downgrade(), _has_table_and_symbol(), _has_table_columns(), _merge_price_state(), _merge_user_coin_subscriptions(), _merge_user_symbol_alert_state() (+5 more)

### Community 75 - "test_event_alert_composition_investigation.py"
Cohesion: 0.19
Nodes (27): market_direction_claims_supported(), Check explicit period directions and the direction implied by relationships., Reject fabricated context, independent of editorial preferences. Valid text…, _validate_event_alert_render_causality(), market(), parametrize, Synthetic regressions for the October alert-composition investigation., test_alignment_fallback_names_direction_and_verified_size_relationship() (+19 more)

### Community 76 - "test_agent_workflow_contract.py"
Cohesion: 0.19
Nodes (10): _adapter_path(), _agent_names(), _agent_paths(), _load_toml(), Path, test_agent_definitions_have_matching_claude_adapters(), test_agent_definitions_have_required_schema(), test_agent_routing_references_existing_agents() (+2 more)

### Community 77 - "test_event_alert_delivery_quality_regressions.py"
Cohesion: 0.15
Nodes (23): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, _event_alert_render_prompt_payload(), Return only a supported sign; no rounded or raw market numbers reach Render., _render_market_direction(), test_generic_snapshot_diagnostic_matches_real_message_newlines(), test_specific_next_observation_is_not_generic(), _decision() (+15 more)

### Community 78 - "test_heartbeat_postgres.py"
Cohesion: 0.20
Nodes (13): automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, importlib, postgres_url(), asyncio, Real PostgreSQL locking checks; the SQLite process mutex cannot prove these… (+5 more)

### Community 79 - "news_service.py"
Cohesion: 0.14
Nodes (24): fetch_crypto_news(), headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Merge available feeds by publication age *before* applying the batch limit. A…, Low-cost, word-boundary-aware prefilter; not an alert decision. (+16 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.27
Nodes (35): LlmOperationOutcome, NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap(), test_invalid_primary_and_openai_backoff_stay_failed_not_cached_success(), build_session() (+27 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "time"
Cohesion: 0.07
Nodes (44): concurrent_futures, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., atom(), call_one(), check_reply() (+36 more)

### Community 83 - "event_analysis.py"
Cohesion: 0.11
Nodes (42): _claim_clause(), _claimed_percent(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal(), _decimal_market_value(), _direction_for_claim(), directional_market_family() (+34 more)

### Community 84 - "get_or_create_user"
Cohesion: 0.44
Nodes (12): get_or_create_user(), Create or update profile fields for the current Telegram interaction., build_session(), asyncio, test_get_or_create_user_allows_missing_username(), test_get_or_create_user_demotes_existing_admin_removed_from_allowlist(), test_get_or_create_user_keeps_non_admin_role_with_allowlist(), test_get_or_create_user_marks_second_admin_id_from_allowlist() (+4 more)

### Community 85 - "CCW-20 paired final messages"
Cohesion: 0.09
Nodes (21): 10. ev_3c7f3da2e73e4b90 — ETH, 11. ev_7804adc277bd3333 — GRAM, 12. ev_345fc49db8255adf — GRAM, 13. ev_7b3325d2f2609480 — GRAM, 14. ev_1b39a518ede3c14f — GRAM, 15. ev_6500c5ad9f5364bc — GRAM, 16. ev_4bba21dd01bc8372 — SOL, 17. ev_1ea4cea05b78ed5c — SOL (+13 more)

### Community 86 - "event_chart.py"
Cohesion: 0.11
Nodes (28): bot_alerting, ChartResult, _connectable_now_segment(), _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw (+20 more)

### Community 87 - "test_event_alert_owner_copy_news_regressions.py"
Cohesion: 0.21
Nodes (16): _action_without_negated_technical_levels(), compact_event_alert_possible_action(), _has_unsupported_action_market_claim(), Keep Event Alert actions short, conditional, and non-prescriptive., test_ccw20_action_rejects_unsupported_future_divergence_or_convergence(), _decision(), _market(), Owner-approved Event Alert final-copy regressions (no provider/network calls). (+8 more)

### Community 88 - "asyncio"
Cohesion: 0.08
Nodes (22): AsyncFalse, AsyncNoop, AsyncTrue, build_session(), CallbackQuery, create_user(), FakeMessage, FakeQuery (+14 more)

### Community 89 - "FakeResponse"
Cohesion: 0.19
Nodes (6): FakeClient, FakeResponse, test_get_coin_price_429_triggers_retry(), __init__(), test_get_with_retry_can_disable_stale_cache_after_429_retries(), test_get_with_retry_returns_stale_cache_after_429_retries()

### Community 90 - "Context Audit Report"
Cohesion: 0.07
Nodes (18): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+10 more)

### Community 91 - "_fixture"
Cohesion: 0.10
Nodes (30): _canonical_event_analysis_context(), _event_analysis_news_summary(), Return compact useful news text, dropping RSS markup/noise before the LLM., Semantic model and grounding context used for exact pre-LLM reuse., _event_analysis_prompt_payload(), Return the compact semantic model view without runtime or repeated static…, Clear all breaker state (tests and controlled restarts)., reset_breakers() (+22 more)

### Community 92 - "test_watchlist_ux.py"
Cohesion: 0.11
Nodes (51): is_symbol_free(), build_premium_paywall_keyboard(), build_trial_offer_keyboard(), is_admin_update(), Update, build_plan_message(), build_subscribe_message(), build_user_settings_message() (+43 more)

### Community 93 - "utc_now"
Cohesion: 0.18
Nodes (22): datetime, Return timezone-aware UTC timestamp., utc_now(), _log_scheduled_refresh_skip(), Return timezone-aware (generated_at, expires_at) for a DB or in-memory report., True when the cached report survives past the scheduled-refresh grace window., Scheduled cache refresh: regenerate unless the cache stays fresh past the grace…, refresh_report_cache_scheduled() (+14 more)

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.17
Nodes (11): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Log pattern counting, News-candidate signal (+3 more)

### Community 96 - "test_event_alert_render_grounded_copy.py"
Cohesion: 0.33
Nodes (11): decision_for(), final_action(), market_down(), Evidence-backed Stage-2 Render guards and final-copy regression tests. All…, test_conditionals_do_not_hide_false_observed_direction(), test_render_does_not_invent_a_path_from_missing_or_gapped_snapshots(), test_render_evidence_exposes_grounded_recent_path_not_only_direction(), test_same_conditional_copy_is_not_forced_on_distinct_paths() (+3 more)

### Community 97 - "automatic_price_check"
Cohesion: 0.06
Nodes (56): _analysed_window_minutes_from_payload(), _build_event_analysis_id(), _build_news_driven_event_key(), _raw_event_key_from_payload(), _semantic_family_from_payload(), _news_driven_identity(), AlertRecipient, AlertRecipientResolution (+48 more)

### Community 98 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.14
Nodes (19): prepare_chart_points(), Never extrapolate over missing time or label a partial day as 24h., Event-specific references are opt-in; Heartbeat is exactly the old chart., render_price_chart(), build_coin_icon_html(), _observations(), Event Alert UX, chart evidence and single-send fallback contracts., test_chart_accepts_normal_30_minute_scheduler_jitter_but_rejects_stale() (+11 more)

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

### Community 105 - "user.py"
Cohesion: 0.42
Nodes (8): DEFAULT_TYPE, Update, General user command handlers., Best-effort product measurement that never exposes deep-link data to users., _record_start_analytics(), start(), _start_payload(), user_id()

### Community 106 - "RichDeliveryUncertain"
Cohesion: 0.15
Nodes (16): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert() (+8 more)

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.33
Nodes (17): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+9 more)

### Community 108 - "test_price_service.py"
Cohesion: 0.13
Nodes (23): _extract_ton_coin_data_from_simple_price(), get_coin_market_data_batch(), Fetch market data for supported symbols with one CoinGecko request. Missing…, Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., clean_price_caches(), clear_price_caches(), isolate_http_client_construction(), NoopAsyncClient (+15 more)

### Community 109 - "Event Alert logic"
Cohesion: 0.10
Nodes (21): Eight mandatory acceptance gates, Event Alert 24h metric and title (2026-10-29), Event Alert acceptance criteria (approved 2026-10-16), Event Alert chart reference markers (2026-10-26), Event Alert logic, Execution and release gates, Independent evidence and evaluation, Related news pipeline (+13 more)

### Community 110 - "Documentation"
Cohesion: 0.33
Nodes (5): Core, Development and operations, Documentation, Research, What is intentionally not here

### Community 111 - "CCW-41 Reviewer C offline audit"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C offline audit, Compare only after sealing, Prepare frozen blind packets, Review and import

### Community 112 - "ccwbot-ops-agent-mark-report-success"
Cohesion: 0.70
Nodes (4): ccwbot-ops-agent-mark-report-success script, reject(), safe_relative_path(), usage()

### Community 113 - "_build_event_analysis_input"
Cohesion: 0.10
Nodes (38): calculate_price_change_percent(), Calculate a percent change without mixing binary floats and ``Decimal`` values., _calculate_price_change(), get_analysed_window_minutes(), _build_event_analysis_input(), _build_market_heartbeat_input(), _compact_event_snapshot(), _compact_event_snapshots() (+30 more)

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
Cohesion: 0.12
Nodes (20): combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids(), Centralized configuration loaded from environment variables. Notes about key…, is_admin_user(), sync_user_from_update(), test_admin_user_ids_ignore_empty_whitespace_and_invalid_values(), test_multi_admin_user_ids_parse_comma_list() (+12 more)

### Community 129 - "decimal"
Cohesion: 0.24
Nodes (9): is_cooldown_active(), datetime, Decimal, Core alert-rule helpers used by automatic market checks., Return True while a previous alert is still inside the cooldown window., decimal, test_calculate_price_change_percent_accepts_mixed_decimal_and_float_operands(), test_calculate_price_change_percent_preserves_direction() (+1 more)

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
Cohesion: 0.17
Nodes (38): UserPremiumSubscription, UserPremiumTrial, activate_premium_from_telegram_stars_payment(), _activate_premium_from_telegram_stars_payment_locked(), ensure_default_coin_subscriptions(), expire_due_premium_trials(), get_payment_by_provider_id(), get_user_premium_subscription() (+30 more)

### Community 145 - "0028_premium_trials.py"
Cohesion: 0.36
Nodes (6): downgrade(), _has_table(), upgrade(), downgrade(), _replace_event_name_check(), upgrade()

### Community 147 - "LLMJsonResult"
Cohesion: 0.29
Nodes (4): LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., CorrelatedFallbackNewsLlm, tuple

### Community 148 - "Development"
Cohesion: 0.15
Nodes (8): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.06
Nodes (67): MarketHeartbeatDecision, MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body(), sanitize_heartbeat_possible_action() (+59 more)

### Community 150 - "os"
Cohesion: 0.07
Nodes (21): argparse, asyncpg, bot_services, ctypes, dotenv, importlib_util, openai, os (+13 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.02
Nodes (147): _get_int_env(), api_key(), api_key_env(), base_url(), effective_max_tokens_for(), event_analysis_operation_budget_seconds(), _format_chain(), global_provider_priority() (+139 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "save_llm_usage_log"
Cohesion: 0.33
Nodes (6): AsyncSession, LLM usage telemetry persistence. Belongs here: saving and updating…, Update a usage row when downstream JSON schema validation fails., Save one LLM usage telemetry row., save_llm_usage_log(), update_llm_usage_log_status()

### Community 156 - "test_multicoin_alerts.py"
Cohesion: 0.10
Nodes (30): _classify_news_context(), Return active market symbols independently of current recipient eligibility., resolve_symbols_to_check(), set_user_coin_subscription(), build_session_factory(), create_user(), asyncio, test_automatic_fallback_state_persists_decimal_prices() (+22 more)

### Community 157 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 158 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 159 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 160 - "schemas.py"
Cohesion: 0.11
Nodes (8): dataclasses, DbQuery, Assert every collector SQL statement is a read-only, single, unterminated…, validate_read_only_queries(), isoformat_utc(), datetime, test_all_db_queries_are_read_only_and_parameterized(), test_db_collector_failure_is_isolated_and_later_collectors_continue()

### Community 162 - "price.py"
Cohesion: 0.43
Nodes (6): log_custom_emoji_ids(), price(), DEFAULT_TYPE, Update, Manual price lookup and text-message utility handlers., build_supported_symbols_message()

### Community 164 - "db/reports.py"
Cohesion: 0.32
Nodes (7): get_latest_market_report(), AsyncSession, datetime, Market report cache persistence. Belongs here: daily/weekly market report cache…, Save one cached market report generation attempt., Return the newest cached market report for a cadence., save_market_report()

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.15
Nodes (20): ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment(), _migration_config() (+12 more)

### Community 169 - "asyncio"
Cohesion: 0.06
Nodes (14): asyncio, parametrize, test_event_chart_file_id_reused_across_recipients_in_one_dispatch(), test_heartbeat_falls_back_to_styled_html_if_rich_adapter_has_no_token(), test_integrity_conflict_preserves_terminal_delivery_reservation(), test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post(), test_rich_ambiguous_error_never_falls_back_or_retries() (+6 more)

### Community 170 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 171 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 173 - "bot/reports.py"
Cohesion: 0.07
Nodes (46): _build_daily_report_message(), _build_deterministic_report_decision(), _build_market_report_input(), _build_weekly_breadth(), _build_weekly_coin_context(), _build_weekly_context(), _build_weekly_report_message(), _build_weekly_timeline() (+38 more)

### Community 174 - "_runner_private.py"
Cohesion: 0.28
Nodes (15): call_once(), classify(), fail(), main(), persist(), datetime, quota_allows(), Finite direct-provider CCW-16 canary runner; Python stdlib only. This script… (+7 more)

### Community 175 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 176 - "build_llm_messages"
Cohesion: 0.33
Nodes (6): build_llm_messages(), graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), base(), prepare(), add()

### Community 177 - "runtime/state.py"
Cohesion: 0.15
Nodes (12): Runtime state and startup helpers., close_database(), initialize_database(), Any, Dispose database resources created during startup., SessionFactoryRef, _sync_package_database_engine(), asyncio (+4 more)

### Community 178 - "test_price_handlers.py"
Cohesion: 0.29
Nodes (15): CoinGeckoRateLimitError, Exception, Raised when CoinGecko returns HTTP 429., clear_manual_price_rate_limits(), _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users() (+7 more)

### Community 180 - "/graphify"
Cohesion: 0.09
Nodes (18): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+10 more)

### Community 181 - "_event_significance_prompt_payload"
Cohesion: 0.10
Nodes (24): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Ground-truth evidence and limitations, Read-only local check, Versioned artifacts, _event_significance_prompt_payload(), Return the small always-on model view used only for significance., Stage verified model-visible pilot calls into isolated CCW-16 workspace. No… (+16 more)

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.33
Nodes (5): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps

### Community 183 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 184 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 185 - "test_report_llm_exhaustion_recovery.py"
Cohesion: 0.43
Nodes (6): asyncio, parametrize, Report availability must survive exhausted LLM providers, but not unrelated…, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload()

### Community 186 - "test_news_driven_alerts.py"
Cohesion: 0.47
Nodes (5): _load_news_driven_alert_candidates(), asyncio, Regression coverage for the disabled standalone-news Event Alert path., test_news_driven_alerts_warning_logs_once_not_per_cycle(), test_news_driven_flag_cannot_bypass_product_policy()

### Community 187 - "check_owner_html.py"
Cohesion: 0.22
Nodes (4): html_parser, HTMLParser, P, Quick syntax and blind-payload integrity check for standalone owner form.

### Community 188 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 189 - "news_context.py"
Cohesion: 0.08
Nodes (42): _alert_news_rank(), _candidate_news_relevance_label(), classify_news_relevance(), filter_news_for_symbol(), _format_candidate_news(), _has_gram_crypto_context(), _is_clearly_market_wide_news(), is_generic_news_item() (+34 more)

### Community 190 - "Repository Source of Truth"
Cohesion: 0.33
Nodes (5): Canonical ownership, Conflict resolution, No standing rules outside the repository, Repository bootstrap, Repository Source of Truth

### Community 192 - "unittest_mock"
Cohesion: 0.17
Nodes (15): MarketReportDecision, format_html_market_report(), format_rich_market_report(), Rich headings and sections, using exactly the persisted plain report content., Valid ordinary Telegram HTML when native Rich is definitively rejected., _decision(), asyncio, parametrize (+7 more)

### Community 193 - "test_news_ingestion.py"
Cohesion: 0.19
Nodes (10): feedparser, _entry(), _feed(), asyncio, datetime, Regression tests for the independent, bounded RSS ingestion path., test_rss_merges_sources_by_publication_time_before_limit(), test_rss_source_failure_is_isolated_and_safely_counted() (+2 more)

### Community 194 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 195 - "0003_premium_watchlist_foundation.py"
Cohesion: 0.80
Nodes (4): _column_names(), downgrade(), _table_names(), upgrade()

### Community 196 - "0026_growth_analytics.py"
Cohesion: 0.90
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

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

### Community 210 - "handlers/reports.py"
Cohesion: 0.16
Nodes (15): daily_report(), DEFAULT_TYPE, Update, Market report command handlers., weekly_report(), Manual rich sends bypass PTB's normal send_message override., Track acknowledged rich output for Close and next-command cleanup., register_rich_reply() (+7 more)

### Community 223 - "build_review.py"
Cohesion: 0.32
Nodes (11): candidate(), canon(), context(), csvwrite(), main(), Private read-only CCWBot market benchmark and independent review CSV exporter., run_psql(), safe() (+3 more)

### Community 226 - "db/settings.py"
Cohesion: 0.42
Nodes (9): AppSettings, UserSettings, _get_app_settings_row(), get_or_create_app_settings(), get_or_create_user_settings(), AsyncSession, Global and legacy per-user settings persistence. Belongs here: app-wide alert…, update_app_settings() (+1 more)

### Community 233 - "enrich_quality_first_history.py"
Cohesion: 0.11
Nodes (20): csv, fmt(), CCW-44: optional quality-first enhancement with actual read-only historical…, reduce_history(), hashfile(), main(), metrics(), Versioned private calibration reference from owner's 66 A/C re-decisions.… (+12 more)

### Community 234 - "database.py"
Cohesion: 0.06
Nodes (48): alembic_config, do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), alembic_script, Base (+40 more)

### Community 238 - "CCW-20 — Offline safety correction of retained Cloudflare final texts"
Cohesion: 0.33
Nodes (5): CCW-20 — Offline safety correction of retained Cloudflare final texts, Concrete verified example — ETH (`ev_0ab71234c9080ecc`), Finding / fix, Reproducible offline check, What this test does not prove

## Knowledge Gaps
- **440 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+435 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1715 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `Observability Snippets` to `Ops-Agent Service`, `asyncio`, `RichDeliveryUncertain`, `CCWBot Ops-Agent Report Analysis`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `test_event_alert_rich_chart_ux.py`, `schedule_automatic_market_check`, `test_rich_market_report_delivery.py`, `asyncio`, `Observability Snippets`, `bot/alerts.py`, `bot/reports.py`, `handlers/reports.py`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `SimulatedDeployTests` connect `SimulatedDeployTests` to `time`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 170 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 170 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _440 weakly-connected nodes found - possible documentation gaps or missing edges._