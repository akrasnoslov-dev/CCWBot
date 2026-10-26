# Graph Report - CCWBot  (2026-10-26)

## Corpus Check
- 639 files · ~1,134,461 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 33 file(s) not represented in the graph (top: .toml 12, (none) 8, .csv 6)

## Summary
- 5575 nodes · 16577 edges · 229 communities (193 shown, 36 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1399 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bf4cf7cb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- replay_event_significance.py
- LlmUsageLog
- onboarding.py
- Period
- test_llm_breaker.py
- ai_agent_groq.py
- test_rich_market_report_delivery.py
- test_telegram_stars_payments.py
- common.py
- test_system_status.py
- sqlalchemy
- test_openai_budget.py
- bot/alerts.py
- test_groq_budget.py
- test_seen_news_dedup.py
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- event_alert_benchmark.py
- bootstrap.py
- admin.py
- runtime/state.py
- test_heartbeat_silence.py
- test_bundle_and_cli.py
- event_text.py
- properties
- utc_now
- _StructuredRecordBuffer
- validate_market_report_output
- properties
- canonicalize_event_key
- ccw41_reviewer_c_audit.py
- detectors.py
- handlers/__init__.py
- Observability Snippets
- test_report_cooldowns.py
- test_gemini_quota_backoff.py
- error_file_logging.py
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- _event_significance_prompt_payload
- test_multicoin_alerts.py
- select
- bot/news.py
- test_ai_agent_groq.py
- log
- db/news.py
- refresh_report_cache_scheduled
- test_llm_rate_limit_backoff.py
- display_symbol
- test_event_alert_render_provider_chain.py
- AISchemaValidationError
- test_event_alert_delivery_quality_regressions.py
- test_llm_outage_detectors.py
- manifest.json
- CCWBot Growth Strategy: 0 -> 1 Premium
- system_status.py
- test_price_service.py
- test_product_analytics.py
- cli.py
- json
- test_event_analysis_health.py
- keyboards.py
- RedactionReport
- button_router
- User
- AIProviderRateLimitError
- 0001_initial_schema.py
- validate_event_significance_output
- CCWBot
- decimal
- event_analysis.py
- 0024_gram_symbol.py
- hashlib
- test_agent_workflow_contract.py
- collections_abc
- EventAnalysisDecision
- test_event_alert_postrelease_regressions.py
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- time
- _fixture
- LlmOperationOutcome
- test_news_intelligence_schema.py
- event_chart.py
- audit
- .__init__
- datetime
- Context Audit Report
- analytics.py
- test_watchlist_ux.py
- Development
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- watchlist.py
- price_service.py
- test_event_alert_rich_chart_ux.py
- Ops-Agent Service
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- unittest_mock
- NotificationType
- test_event_alert_chart_markers.py
- make_news_key
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
- FakeResponse
- bot/config.py
- architecture-guardian.md
- code-quality.md
- db-migration-guardian.md
- devops-release.md
- market-pipeline.md
- bot/health.py
- product-policy.md
- security-review.md
- telegram-stars-payments.md
- Base
- AGENTS.md
- agents/README.md
- codex_task_prompt_template.md
- Project Context
- db/premium.py
- _runner_private.py
- _build_exact_event_context_fingerprint
- os
- test_event_alert_composition_investigation.py
- test_market_heartbeat.py
- _send_alert_to_recipient_once
- test_llm_config_budgets.py
- ChatGPT / Bridge / Codex Workflow
- telegram_error
- collectors/__init__.py
- ops_agent/__init__.py
- test_alert_recipients.py
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- db.py
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: extra exports and benchmark
- pkgutil
- news_intelligence_service.py
- reviewer-c-rubric.md
- What You Must Do When Invoked
- extraction-spec.md
- test_alembic_migrations.py
- test_news_driven_alerts.py
- CCW-41 exploratory Reviewer-C agreement/disagreement
- test_heartbeat_does_not_query_previous_event
- bot/reports.py
- RichDeliveryUncertain
- TransientSessions
- handlers/reports.py
- test_ccw9_ccw10.py
- test_price_handlers.py
- /graphify
- test_rich_403_preserves_safe_blocked_classification_without_raw_errors
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- 0008_database_comments.py
- CCW-43 — Evidence-based Event Analysis prompt redesign
- test_transport_reuses_file_id_and_handles_valid_response
- 0027_market_heartbeat_defaults.py
- P
- database.py
- news_context.py
- 0025_llm_operation_correlation.py
- .__init__
- FakeAsyncClient
- get_or_create_user
- CCWBot Operational Report — Unverified (No Production Bundle)
- _build_event_analysis_input
- CCW-25 — Self-hosted LLM owner decision
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- CCWBot — blind owner disagreement-only replay
- calculate_price_change_percent
- Repository-backed Graphify
- CCW-25 research evidence
- 0031_onboarding_customize_event.py
- operator_prompt.md
- normalize_symbol
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- 0009_error_file_logging_toggle.py
- 0026_growth_analytics.py
- README_RU.md
- test_heartbeat_postgres.py
- fresh200_luna_wait_start.sh
- openai_luna_wait_start.sh
- .__init__
- build_owner_reference_candidate_v1.py
- build_llm_messages
- test_growth_analytics_migration.py
- save_market_report
- Provider fallback (redundancy)
- test_exhausted_provider_chain_uses_verified_data_fallback
- users.py
- NoopAsyncClient

## God Nodes (most connected - your core abstractions)
1. `select()` - 171 edges
2. `Period` - 114 edges
3. `LLMRouter` - 96 edges
4. `Base` - 91 edges
5. `normalize_symbol()` - 88 edges
6. `User` - 68 edges
7. `utc_now()` - 64 edges
8. `run_detectors()` - 64 edges
9. `EventAnalysisDecision` - 56 edges
10. `automatic_price_check()` - 56 edges

## Surprising Connections (you probably didn't know these)
- `Event Alert chart reference markers (2026-10-26)` --references--> `price()`  [INFERRED]
  docs/alert_logic.md → bot/handlers/price.py
- `Startup configuration log` --references--> `AIProviderRateLimitError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Which 4xx responses fall back` --references--> `AIInvalidJsonError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Read-only local check` --references--> `load_frozen()`  [INFERRED]
  benchmarks/ccw15-v1/README.md → scripts/event_alert_benchmark.py
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (229 total, 36 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.14
Nodes (47): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), alert_analysis_result(), event_analysis_result(), factual_market_input() (+39 more)

### Community 1 - "replay_event_significance.py"
Cohesion: 0.09
Nodes (33): _groq_json_mode_enabled(), scripts, blind_packet(), classify_replay_error(), effort_budget(), groq_significance_response_format(), live_report(), load_cases() (+25 more)

### Community 2 - "LlmUsageLog"
Cohesion: 0.11
Nodes (34): LlmUsageLog, Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider… (+26 more)

### Community 3 - "onboarding.py"
Cohesion: 0.10
Nodes (53): ProductEvent, UserCoinSubscription, build_onboarding_customize_keyboard(), Premium-only onboarding selector. BTC stays as the free default during…, _as_aware_utc(), build_instant_brief(), build_onboarding_message(), build_returning_user_message() (+45 more)

### Community 4 - "Period"
Cohesion: 0.05
Nodes (62): alembic_migration, alembic_operations, ops_agent_collectors, run_detectors(), Period, sqlite3, _AlertEvidenceFakeEngine, _assert_malformed_numeric_context_is_safe() (+54 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.08
Nodes (77): _backoff_schedule(), breaker_snapshot(), _BreakerState, is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics., True when this triple is open and must be skipped in favour of the next… (+69 more)

### Community 6 - "ai_agent_groq.py"
Cohesion: 0.04
Nodes (117): asyncio, ask_event_alert_render_raw(), ask_market_heartbeat_raw(), ask_market_report_raw(), ask_news_intelligence_raw(), build_event_alert_render_prompt(), build_market_heartbeat_prompt(), build_market_report_prompt() (+109 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.09
Nodes (45): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report(), market_report_change_chart() (+37 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.09
Nodes (57): Payment, premium_symbols_display(), Supported coin metadata shared by price checks and Premium watchlists., build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date() (+49 more)

### Community 9 - "common.py"
Cohesion: 0.08
Nodes (36): _callback_command_update(), decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, Edit a transient callback screen without exposing Telegram failures. (+28 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.18
Nodes (47): PriceState, build_admin_llm_diagnostics_text(), build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health., build_session_factory(), _event_analysis(), _final_failed_alert() (+39 more)

### Community 11 - "sqlalchemy"
Cohesion: 0.04
Nodes (22): alembic, downgrade(), _unique_constraint_names(), upgrade(), downgrade(), _table_names(), upgrade(), _column_names() (+14 more)

### Community 12 - "test_openai_budget.py"
Cohesion: 0.09
Nodes (46): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., Return the fully resolved per-call-type LLM configuration. Model identifiers,…, resolved_configuration(), _cost(), monthly_budget_usd(), OpenAIBudget, OpenAIBudgetExhausted (+38 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.04
Nodes (83): bot_alerting, alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.… (+75 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.16
Nodes (20): _Charge, GroqBudget, GroqBudgetExhausted, datetime, Test-only reset; production restarts reload persisted usage., asyncio, Regression checks for zero-cost Groq pacing, day quota, symbol fairness and…, Other Groq model budgets remain separate from Event Analysis reservations. (+12 more)

### Community 15 - "test_seen_news_dedup.py"
Cohesion: 0.14
Nodes (33): attach_analysis_to_market_event(), get_event_ai_analysis(), get_latest_success_event_ai_analysis(), get_or_create_market_event(), Decimal, Return the market event for event_instance_key, creating it when needed., Return an existing AI analysis for the event/input pair if present., Return any successful saved analysis for a market event. (+25 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (65): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+57 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.13
Nodes (41): ask_event_analysis_raw(), _configure(), ContentProvider, _empty_report_news_context(), _grounded_alert(), _grounding_market(), _grounding_schema_check(), _install_report_inputs() (+33 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (79): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+71 more)

### Community 19 - "event_alert_benchmark.py"
Cohesion: 0.11
Nodes (39): importlib_util, random, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, CCW-29 fresh private holdout: collect real POST-200 market cases via…, choose(), Freeze fresh 200 real CCWBot market cases, excluding both earlier sets;…, Resume CCW-29 Groq after server-supplied 429 Retry-After. Preserve previous…, canonical_json() (+31 more)

### Community 20 - "bootstrap.py"
Cohesion: 0.09
Nodes (33): AbstractEventLoop, AppRunner, bot_handlers, Application, register_bot_handlers(), start_health_server(), handle_health(), stop_health_server() (+25 more)

### Community 21 - "admin.py"
Cohesion: 0.14
Nodes (33): _build_admin_llm_diagnostics_text(), _build_admin_system_status_text(), _format_admin_alert_settings(), _parse_acquisition_link_arguments(), _premium_grant_usage_text(), _premium_revoke_usage_text(), Admin and operational Telegram command handlers. Belongs here: admin-only…, send_admin_callback_response() (+25 more)

### Community 22 - "runtime/state.py"
Cohesion: 0.15
Nodes (12): Runtime state and startup helpers., close_database(), initialize_database(), Any, Dispose database resources created during startup., SessionFactoryRef, _sync_package_database_engine(), asyncio (+4 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.16
Nodes (22): can_deliver_market_heartbeat_now(), pytest_asyncio, add_delivery(), asyncio, parametrize, test_delayed_success_uses_completion_not_reservation(), test_event_resets_timer_during_generation_market_fetch(), market() (+14 more)

### Community 24 - "test_bundle_and_cli.py"
Cohesion: 0.04
Nodes (55): ops_agent, BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk. (+47 more)

### Community 25 - "event_text.py"
Cohesion: 0.09
Nodes (43): compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback(), _has_persistent_snapshot_direction(), is_news_centered_event_action(), _is_safe_llm_situation() (+35 more)

### Community 26 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 27 - "utc_now"
Cohesion: 0.16
Nodes (16): Return timezone-aware UTC timestamp., utc_now(), _llm_diagnostics_menu(), InlineKeyboardMarkup, Return timezone-aware (generated_at, expires_at) for a DB or in-memory report., True when the cached report survives past the scheduled-refresh grace window., _report_cache_timestamps(), _scheduled_refresh_can_skip() (+8 more)

### Community 28 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "canonicalize_event_key"
Cohesion: 0.11
Nodes (27): canonicalize_event_key(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal(), _fallback_event_key(), _is_random_event_key(), _normalize_event_key_text() (+19 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.10
Nodes (60): _aggregate_markdown(), _cli(), compare_reviewers(), _field_exists(), _group_metrics(), import_results(), _label_counts(), _load_manifest() (+52 more)

### Community 33 - "detectors.py"
Cohesion: 0.13
Nodes (30): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+22 more)

### Community 34 - "handlers/__init__.py"
Cohesion: 0.14
Nodes (44): build_acquisition_telegram_url(), Build a Telegram deep link only from a valid configured bot username and opaque…, acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_error_logging_status_text(), chat_id() (+36 more)

### Community 35 - "Observability Snippets"
Cohesion: 0.08
Nodes (27): consecutive_failures(), Output, Rules you enforce, What you review, Admin System Status, Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis (+19 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.17
Nodes (34): MarketReport, reports(), get_or_generate_report(), _is_completed_report(), One shared refresh on old content; never fan out LLM/RSS per recipient., send_daily_report_message(), AsyncClock, build_session_factory() (+26 more)

### Community 37 - "test_gemini_quota_backoff.py"
Cohesion: 0.19
Nodes (17): GeminiProvider, get_provider(), Gemini provider (second fallback). Reached through Google's OpenAI-compatible…, Gemini 3.x deprecates explicit sampling parameters in generation config., _failed_provider(), asyncio, Gemini quota and structured retry guidance regression tests; no live API calls., _response_error() (+9 more)

### Community 38 - "error_file_logging.py"
Cohesion: 0.08
Nodes (47): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., bot_observability, _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports() (+39 more)

### Community 39 - "LLMRouter"
Cohesion: 0.15
Nodes (53): LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider, _http_error(), _parse_json_validate() (+45 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.07
Nodes (35): _event_alert_presentation_title(), _llm_no_alert_decision_reason(), Render the headline from the primary deterministic metric, not LLM prose., contextlib, _event_input(), asyncio, parametrize, _runtime_no_alert_payload() (+27 more)

### Community 42 - "_event_significance_prompt_payload"
Cohesion: 0.10
Nodes (24): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Ground-truth evidence and limitations, Read-only local check, Versioned artifacts, _event_significance_prompt_payload(), Return the small always-on model view used only for significance., Stage verified model-visible pilot calls into isolated CCW-16 workspace. No… (+16 more)

### Community 43 - "test_multicoin_alerts.py"
Cohesion: 0.12
Nodes (27): AlertRecipientResolution, get_alert_recipients(), Return active market symbols independently of current recipient eligibility., Resolve eligible recipients once for one market event., resolve_symbols_to_check(), set_user_coin_subscription(), build_session_factory(), create_user() (+19 more)

### Community 44 - "select"
Cohesion: 0.09
Nodes (58): _save_market_heartbeat_attempt(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery(), get_last_sent_alert(), get_last_sent_alert_at(), get_last_sent_event_alert_at_for_event_key(), get_latest_event_analysis_attempt() (+50 more)

### Community 45 - "bot/news.py"
Cohesion: 0.16
Nodes (29): _dedupe_report_news(), fetch_report_news_context(), within_window(), _has_report_news_identity(), _item_link(), _item_published_at(), _item_related_symbols(), _news_row_rank() (+21 more)

### Community 46 - "test_ai_agent_groq.py"
Cohesion: 0.09
Nodes (17): build_event_analysis_prompt(), _parse_json(), Parse a JSON-object response without relaxing schema validation., bot_services_llm, The ops-agent's copy of the shipped model defaults must not drift from the…, parametrize, _set_groq_client(), test_event_alert_render_schema_only_contains_model_generated_fields() (+9 more)

### Community 47 - "log"
Cohesion: 0.10
Nodes (30): _build_market_heartbeat_id(), cleanup_seen_news_job(), generate_market_heartbeats(), _is_fresh_heartbeat(), Application, DEFAULT_TYPE, Compatibility wrapper for older imports; schedules the market-wide check., schedule_automatic_btc_check() (+22 more)

### Community 48 - "db/news.py"
Cohesion: 0.13
Nodes (27): SeenNews, cleanup_seen_news(), count_recent_news_intelligence_llm_calls(), get_cached_news_item_analysis(), get_cooling_failed_news_keys(), get_news_item_by_key(), get_recent_seen_news(), get_retryable_failed_news_items() (+19 more)

### Community 49 - "refresh_report_cache_scheduled"
Cohesion: 0.19
Nodes (19): Market report use-case entrypoints., generate_daily_report_cache_job(), generate_weekly_report_cache_job(), _is_report_provider_backoff_active(), Scheduled cache refresh: regenerate unless the cache stays fresh past the grace…, One recovery attempt after a scheduled failure; no recurring retry storm., refresh_report_cache_scheduled(), _schedule_failed_report_retry() (+11 more)

### Community 50 - "test_llm_rate_limit_backoff.py"
Cohesion: 0.06
Nodes (48): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions… (+40 more)

### Community 51 - "display_symbol"
Cohesion: 0.11
Nodes (26): Escape all model/news wording; only safely link explicit HTTP(S) sources., _report_coin_icon_html(), _safe_rich_line(), _build_event_alert_rich_html(), _build_market_heartbeat_rich_html(), _coin_fallback_emoji(), Presentation only; heartbeat timing and eligibility stay unchanged., Compact, legible rich-message metrics. Keep labels and values contiguous. (+18 more)

### Community 52 - "test_event_alert_render_provider_chain.py"
Cohesion: 0.26
Nodes (19): call_render(), FakeProvider, good_render(), input_payload(), install(), patch_significance_and_storage(), ProviderError, asyncio (+11 more)

### Community 53 - "AISchemaValidationError"
Cohesion: 0.10
Nodes (31): _create_market_heartbeat(), _schema_check(), ask_event_significance_raw(), Return JSON mode and provider-specific schemas for verified model attempts., _structured_response_formats(), AISchemaValidationError, RuntimeError, Raised when validated JSON does not match the expected schema. ``raw_content``… (+23 more)

### Community 54 - "test_event_alert_delivery_quality_regressions.py"
Cohesion: 0.17
Nodes (21): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, _event_alert_render_prompt_payload(), Return only a supported sign; no rounded or raw market numbers reach Render., _render_market_direction(), test_specific_next_observation_is_not_generic(), _decision(), _market() (+13 more)

### Community 55 - "test_llm_outage_detectors.py"
Cohesion: 0.19
Nodes (23): _detector(), _evidence(), parametrize, Detectors and evidence quality for an LLM-side Event Analysis outage. Covers…, Mimic the collector: newest bucket first, each bucket capped by remaining…, _row(), _simulate_row_cap(), test_a_failure_storm_no_longer_starves_delivered_analyses_of_the_row_cap() (+15 more)

### Community 56 - "manifest.json"
Cohesion: 0.06
Nodes (35): batch_size, batches, path, sha256, case_count, cases, dataset_sha256, operator_prompt_sha256 (+27 more)

### Community 57 - "CCWBot Growth Strategy: 0 -> 1 Premium"
Cohesion: 0.15
Nodes (12): Acquisition limitation, CCWBot Growth Strategy: 0 -> 1 Premium, Change, Current comparable cohort, Decision rule, Experiment 1 - Premium-only onboarding selector, Handoff prompt for a new chat, Primary metric (+4 more)

### Community 58 - "system_status.py"
Cohesion: 0.15
Nodes (33): _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, _delivery_failure_category(), _delivery_health(), _format_price() (+25 more)

### Community 59 - "test_price_service.py"
Cohesion: 0.15
Nodes (22): _extract_ton_coin_data_from_simple_price(), get_coin_market_data_batch(), Fetch market data for supported symbols with one CoinGecko request. Missing…, Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., clean_price_caches(), clear_price_caches(), isolate_http_client_construction(), asyncio (+14 more)

### Community 60 - "test_product_analytics.py"
Cohesion: 0.13
Nodes (29): AcquisitionAttribution, capture_first_touch_attribution(), AsyncSession, datetime, Resolve an active opaque deep-link token into configured attribution., Persist first-touch attribution without replacing a prior acquisition., Record one typed event; a duplicate lifecycle key returns the original., Atomically save eligible first-touch attribution and a bot start event. (+21 more)

### Community 61 - "cli.py"
Cohesion: 0.09
Nodes (54): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+46 more)

### Community 62 - "json"
Cohesion: 0.04
Nodes (36): collections, json, math, pathlib, re, main(), Verify completed research, reconcile metrics and fill the decision reports., sha() (+28 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.10
Nodes (27): _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, evaluate_state(), failure_escalation_threshold(), max_success_age_seconds(), datetime, In-process health signal for Event Analysis. Event Alerts were fully dead for…, Return ``(state, last_success_age_seconds)`` for the Event Analysis health… (+19 more)

### Community 64 - "keyboards.py"
Cohesion: 0.15
Nodes (25): log_custom_emoji_ids(), price(), DEFAULT_TYPE, Update, Manual price lookup and text-message utility handlers., build_admin_back_keyboard(), build_admin_keyboard(), build_admin_logs_keyboard() (+17 more)

### Community 65 - "RedactionReport"
Cohesion: 0.07
Nodes (58): dataclasses, httpx, collect_health(), Any, collect_local_state(), Any, collect_logs(), _empty_counts() (+50 more)

### Community 66 - "button_router"
Cohesion: 0.14
Nodes (19): button_router(), DEFAULT_TYPE, Update, build_interval_keyboard(), AsyncFalse, AsyncTrue, _callback_update(), _callback_values() (+11 more)

### Community 67 - "User"
Cohesion: 0.21
Nodes (16): User, build_session_factory(), create_market_event(), create_user(), asyncio, test_backfill_marks_historical_blocked_users_and_is_idempotent(), test_bad_request_delivery_failure_is_not_retried(), test_blocked_telegram_error_disables_user_and_keeps_failed_alert() (+8 more)

### Community 68 - "AIProviderRateLimitError"
Cohesion: 0.10
Nodes (31): ABC, BaseProvider, ProviderResult, Normalized successful chat-completion result returned by every provider., Common interface for all LLM providers., True when this provider has all configuration required for an attempt., Run one chat completion and return a :class:`ProviderResult` on success.…, provider_priority() (+23 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "validate_event_significance_output"
Cohesion: 0.17
Nodes (16): empirical_absolute_move_percentile(), Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., _required_choice(), validate_event_significance_output(), _significance_schema_check(), _payload(), parametrize (+8 more)

### Community 71 - "CCWBot"
Cohesion: 0.10
Nodes (20): Admin System Status, CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables (+12 more)

### Community 72 - "decimal"
Cohesion: 0.29
Nodes (7): is_cooldown_active(), datetime, Return True while a previous alert is still inside the cooldown window., decimal, test_calculate_price_change_percent_accepts_mixed_decimal_and_float_operands(), test_calculate_price_change_percent_preserves_direction(), test_cooldown_active_only_inside_window()

### Community 73 - "event_analysis.py"
Cohesion: 0.14
Nodes (35): CanonicalEventKey, _claim_clause(), _claimed_percent(), _decimal_market_value(), _direction_for_claim(), directional_market_family(), _duration_minutes(), _duration_minutes_from_claim() (+27 more)

### Community 74 - "0024_gram_symbol.py"
Cohesion: 0.33
Nodes (13): _coerce_related_symbols(), _column_names(), downgrade(), _has_table_and_symbol(), _has_table_columns(), _merge_price_state(), _merge_user_coin_subscriptions(), _merge_user_symbol_alert_state() (+5 more)

### Community 75 - "hashlib"
Cohesion: 0.04
Nodes (45): _json_dumps(), Canonical JSON that writes Decimal market values without binary-float loss., copy, hashlib, html_parser, io, Change only the CCW-16 experiment user cron cadence, preserving all other jobs., Read-only provider credential authentication probe on isolated Hetzner… (+37 more)

### Community 76 - "test_agent_workflow_contract.py"
Cohesion: 0.19
Nodes (10): _adapter_path(), _agent_names(), _agent_paths(), _load_toml(), Path, test_agent_definitions_have_matching_claude_adapters(), test_agent_definitions_have_required_schema(), test_agent_routing_references_existing_agents() (+2 more)

### Community 77 - "collections_abc"
Cohesion: 0.09
Nodes (8): _column_names(), downgrade(), _table_names(), upgrade(), downgrade(), _is_sqlite(), upgrade(), collections_abc

### Community 78 - "EventAnalysisDecision"
Cohesion: 0.17
Nodes (20): EventAnalysisDecision, Keep trading-oriented guidance conditional and proportionate., soften_possible_action(), _build_event_alert_html_message(), _build_event_alert_payload(), test_full_event_alert_keeps_shared_message_structure_and_disclaimer(), test_event_alert_presentation_is_market_first_with_nonmaterial_related_news(), test_event_alert_presentation_removes_repeated_llm_market_facts() (+12 more)

### Community 79 - "test_event_alert_postrelease_regressions.py"
Cohesion: 0.12
Nodes (24): bot, compact_event_alert_possible_action(), Keep Event Alert actions short, conditional, and non-prescriptive., build_event_significance_prompt(), _market(), parametrize, Historical alert defect contracts: never call an external provider or Telegram.…, test_contradictory_period_alignment_is_never_delivered_as_factual_claim() (+16 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.21
Nodes (39): NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap(), build_session(), CorrelatedFallbackNewsLlm, FakeNewsLlm (+31 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "time"
Cohesion: 0.05
Nodes (50): argparse, concurrent_futures, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., CCW-29 blind AI review worker: reuses existing provider transport; no prod…, atom() (+42 more)

### Community 83 - "_fixture"
Cohesion: 0.06
Nodes (39): _event_analysis_percent(), _event_analysis_prompt_payload(), Bound model-visible percent precision without erasing a non-zero sign., Return the compact semantic model view without runtime or repeated static…, Clear all breaker state (tests and controlled restarts)., reset_breakers(), _real_socket, socket (+31 more)

### Community 84 - "LlmOperationOutcome"
Cohesion: 0.14
Nodes (12): LlmOperationOutcome, AsyncSession, LLM usage telemetry persistence. Belongs here: saving and updating…, Update a usage row when downstream JSON schema validation fails., Persist one sanitized terminal outcome for a logical LLM operation., Save one LLM usage telemetry row., save_llm_operation_outcome(), save_llm_usage_log() (+4 more)

### Community 85 - "test_news_intelligence_schema.py"
Cohesion: 0.25
Nodes (17): _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), schema_check(), asyncio, parametrize, Offline News Intelligence symbol-contract regression tests; no provider calls. (+9 more)

### Community 86 - "event_chart.py"
Cohesion: 0.18
Nodes (15): ChartResult, _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw, Deterministic PNG chart from persisted, timestamped price observations only., Auditable reference value and its actual, not nominal, UTC timestamp. (+7 more)

### Community 87 - "audit"
Cohesion: 0.23
Nodes (13): audit(), positive_age_minutes(), ranking(), main(), _number(), Read-only assessment of sanitized Event Analysis decisions; NOT an LLM replay.…, _time(), Production timeline review tests: decision counts are not ground-truth FP/FN. (+5 more)

### Community 89 - "datetime"
Cohesion: 0.15
Nodes (14): datetime, Audit only aggregated benchmark budget and next-call feasibility (no inference)., CCW-45 offline matched scorer. Does not generate, rerun or request any model…, candidate(), canon(), context(), csvwrite(), main() (+6 more)

### Community 90 - "Context Audit Report"
Cohesion: 0.07
Nodes (18): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+10 more)

### Community 91 - "analytics.py"
Cohesion: 0.11
Nodes (28): create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), Durable, allowlisted product analytics persistence., List a bounded set of links which may currently attribute a start., Create one collision-safe, validated operator acquisition link., _validate_event(), AcquisitionLink (+20 more)

### Community 92 - "test_watchlist_ux.py"
Cohesion: 0.07
Nodes (41): build_watchlist_keyboard(), build_watchlist_render(), AsyncFalse, AsyncNoop, AsyncTrue, build_session(), CallbackQuery, create_user() (+33 more)

### Community 93 - "Development"
Cohesion: 0.25
Nodes (8): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.17
Nodes (11): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Log pattern counting, News-candidate signal (+3 more)

### Community 96 - "watchlist.py"
Cohesion: 0.12
Nodes (49): _as_aware_utc(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active(), is_user_trial_active() (+41 more)

### Community 97 - "price_service.py"
Cohesion: 0.13
Nodes (29): supported_symbols_display(), _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), _extract_sparkline_prices(), get_btc_market_data(), get_btc_price(), _get_cached_price() (+21 more)

### Community 98 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.19
Nodes (17): prepare_chart_points(), Never extrapolate over missing time or label a partial day as 24h., Event-specific references are opt-in; Heartbeat is exactly the old chart., render_price_chart(), _observations(), Event Alert UX, chart evidence and single-send fallback contracts., test_chart_accepts_normal_30_minute_scheduler_jitter_but_rejects_stale(), test_chart_downtime_selects_latest_gap_free_run_without_inventing_prices() (+9 more)

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
Cohesion: 0.29
Nodes (4): Event Alert benchmark and historical diagnostics (PR 1), Historical investigation: evidence status, Next-stage dependency and acceptance, Technical baseline, not product-quality scores

### Community 105 - "unittest_mock"
Cohesion: 0.33
Nodes (4): asyncio, SessionContext, test_trial_expiry_job_contains_lifecycle_failures(), unittest_mock

### Community 106 - "NotificationType"
Cohesion: 0.50
Nodes (4): NotificationType, Enum, str, Product-level notification type used for persisted alert-state bookkeeping.

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.33
Nodes (17): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+9 more)

### Community 108 - "make_news_key"
Cohesion: 0.07
Nodes (30): make_news_key(), Build a stable key for a news item. Links are preferred because RSS titles can…, fetch_news_context(), Fetch RSS news and use seen_news for dedupe when PostgreSQL is active., fetch_crypto_news(), headline_is_relevant(), _keyword_matches(), _published_at() (+22 more)

### Community 109 - "Event Alert logic"
Cohesion: 0.10
Nodes (20): Eight mandatory acceptance gates, Event Alert acceptance criteria (approved 2026-10-16), Event Alert chart reference markers (2026-10-26), Event Alert logic, Event Alert message quality contract, Execution and release gates, Independent evidence and evaluation, Render evidence and backend guard behavior (+12 more)

### Community 110 - "README.md"
Cohesion: 0.12
Nodes (10): Core, Development and operations, Documentation, Research, What is intentionally not here, Canonical ownership, Conflict resolution, No standing rules outside the repository (+2 more)

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

### Community 128 - "FakeResponse"
Cohesion: 0.19
Nodes (6): FakeClient, FakeResponse, test_get_coin_price_429_triggers_retry(), __init__(), test_get_with_retry_can_disable_stale_cache_after_429_retries(), test_get_with_retry_returns_stale_cache_after_429_retries()

### Community 129 - "bot/config.py"
Cohesion: 0.12
Nodes (20): combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids(), Centralized configuration loaded from environment variables. Notes about key…, is_admin_user(), sync_user_from_update(), test_admin_user_ids_ignore_empty_whitespace_and_invalid_values(), test_multi_admin_user_ids_parse_comma_list() (+12 more)

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

### Community 135 - "bot/health.py"
Cohesion: 0.10
Nodes (23): aiohttp, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any, datetime, Authoritative last successful Event Analysis time, or None when unavailable.…, Event Analysis health, as a nested block that never changes the top-level… (+15 more)

### Community 136 - "product-policy.md"
Cohesion: 0.50
Nodes (3): Output, Product rules you enforce, What you review

### Community 137 - "security-review.md"
Cohesion: 0.50
Nodes (3): Hard rules you enforce, Output, What you review

### Community 138 - "telegram-stars-payments.md"
Cohesion: 0.50
Nodes (3): Output, Rules you enforce, What you review

### Community 139 - "Base"
Cohesion: 0.15
Nodes (19): alembic_script, Base, Base class for all SQLAlchemy models., DeclarativeBase, pytest, _alembic_head(), _load_comments_migration(), _load_event_alert_policy_migration() (+11 more)

### Community 143 - "Project Context"
Cohesion: 0.29
Nodes (6): Current product behavior, Event Alerts, Manual command UX and price lookups, Market Heartbeat, Permanent guardrails, Project Context

### Community 144 - "db/premium.py"
Cohesion: 0.18
Nodes (37): UserPremiumSubscription, UserPremiumTrial, activate_premium_from_telegram_stars_payment(), _activate_premium_from_telegram_stars_payment_locked(), ensure_default_coin_subscriptions(), expire_due_premium_trials(), get_payment_by_provider_id(), get_user_premium_subscription() (+29 more)

### Community 145 - "_runner_private.py"
Cohesion: 0.28
Nodes (15): call_once(), classify(), fail(), main(), persist(), datetime, quota_allows(), Finite direct-provider CCW-16 canary runner; Python stdlib only. This script… (+7 more)

### Community 146 - "_build_exact_event_context_fingerprint"
Cohesion: 0.32
Nodes (13): _build_exact_event_context_fingerprint(), _payload(), parametrize, test_decimal_json_is_full_precision_json_number_not_float_or_string(), test_exact_context_does_not_reuse_the_ambiguous_change_field_contract(), test_exact_context_ignores_previous_title_not_sent_to_model(), test_exact_context_ignores_runtime_metadata_and_normalizes_decimal_representation(), test_exact_context_includes_last_message_time_for_grounding_reuse() (+5 more)

### Community 147 - "os"
Cohesion: 0.10
Nodes (17): asyncpg, bot_services, ctypes, dotenv, openai, os, call(), memory() (+9 more)

### Community 148 - "test_event_alert_composition_investigation.py"
Cohesion: 0.20
Nodes (26): market_direction_claims_supported(), Check explicit period directions and the direction implied by relationships., market(), parametrize, Synthetic regressions for the October alert-composition investigation., test_alignment_fallback_names_direction_and_verified_size_relationship(), test_alignment_without_monotonic_snapshots_survives_compaction(), test_consistent_with_describes_alignment_not_snapshot_persistence() (+18 more)

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.06
Nodes (64): MarketHeartbeatDecision, MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body(), sanitize_heartbeat_possible_action() (+56 more)

### Community 150 - "_send_alert_to_recipient_once"
Cohesion: 0.10
Nodes (22): _delivery_retry_delay_seconds(), _is_permanent_telegram_delivery_error(), _is_transient_telegram_delivery_error(), BaseException, Exactly one confirmed send per attempt. No fallback after uncertain acceptance., Send with retries; returns (sent, error_message, last_exception). The exception…, _retry_after_seconds(), _send_alert_to_recipient() (+14 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.04
Nodes (96): api_key_env(), base_url(), effective_max_tokens_for(), is_reasoning_model(), is_thinking_model(), log_resolved_configuration(), max_tokens_for(), model_for() (+88 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "telegram_error"
Cohesion: 0.31
Nodes (8): handle_application_error(), Global python-telegram-bot error handler. Log-only: never sends anything to…, telegram_error, asyncio, parametrize, Global PTB error handler: concise WARNING for transient network errors, ERROR…, test_non_network_error_logs_error_with_traceback(), test_transient_network_error_logs_one_concise_warning()

### Community 156 - "test_alert_recipients.py"
Cohesion: 0.24
Nodes (9): FakeSession, asyncio, test_event_alert_eligibility_ignores_market_heartbeat_preference(), fake_get_active_users_with_alert_preferences(), test_event_recipient_resolution_is_isolated_from_trial_expiry_failures(), test_get_alert_recipients_deduplicates_active_db_users(), fake_get_active_users_with_alert_preferences(), test_get_alert_recipients_skips_non_btc_events() (+1 more)

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

### Community 164 - "news_intelligence_service.py"
Cohesion: 0.11
Nodes (30): _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text(), _dedup_hint_is_specific_to_title(), _dedup_terms() (+22 more)

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.15
Nodes (20): ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment(), _migration_config() (+12 more)

### Community 169 - "test_news_driven_alerts.py"
Cohesion: 0.50
Nodes (4): asyncio, Regression coverage for the disabled standalone-news Event Alert path., test_news_driven_alerts_warning_logs_once_not_per_cycle(), test_news_driven_flag_cannot_bypass_product_policy()

### Community 170 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 171 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 173 - "bot/reports.py"
Cohesion: 0.07
Nodes (55): MarketReportDecision, Mark news items as seen in PostgreSQL after they were used by the bot., remember_news_context(), _build_daily_report_message(), _build_deterministic_report_decision(), _build_market_report_input(), _build_report_coin_payload(), _build_report_telegram_message() (+47 more)

### Community 174 - "RichDeliveryUncertain"
Cohesion: 0.28
Nodes (8): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert()

### Community 176 - "handlers/reports.py"
Cohesion: 0.21
Nodes (11): daily_report(), DEFAULT_TYPE, Update, Market report command handlers., weekly_report(), send_weekly_report_message(), Groq free-tier admission control (Event Analysis), LLM Usage Reporting (+3 more)

### Community 177 - "test_ccw9_ccw10.py"
Cohesion: 0.16
Nodes (17): CoinGeckoRateLimitError, get_coin_price(), Exception, Raised when CoinGecko returns HTTP 429., Get current coin price and 24h change from CoinGecko. Unsupported symbols raise…, fetch(), asyncio, parametrize (+9 more)

### Community 178 - "test_price_handlers.py"
Cohesion: 0.45
Nodes (11): _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users(), test_price_maps_provider_errors_to_safe_user_messages(), test_price_normalizes_legacy_ton_alias_before_lookup(), test_price_rejects_unsupported_symbol_without_provider_call(), test_price_repeated_calls_are_not_ui_throttled() (+3 more)

### Community 180 - "/graphify"
Cohesion: 0.11
Nodes (16): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+8 more)

### Community 181 - "test_rich_403_preserves_safe_blocked_classification_without_raw_errors"
Cohesion: 0.29
Nodes (3): parametrize, test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post()

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.33
Nodes (5): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps

### Community 183 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 184 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 186 - "0027_market_heartbeat_defaults.py"
Cohesion: 0.70
Nodes (4): downgrade(), _has_alert_frequency_column(), _set_default(), upgrade()

### Community 188 - "database.py"
Cohesion: 0.11
Nodes (27): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), AppSettings, _collapse_whitespace(), _normalize_news_link() (+19 more)

### Community 189 - "news_context.py"
Cohesion: 0.08
Nodes (41): _candidate_news_relevance_label(), classify_news_relevance(), filter_news_for_symbol(), _format_candidate_news(), _has_gram_crypto_context(), _is_clearly_market_wide_news(), is_generic_news_item(), is_material_news_item() (+33 more)

### Community 190 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 193 - "get_or_create_user"
Cohesion: 0.44
Nodes (12): get_or_create_user(), Create or update profile fields for the current Telegram interaction., build_session(), asyncio, test_get_or_create_user_allows_missing_username(), test_get_or_create_user_demotes_existing_admin_removed_from_allowlist(), test_get_or_create_user_keeps_non_admin_role_with_allowlist(), test_get_or_create_user_marks_second_admin_id_from_allowlist() (+4 more)

### Community 194 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 196 - "_build_event_analysis_input"
Cohesion: 0.08
Nodes (43): AnalysedWindowReference, _calculate_price_change(), _canonical_event_analysis_context(), _event_analysis_datetime(), _event_analysis_news_age_hours(), _event_analysis_news_summary(), get_analysed_window_minutes(), datetime (+35 more)

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

### Community 205 - "calculate_price_change_percent"
Cohesion: 0.10
Nodes (20): calculate_price_change_percent(), Decimal, Core alert-rule helpers used by automatic market checks., Calculate a percent change without mixing binary floats and ``Decimal`` values., _event_alert_change_label(), _format_analysed_window_label(), compact_elapsed_since(), _decimal_numeric_context_value() (+12 more)

### Community 206 - "Repository-backed Graphify"
Cohesion: 0.33
Nodes (5): Clones and local development, Repository-backed Graphify, Retention, Shared state in dev, Updates after migration

### Community 207 - "CCW-25 research evidence"
Cohesion: 0.40
Nodes (4): Billing assumptions, CCW-25 research evidence, Interpretation limits, Reproduce

### Community 208 - "0031_onboarding_customize_event.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_event_name_check(), upgrade()

### Community 209 - "operator_prompt.md"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C operator prompt, CCW-41 Reviewer C significance rubric v1, Frozen output schema, Frozen rubric

### Community 210 - "normalize_symbol"
Cohesion: 0.06
Nodes (81): _analysed_window_minutes_from_payload(), _automatic_market_check_job_name(), _build_event_analysis_id(), _build_event_instance_key(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _canonical_decimal_string(), _event_input_hash() (+73 more)

### Community 213 - "0009_error_file_logging_toggle.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 214 - "0026_growth_analytics.py"
Cohesion: 0.90
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 217 - "test_heartbeat_postgres.py"
Cohesion: 0.20
Nodes (13): automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, importlib, postgres_url(), asyncio, Real PostgreSQL locking checks; the SQLite process mutex cannot prove these… (+5 more)

### Community 223 - "build_owner_reference_candidate_v1.py"
Cohesion: 0.15
Nodes (17): csv, hashfile(), main(), metrics(), Versioned private calibration reference from owner's 66 A/C re-decisions.…, write(), main(), Convert complete HTML human reviews to PR1 pinned independent labels. Place… (+9 more)

### Community 224 - "build_llm_messages"
Cohesion: 0.33
Nodes (6): build_llm_messages(), graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), base(), prepare(), add()

### Community 225 - "test_growth_analytics_migration.py"
Cohesion: 0.47
Nodes (5): alembic_config, _alembic_config(), Config, test_growth_analytics_upgrade_backfills_existing_users(), test_premium_trials_upgrade_preserves_existing_premium_and_payment_rows()

### Community 227 - "save_market_report"
Cohesion: 0.33
Nodes (6): get_latest_market_report(), AsyncSession, datetime, Save one cached market report generation attempt., Return the newest cached market report for a cadence., save_market_report()

### Community 228 - "Provider fallback (redundancy)"
Cohesion: 0.33
Nodes (6): Circuit breaker, Event Analysis timeout and operation budget, Historical Gemini 429 quota classification and backoff, Optional OpenAI activation and spend cap, Provider fallback (redundancy), Which 4xx responses fall back

### Community 229 - "test_exhausted_provider_chain_uses_verified_data_fallback"
Cohesion: 0.50
Nodes (5): asyncio, parametrize, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload()

### Community 230 - "users.py"
Cohesion: 0.12
Nodes (23): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), backfill_blocked_users_from_alerts(), get_active_users_with_alert_preferences(), get_active_users_with_chat_ids(), get_user_by_telegram_chat_id(), get_user_role() (+15 more)

## Knowledge Gaps
- **402 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+397 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1606 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `Observability Snippets` to `Ops-Agent Service`, `RichDeliveryUncertain`, `CCWBot Ops-Agent Report Analysis`, `_send_alert_to_recipient_once`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Why does `select()` connect `select` to `LlmUsageLog`, `onboarding.py`, `test_telegram_stars_payments.py`, `test_system_status.py`, `Base`, `test_openai_budget.py`, `test_groq_budget.py`, `test_seen_news_dedup.py`, `db/premium.py`, `test_market_heartbeat.py`, `news_intelligence_service.py`, `test_report_cooldowns.py`, `test_event_alert_pipeline.py`, `test_multicoin_alerts.py`, `bot/news.py`, `db/news.py`, `test_llm_rate_limit_backoff.py`, `system_status.py`, `database.py`, `test_product_analytics.py`, `get_or_create_user`, `User`, `_build_event_analysis_input`, `test_news_intelligence_service.py`, `test_news_intelligence_schema.py`, `datetime`, `analytics.py`, `test_watchlist_ux.py`, `save_market_report`, `users.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `test_event_alert_rich_chart_ux.py`, `Observability Snippets`, `test_rich_market_report_delivery.py`, `bot/alerts.py`, `bot/reports.py`, `_send_alert_to_recipient_once`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 168 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 168 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 74 inferred relationships involving `LLMRouter` (e.g. with `AIInvalidJsonError` and `AIProviderRateLimitError`) actually correct?**
  _`LLMRouter` has 74 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _402 weakly-connected nodes found - possible documentation gaps or missing edges._