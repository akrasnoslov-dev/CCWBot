# Graph Report - CCWBot  (2026-11-06)

## Corpus Check
- 668 files · ~1,170,774 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 36 file(s) not represented in the graph (top: .toml 12, .csv 9, (none) 8)

## Summary
- 6029 nodes · 17757 edges · 227 communities (193 shown, 34 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1468 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `aa85b64a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- json
- event_alert_benchmark.py
- onboarding.py
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
- BundleWriter
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- LLMRateLimitBackoffActive
- bot/health.py
- ai_agent_groq.py
- cli.py
- test_heartbeat_silence.py
- LlmUsageLog
- event_text.py
- properties
- ProviderResult
- test_product_analytics.py
- validate_market_report_output
- properties
- test_gram_render_prompt_reliability.py
- ccw41_reviewer_c_audit.py
- detectors.py
- handlers/__init__.py
- automatic_price_check
- utc_now
- ccw15_prompt_pack.py
- logging
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- test_report_content_rich_and_llm_summary.py
- Observability Snippets
- select
- bot/news.py
- test_event_analysis_free_fallback.py
- news_intelligence_service.py
- make_news_key
- types
- test_llm_rate_limit_backoff.py
- ccw47_runner.py
- AISchemaValidationError
- test_event_analysis_health.py
- _create_event_analysis_decision
- test_llm_outage_detectors.py
- manifest.json
- CCWBot Growth Strategy: 0 -> 1 Premium
- User
- price_service.py
- system_status.py
- test_bundle_and_cli.py
- RichDeliveryUncertain
- test_event_news_trace.py
- test_event_alert_historical_diagnostics.py
- RedactionReport
- test_admin_cleanup.py
- validate_event_significance_output
- _deliver_market_event_alert
- 0001_initial_schema.py
- event_analysis.py
- CCWBot
- conftest.py
- replay_event_significance.py
- 0024_gram_symbol.py
- test_event_alert_composition_investigation.py
- test_agent_workflow_contract.py
- test_event_alert_delivery_quality_regressions.py
- telegram_error
- news_service.py
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- time
- test_event_alert_pr2_cooldown.py
- log
- CCW-20 paired final messages
- event_chart.py
- test_llm_config_budgets.py
- test_watchlist_ux.py
- CCW-47 Final Event Significance Prompt Comparison
- Context Audit Report
- _fixture
- watchlist.py
- refresh_report_cache_scheduled
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- _build_market_heartbeat_payload
- EventAnalysisDecision
- test_event_alert_rich_chart_ux.py
- Ops-Agent Service
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- _build_exact_event_context_fingerprint
- test_event_alert_24h_now_continuity.py
- test_event_alert_chart_markers.py
- test_price_service.py
- Event Alert logic
- Documentation
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
- benchmark.py
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
- _build_event_analysis_input
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
- database.py
- test_growth_analytics_migration.py
- TransientSessions
- Repository Source of Truth
- Development
- test_market_heartbeat.py
- os
- test_heartbeat_postgres.py
- ChatGPT / Bridge / Codex Workflow
- test_alert_section_extraction.py
- collectors/__init__.py
- ops_agent/__init__.py
- test_multicoin_alerts.py
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- test_db_collector_failure_is_isolated_and_later_collectors_continue
- graphify reference: GitHub clone and cross-repo merge
- admin.py
- pkgutil
- test_heartbeat_does_not_query_previous_event
- reviewer-c-rubric.md
- What You Must Do When Invoked
- extraction-spec.md
- db/settings.py
- test_rich_403_preserves_safe_blocked_classification_without_raw_errors
- CCW-41 exploratory Reviewer-C agreement/disagreement
- TransientBot
- 0008_database_comments.py
- bot/reports.py
- _runner_private.py
- _StructuredRecordBuffer
- test_alembic_migrations.py
- test_database_comments.py
- test_price_handlers.py
- FakeAsyncClient
- /graphify
- bot
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- test_report_and_hourly_ingestion_share_serial_llm_budget_gate
- CCW-43 — Evidence-based Event Analysis prompt redesign
- decimal
- alembic/env.py
- P
- 0025_llm_operation_correlation.py
- normalize_symbol
- clean_news_title
- .__init__
- generate_report_cache
- schedule_automatic_btc_check
- CCWBot Operational Report — Unverified (No Production Bundle)
- db/reports.py
- asyncio
- CCW-25 — Self-hosted LLM owner decision
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- CCWBot — blind owner disagreement-only replay
- test_scheduled_ingestion_persists_only_through_existing_intelligence
- Repository-backed Graphify
- CCW-25 research evidence
- operator_prompt.md
- graphify reference: extra exports and benchmark
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- Provider fallback (redundancy)
- FakeResponse
- README_RU.md
- fresh200_luna_wait_start.sh
- openai_luna_wait_start.sh
- pytest
- build_review.py
- coin_icons.py
- 0003_premium_watchlist_foundation.py
- CCW20_FINAL_MESSAGE_BASELINE_20261026.md
- build_owner_reference_candidate_v1.py
- CCW-12 matched Luna significance comparison

## God Nodes (most connected - your core abstractions)
1. `select()` - 173 edges
2. `Period` - 115 edges
3. `Base` - 100 edges
4. `LLMRouter` - 98 edges
5. `normalize_symbol()` - 90 edges
6. `EventAnalysisValidationError` - 79 edges
7. `User` - 68 edges
8. `utc_now()` - 64 edges
9. `run_detectors()` - 64 edges
10. `Alert` - 60 edges

## Surprising Connections (you probably didn't know these)
- `Event Alert chart reference markers (2026-10-26)` --references--> `price()`  [INFERRED]
  docs/alert_logic.md → bot/handlers/price.py
- `Startup configuration log` --references--> `AIProviderRateLimitError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Which 4xx responses fall back` --references--> `AIInvalidJsonError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py
- `Event Alert Regression Evidence` --references--> `unknown()`  [INFERRED]
  docs/ops_agent_service.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (227 total, 34 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.11
Nodes (55): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), check(), check(), check() (+47 more)

### Community 1 - "json"
Cohesion: 0.02
Nodes (57): collections, datetime, html, html_parser, importlib_util, json, math, pathlib (+49 more)

### Community 2 - "event_alert_benchmark.py"
Cohesion: 0.10
Nodes (43): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Read-only local check, random, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, CCW-29 fresh private holdout: collect real POST-200 market cases via…, choose(), Freeze fresh 200 real CCWBot market cases, excluding both earlier sets;… (+35 more)

### Community 3 - "onboarding.py"
Cohesion: 0.11
Nodes (53): ProductEvent, UserCoinSubscription, build_onboarding_keyboard(), _as_aware_utc(), build_instant_brief(), build_onboarding_message(), build_returning_user_message(), _edit_onboarding_message() (+45 more)

### Community 4 - "test_db_queries_and_detectors.py"
Cohesion: 0.04
Nodes (65): alembic_migration, alembic_operations, ops_agent_collectors, _alert_evidence_windows(), datetime, run_detectors(), Period, sqlite3 (+57 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.08
Nodes (75): _backoff_schedule(), breaker_snapshot(), _BreakerState, _failure_threshold(), is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics. (+67 more)

### Community 6 - "telemetry.py"
Cohesion: 0.05
Nodes (79): asyncio, AsyncSession, Update a usage row when downstream JSON schema validation fails., Save one LLM usage telemetry row., save_llm_usage_log(), update_llm_usage_log_status(), _validate(), Provider interface and the shared OpenAI-compatible provider implementation.… (+71 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.08
Nodes (47): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report(), market_report_change_chart() (+39 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.08
Nodes (61): Payment, activate_premium_from_telegram_stars_payment(), Record one Stars payment and extend Premium once for that payment id., Application, register_bot_handlers(), build_premium_activation_keyboard(), build_premium_invoice_payload(), build_premium_prices() (+53 more)

### Community 9 - "common.py"
Cohesion: 0.12
Nodes (28): decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, Edit a transient callback screen without exposing Telegram failures., Best-effort deletion of a user's slash command in a private chat. (+20 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.16
Nodes (50): PriceState, build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., builtins, build_session_factory(), _event_analysis(), _final_failed_alert(), _now() (+42 more)

### Community 11 - "sqlalchemy"
Cohesion: 0.03
Nodes (33): alembic, downgrade(), _unique_constraint_names(), upgrade(), downgrade(), _table_names(), upgrade(), _column_names() (+25 more)

### Community 12 - "test_openai_costs.py"
Cohesion: 0.05
Nodes (94): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., _cost(), monthly_budget_usd(), OpenAIBudget, OpenAIBudgetExhausted, OpenAIBudgetLease, _positive_decimal_env() (+86 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.04
Nodes (73): alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.…, SeverityEvaluation (+65 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.15
Nodes (22): _Charge, GroqBudget, GroqBudgetExhausted, datetime, Test-only reset; production restarts reload persisted usage., GroqProvider, Groq provider (primary). OpenAI-compatible chat-completions API., asyncio (+14 more)

### Community 15 - "BundleWriter"
Cohesion: 0.11
Nodes (15): BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk., sha256_file() (+7 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (67): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+59 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.07
Nodes (56): ask_event_analysis_raw(), _parse_json(), Parse a JSON-object response without relaxing schema validation., parametrize, _set_groq_client(), test_event_alert_render_schema_only_contains_model_generated_fields(), test_event_analysis_prompt_makes_llm_the_market_significance_decider(), test_event_analysis_prompt_preserves_subpercent_values_as_percentages() (+48 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (79): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+71 more)

### Community 19 - "LLMRateLimitBackoffActive"
Cohesion: 0.11
Nodes (24): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., LLMRateLimitBackoffActive, Raised when a provider/model is already in temporary rate-limit backoff., GeminiProvider (+16 more)

### Community 20 - "bot/health.py"
Cohesion: 0.17
Nodes (18): aiohttp, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any, datetime, Authoritative last successful Event Analysis time, or None when unavailable.…, Read terminal Render outcomes independently of significance health. (+10 more)

### Community 21 - "ai_agent_groq.py"
Cohesion: 0.04
Nodes (69): Ground-truth evidence and limitations, Versioned artifacts, AnalysedWindowReference, _canonical_decimal_string(), _event_analysis_datetime(), _event_analysis_news_age_hours(), _event_analysis_news_summary(), _json_dumps() (+61 more)

### Community 22 - "cli.py"
Cohesion: 0.14
Nodes (31): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+23 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.11
Nodes (27): pytest_asyncio, fake_get_active_users_with_alert_preferences(), add_delivery(), asyncio, parametrize, test_cache_expiring_before_lock_acquisition_is_not_sent(), test_concurrent_checks_send_one_heartbeat_and_reset_timer(), test_delayed_success_uses_completion_not_reservation() (+19 more)

### Community 24 - "LlmUsageLog"
Cohesion: 0.11
Nodes (32): LlmUsageLog, Clear all state (tests and controlled restarts)., reset(), _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider…, Compute 24h terminal outcomes. Raises on DB errors; never returns fake OK. (+24 more)

### Community 25 - "event_text.py"
Cohesion: 0.04
Nodes (100): _action_price_levels_supported(), _action_without_negated_technical_levels(), compact_event_alert_possible_action(), compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback() (+92 more)

### Community 26 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 27 - "ProviderResult"
Cohesion: 0.09
Nodes (31): ABC, ask_event_significance_raw(), ask_market_heartbeat_raw(), ask_news_intelligence_raw(), _json_response_validator(), Return JSON mode and provider-specific schemas for verified model attempts., _structured_response_formats(), BaseProvider (+23 more)

### Community 28 - "test_product_analytics.py"
Cohesion: 0.06
Nodes (59): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+51 more)

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "test_gram_render_prompt_reliability.py"
Cohesion: 0.15
Nodes (12): LogicalHealth, test_health_counts_no_alert_as_a_successful_analysis(), _logical_success(), _gram_market(), asyncio, Offline regressions for GRAM Render grounding and separate health telemetry., test_gram_render_prompt_separates_window_day_and_earlier_steps(), test_gram_render_validator_preserves_direction_safety() (+4 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.07
Nodes (72): audit(), positive_age_minutes(), ranking(), main(), _number(), _time(), _aggregate_markdown(), _cli() (+64 more)

### Community 33 - "detectors.py"
Cohesion: 0.11
Nodes (35): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+27 more)

### Community 34 - "handlers/__init__.py"
Cohesion: 0.13
Nodes (42): acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), chat_id(), error_logging_off(), error_logging_on(), error_logging_status() (+34 more)

### Community 35 - "automatic_price_check"
Cohesion: 0.17
Nodes (17): _analysed_window_minutes_from_payload(), _build_event_analysis_id(), _event_input_hash(), _raw_event_key_from_payload(), _semantic_family_from_payload(), automatic_price_check(), _event_context_fingerprint(), _event_numeric_context() (+9 more)

### Community 36 - "utc_now"
Cohesion: 0.15
Nodes (36): MarketReport, datetime, Return timezone-aware UTC timestamp., utc_now(), reports(), get_or_generate_report(), _is_completed_report(), _is_fresh_report() (+28 more)

### Community 37 - "ccw15_prompt_pack.py"
Cohesion: 0.14
Nodes (17): Stage verified model-visible pilot calls into isolated CCW-16 workspace. No…, CCW-43 offline source verification, paired scoring, and restricted case error…, build_prompt(), check_production_parity(), inspect_private_frozen(), instruction(), main(), Path (+9 more)

### Community 38 - "logging"
Cohesion: 0.08
Nodes (48): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports(), _collect_secret_values() (+40 more)

### Community 39 - "LLMRouter"
Cohesion: 0.15
Nodes (57): AIProviderRateLimitError, Raised when a provider refuses a request because the account is rate limited., LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider (+49 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.07
Nodes (42): _event_alert_presentation_title(), _has_non_flat_analysed_market_context(), _llm_no_alert_decision_reason(), Render the headline from the primary deterministic metric, not LLM prose., contextlib, _assert_invalid_stage2(), _event_input(), asyncio (+34 more)

### Community 42 - "test_report_content_rich_and_llm_summary.py"
Cohesion: 0.19
Nodes (15): MarketReportDecision, _build_report_telegram_message(), _decision(), asyncio, parametrize, Regression contracts for content-rich cached reports and concise admin…, test_admin_llm_summary_is_compact_and_provider_details_are_separate(), test_llm_summary_uses_fresh_bounded_24h_query_not_cumulative_snapshot() (+7 more)

### Community 43 - "Observability Snippets"
Cohesion: 0.08
Nodes (29): consecutive_failures(), Output, Rules you enforce, What you review, Admin System Status, Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis (+21 more)

### Community 44 - "select"
Cohesion: 0.05
Nodes (114): _get_or_create_event_alert_market_event(), main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery() (+106 more)

### Community 45 - "bot/news.py"
Cohesion: 0.09
Nodes (44): _alert_news_rank(), classify_news_relevance(), _is_clearly_market_wide_news(), _major_market_incident(), Evidence-backed systemic incident, independent of coin tagging. This is a…, Use article evidence for direct and substantive market-wide relevance., Impact dominates primary tags; direct relevance resolves close rankings., _dedupe_report_news() (+36 more)

### Community 46 - "test_event_analysis_free_fallback.py"
Cohesion: 0.16
Nodes (25): global_provider_priority(), _parse_priority_list(), provider_priority(), Parse a comma-separated provider list, warning about names that are not…, Resolve the ordered provider chain for a call type. Per-call-type override env…, _configure(), _event_call(), _http_error() (+17 more)

### Community 47 - "news_intelligence_service.py"
Cohesion: 0.08
Nodes (48): _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text(), _dedup_hint_is_specific_to_title(), _dedup_terms() (+40 more)

### Community 48 - "make_news_key"
Cohesion: 0.07
Nodes (44): _collapse_whitespace(), make_news_key(), _normalize_news_link(), Normalize repeated spaces so keys stay stable across feed formatting., Return a stable URL string for news identity checks., Build a stable key for a news item. Links are preferred because RSS titles can…, SeenNews, cleanup_seen_news() (+36 more)

### Community 49 - "types"
Cohesion: 0.08
Nodes (19): Runtime state and startup helpers., close_database(), initialize_database(), Any, Dispose database resources created during startup., SessionFactoryRef, _sync_package_database_engine(), test_report_scheduler_check_interval_fits_refresh_grace() (+11 more)

### Community 50 - "test_llm_rate_limit_backoff.py"
Cohesion: 0.08
Nodes (38): CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions…, get_provider(), get_provider(), OpenAIProvider, OpenAI paid fallback, guarded by an explicit kill switch and durable budget., _default_registry() (+30 more)

### Community 51 - "ccw47_runner.py"
Cohesion: 0.10
Nodes (20): pct(), Path, quality(), sha(), canonical(), compact(), execute(), load() (+12 more)

### Community 52 - "AISchemaValidationError"
Cohesion: 0.12
Nodes (30): AIInvalidJsonError, AISchemaValidationError, datetime, Exception, RuntimeError, Raised when the provider response is not valid JSON., Raised when validated JSON does not match the expected schema. ``raw_content``…, Circuit breaker (+22 more)

### Community 53 - "test_event_analysis_health.py"
Cohesion: 0.08
Nodes (34): _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, bot_observability, evaluate_state(), failure_escalation_threshold(), max_success_age_seconds(), datetime, In-process health signal for Event Analysis. Event Alerts were fully dead for… (+26 more)

### Community 54 - "_create_event_analysis_decision"
Cohesion: 0.11
Nodes (47): _as_news_only_rejected_decision(), _create_event_analysis_decision(), _render_schema_check(), _event_alert_render_result_for_validation(), _event_alert_render_validation_reason(), _no_alert_decision_from_significance(), _normalize_render_section_labels(), _percent_claim_value() (+39 more)

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
Cohesion: 0.14
Nodes (31): User, get_active_users_with_alert_preferences(), get_active_users_with_chat_ids(), get_or_create_user(), get_user_by_telegram_chat_id(), get_user_role(), is_telegram_chat_delivery_enabled(), mark_user_bot_blocked() (+23 more)

### Community 59 - "price_service.py"
Cohesion: 0.11
Nodes (33): _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), _extract_sparkline_prices(), get_btc_market_data(), get_btc_price(), _get_cached_price(), get_report_market_data_batch() (+25 more)

### Community 60 - "system_status.py"
Cohesion: 0.11
Nodes (41): _age_label(), _ai_health(), _as_utc(), build_admin_llm_diagnostics_text(), build_admin_llm_summary_html(), ComponentHealth, _container_started_at(), _delivery_failure_category() (+33 more)

### Community 61 - "test_bundle_and_cli.py"
Cohesion: 0.06
Nodes (48): ops_agent, _mark_report_success(), load_state(), parse_timestamp(), Any, datetime, Path, record_collection() (+40 more)

### Community 62 - "RichDeliveryUncertain"
Cohesion: 0.28
Nodes (8): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert()

### Community 63 - "test_event_news_trace.py"
Cohesion: 0.17
Nodes (12): _compact_event_analysis_news(), _log_event_news_trace(), Log one shared prepared payload, never validation attempts or recipient data., asyncio, parametrize, test_news_trace_allows_empty_selection(), test_news_trace_counts_actual_payload_without_exposing_contents(), test_news_trace_distinguishes_presentation_cap_from_relevance() (+4 more)

### Community 64 - "test_event_alert_historical_diagnostics.py"
Cohesion: 0.33
Nodes (10): build_event_significance_prompt(), _market(), parametrize, Historical alert defect contracts: never call an external provider or Telegram.…, test_contradictory_period_alignment_is_never_delivered_as_factual_claim(), test_exact_reuse_excludes_changed_micro_moves_and_news(), test_grounded_render_survives_final_message_without_generic_substitution(), test_historical_numeric_keys_cannot_fragment_directional_identity() (+2 more)

### Community 65 - "RedactionReport"
Cohesion: 0.06
Nodes (79): dataclasses, _collect_alert_repetition_rows(), collect_db(), _collector_error(), _jsonable(), Any, Exception, _successful_alert_repetition_buckets() (+71 more)

### Community 66 - "test_admin_cleanup.py"
Cohesion: 0.14
Nodes (16): AsyncFalse, AsyncTrue, _callback_update(), _callback_values(), FakeMessage, FakeQuery, asyncio, test_admin_alert_settings_keyboard_has_no_threshold_controls() (+8 more)

### Community 67 - "validate_event_significance_output"
Cohesion: 0.17
Nodes (16): empirical_absolute_move_percentile(), EventSignificanceDecision, Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., validate_event_significance_output(), _significance_schema_check(), _payload(), parametrize (+8 more)

### Community 68 - "_deliver_market_event_alert"
Cohesion: 0.06
Nodes (54): AlertRecipient, _automatic_delivery_lock(), _count_suppression(), _deliver_market_event_alert(), _delivery_error_class_name(), _delivery_retry_delay_seconds(), _disable_recipient_if_bot_blocked(), EventRecipientFilterResult (+46 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "event_analysis.py"
Cohesion: 0.06
Nodes (72): CanonicalEventKey, canonicalize_event_key(), _claim_clause(), _claimed_percent(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal() (+64 more)

### Community 71 - "CCWBot"
Cohesion: 0.10
Nodes (20): Admin System Status, CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables (+12 more)

### Community 72 - "conftest.py"
Cohesion: 0.36
Nodes (7): _real_socket, _guarded_create_connection(), _guarded_getaddrinfo(), _GuardedSocket, _is_loopback(), _is_loopback_address(), _raise_external_network_block()

### Community 73 - "replay_event_significance.py"
Cohesion: 0.09
Nodes (30): _groq_json_mode_enabled(), scripts, classify_replay_error(), groq_significance_response_format(), live_report(), load_cases(), NonObjectSignificanceError, offline_report() (+22 more)

### Community 74 - "0024_gram_symbol.py"
Cohesion: 0.33
Nodes (13): _coerce_related_symbols(), _column_names(), downgrade(), _has_table_and_symbol(), _has_table_columns(), _merge_price_state(), _merge_user_coin_subscriptions(), _merge_user_symbol_alert_state() (+5 more)

### Community 75 - "test_event_alert_composition_investigation.py"
Cohesion: 0.18
Nodes (29): market_direction_claims_supported(), Check explicit period directions and the direction implied by relationships., market(), parametrize, Synthetic regressions for the October alert-composition investigation., test_alignment_fallback_names_direction_and_verified_size_relationship(), test_alignment_without_monotonic_snapshots_survives_compaction(), test_comparative_strength_does_not_reverse_explicit_direction() (+21 more)

### Community 76 - "test_agent_workflow_contract.py"
Cohesion: 0.19
Nodes (10): _adapter_path(), _agent_names(), _agent_paths(), _load_toml(), Path, test_agent_definitions_have_matching_claude_adapters(), test_agent_definitions_have_required_schema(), test_agent_routing_references_existing_agents() (+2 more)

### Community 77 - "test_event_alert_delivery_quality_regressions.py"
Cohesion: 0.19
Nodes (21): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, test_specific_next_observation_is_not_generic(), _decision(), _market(), parametrize, Regressions from 2026-10-13 delivered Event Alerts. These assertions inspect…, _render() (+13 more)

### Community 78 - "telegram_error"
Cohesion: 0.31
Nodes (8): handle_application_error(), Global python-telegram-bot error handler. Log-only: never sends anything to…, telegram_error, asyncio, parametrize, Global PTB error handler: concise WARNING for transient network errors, ERROR…, test_non_network_error_logs_error_with_traceback(), test_transient_network_error_logs_one_concise_warning()

### Community 79 - "news_service.py"
Cohesion: 0.13
Nodes (23): headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Low-cost, word-boundary-aware prefilter; not an alert decision., Bound provider latency/response size; parse only successfully fetched bytes., Return one usable publisher feed; never fetch the mirror on primary success. (+15 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.12
Nodes (53): LlmOperationOutcome, NewsItem, LLM usage telemetry persistence. Belongs here: saving and updating…, Persist one sanitized terminal outcome for a logical LLM operation., save_llm_operation_outcome(), AsyncSession, Return stored, intelligence-ranked news candidates for a symbol. This selector…, select_intelligence_news_for_symbol() (+45 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "time"
Cohesion: 0.07
Nodes (44): concurrent_futures, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., atom(), call_one(), check_reply() (+36 more)

### Community 83 - "test_event_alert_pr2_cooldown.py"
Cohesion: 0.39
Nodes (8): _db(), asyncio, parametrize, PR 2 regressions for confirmed semantic cooldown boundary defects. No provider,…, Two distinct event rows can pass prefilter before the first send finishes., test_incomplete_persisted_identity_uses_own_verified_market_move(), test_late_delivery_remains_in_semantic_cooldown_query(), test_stale_prefilter_cannot_bypass_in_lock_cooldown()

### Community 84 - "log"
Cohesion: 0.07
Nodes (49): AbstractEventLoop, AppRunner, _automatic_market_check_job_name(), cleanup_seen_news_job(), schedule_automatic_market_check(), schedule_market_heartbeat_generation(), schedule_seen_news_cleanup(), Alert and heartbeat use-case entrypoints. (+41 more)

### Community 85 - "CCW-20 paired final messages"
Cohesion: 0.09
Nodes (21): 10. ev_3c7f3da2e73e4b90 — ETH, 11. ev_7804adc277bd3333 — GRAM, 12. ev_345fc49db8255adf — GRAM, 13. ev_7b3325d2f2609480 — GRAM, 14. ev_1b39a518ede3c14f — GRAM, 15. ev_6500c5ad9f5364bc — GRAM, 16. ev_4bba21dd01bc8372 — SOL, 17. ev_1ea4cea05b78ed5c — SOL (+13 more)

### Community 86 - "event_chart.py"
Cohesion: 0.14
Nodes (18): _display_marker_label(), _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw, Deterministic PNG chart from persisted, timestamped price observations only., Auditable reference value and its actual, not nominal, UTC timestamp. (+10 more)

### Community 87 - "test_llm_config_budgets.py"
Cohesion: 0.03
Nodes (138): _get_int_env(), api_key(), api_key_env(), base_url(), effective_max_tokens_for(), event_analysis_operation_budget_seconds(), _format_chain(), is_reasoning_model() (+130 more)

### Community 88 - "test_watchlist_ux.py"
Cohesion: 0.06
Nodes (45): build_watchlist_keyboard(), build_subscribe_message(), build_watchlist_render(), AsyncFalse, AsyncNoop, AsyncTrue, build_session(), CallbackQuery (+37 more)

### Community 89 - "CCW-47 Final Event Significance Prompt Comparison"
Cohesion: 0.08
Nodes (23): CCW-47 Final Event Significance Prompt Comparison, confidence, Coverage and per-coin decisions, Decision differences, Distributions, Eight owner-ambiguous cases (excluded from scoring), Final recommendation, Focused error analysis (+15 more)

### Community 90 - "Context Audit Report"
Cohesion: 0.07
Nodes (18): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+10 more)

### Community 91 - "_fixture"
Cohesion: 0.12
Nodes (24): _canonical_event_analysis_context(), Semantic model and grounding context used for exact pre-LLM reuse., Clear all breaker state (tests and controlled restarts)., reset_breakers(), _isolate_llm_breaker_state(), _test_verified_groq_routing(), _reset_state(), _estimate_tokens() (+16 more)

### Community 92 - "watchlist.py"
Cohesion: 0.11
Nodes (53): _as_aware_utc(), can_deliver_market_heartbeat_now(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active() (+45 more)

### Community 93 - "refresh_report_cache_scheduled"
Cohesion: 0.16
Nodes (24): _freshness_seconds(), _get_fresh_cached_report(), _is_fresh_memory_report(), _log_scheduled_refresh_skip(), Any, Return timezone-aware (generated_at, expires_at) for a DB or in-memory report., True when the cached report survives past the scheduled-refresh grace window., Scheduled cache refresh: regenerate unless the cache stays fresh past the grace… (+16 more)

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.17
Nodes (11): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Log pattern counting, News-candidate signal (+3 more)

### Community 96 - "_build_market_heartbeat_payload"
Cohesion: 0.09
Nodes (25): _event_alert_change_label(), _format_analysed_window_label(), compact_elapsed_since(), _build_market_heartbeat_html_message(), _build_market_heartbeat_payload(), _decimal_numeric_context_value(), _deterministic_event_text(), _enabled_subscription_by_symbol() (+17 more)

### Community 97 - "EventAnalysisDecision"
Cohesion: 0.08
Nodes (46): EventAnalysisDecision, filter_news_for_symbol(), _build_event_alert_html_message(), _build_event_alert_payload(), _event_news_shortlist_limit(), _get_reusable_event_analysis_by_context(), _preserve_render_prose(), Minimal whitespace normalization; retain the model's paragraph structure. (+38 more)

### Community 98 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.15
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

### Community 105 - "_build_exact_event_context_fingerprint"
Cohesion: 0.29
Nodes (15): _build_exact_event_context_fingerprint(), _payload(), parametrize, test_ccw349_invalid_headline_does_not_hide_second_valid_headline(), test_ccw349_news_priority_changes_model_visible_context_and_fingerprint(), test_decimal_json_is_full_precision_json_number_not_float_or_string(), test_exact_context_does_not_reuse_the_ambiguous_change_field_contract(), test_exact_context_ignores_previous_title_not_sent_to_model() (+7 more)

### Community 106 - "test_event_alert_24h_now_continuity.py"
Cohesion: 0.27
Nodes (12): bot_alerting, _connectable_now_segment(), Join two genuine observations only within the documented 45m cadence., decision(), history(), market_payload(), Event Alert metric/title and true observed NOW continuity regressions., test_24h_metric_and_unambiguous_header_in_all_delivery_formats() (+4 more)

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.32
Nodes (18): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+10 more)

### Community 108 - "test_price_service.py"
Cohesion: 0.13
Nodes (21): _extract_ton_coin_data_from_simple_price(), get_coin_market_data_batch(), get_coin_price(), Get current coin price and 24h change from CoinGecko. Unsupported symbols raise…, Fetch market data for supported symbols with one CoinGecko request. Missing…, Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., clean_price_caches(), clear_price_caches() (+13 more)

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

### Community 113 - "benchmark.py"
Cohesion: 0.14
Nodes (17): argparse, build_llm_messages(), graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), copy, ctypes, base(), call() (+9 more)

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

### Community 129 - "_build_event_analysis_input"
Cohesion: 0.11
Nodes (34): _calculate_price_change(), get_analysed_window_minutes(), _build_event_analysis_input(), _build_market_heartbeat_input(), _compact_event_snapshot(), _compact_event_snapshots(), _historical_event_analysis_moves(), _load_news_driven_alert_candidates() (+26 more)

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
Cohesion: 0.18
Nodes (15): CoinGeckoRateLimitError, Exception, Raised when CoinGecko returns HTTP 429., fetch(), asyncio, parametrize, Regression coverage for CCW-9 transient command screens and CCW-10 price cache., test_admin_settings_navigation_remembers_entry_origin() (+7 more)

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

### Community 144 - "database.py"
Cohesion: 0.12
Nodes (48): Record one typed event; a duplicate lifecycle key returns the original., record_product_event(), AppSettings, Base, Database infrastructure for optional PostgreSQL runtime storage., Run Alembic migrations without blocking the active event loop., Base class for all SQLAlchemy models., run_async_upgrade() (+40 more)

### Community 145 - "test_growth_analytics_migration.py"
Cohesion: 0.47
Nodes (5): alembic_config, _alembic_config(), Config, test_growth_analytics_upgrade_backfills_existing_users(), test_premium_trials_upgrade_preserves_existing_premium_and_payment_rows()

### Community 147 - "Repository Source of Truth"
Cohesion: 0.33
Nodes (5): Canonical ownership, Conflict resolution, No standing rules outside the repository, Repository bootstrap, Repository Source of Truth

### Community 148 - "Development"
Cohesion: 0.15
Nodes (8): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.08
Nodes (54): _build_market_heartbeat_id(), MarketHeartbeatDecision, MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body() (+46 more)

### Community 150 - "os"
Cohesion: 0.09
Nodes (13): asyncpg, bot_services, bot_services_llm, dotenv, openai, Model identifiers the shipped bot defaults to, for drift detection. The ops-…, os, CCW-25: bounded read-only aggregate collection; never exports prompts or IDs. (+5 more)

### Community 151 - "test_heartbeat_postgres.py"
Cohesion: 0.20
Nodes (13): automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, importlib, postgres_url(), asyncio, Real PostgreSQL locking checks; the SQLite process mutex cannot prove these… (+5 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "test_alert_section_extraction.py"
Cohesion: 0.40
Nodes (5): asyncio, parametrize, Execute the production aggregate SQL using synthetic final Telegram messages., test_delivery_failure_sql_distinguishes_both_error_fields(), test_final_section_sql_handles_newlines_fanout_and_missing_sections()

### Community 156 - "test_multicoin_alerts.py"
Cohesion: 0.16
Nodes (25): AlertRecipientResolution, Return active market symbols independently of current recipient eligibility., resolve_symbols_to_check(), set_user_coin_subscription(), build_session_factory(), create_user(), asyncio, parametrize (+17 more)

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
Cohesion: 0.14
Nodes (5): DbQuery, Assert every collector SQL statement is a read-only, single, unterminated…, validate_read_only_queries(), test_all_db_queries_are_read_only_and_parameterized(), test_db_collector_failure_is_isolated_and_later_collectors_continue()

### Community 162 - "admin.py"
Cohesion: 0.08
Nodes (65): _build_admin_llm_diagnostics_text(), _build_admin_openai_costs_text(), _build_admin_system_status_text(), _build_error_logging_status_text(), _format_admin_alert_settings(), _llm_diagnostics_menu(), _premium_grant_usage_text(), _premium_revoke_usage_text() (+57 more)

### Community 164 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "db/settings.py"
Cohesion: 0.47
Nodes (8): UserSettings, _get_app_settings_row(), get_or_create_app_settings(), get_or_create_user_settings(), AsyncSession, Global and legacy per-user settings persistence. Belongs here: app-wide alert…, update_app_settings(), update_user_settings()

### Community 169 - "test_rich_403_preserves_safe_blocked_classification_without_raw_errors"
Cohesion: 0.08
Nodes (8): parametrize, test_integrity_conflict_preserves_terminal_delivery_reservation(), test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post(), test_rich_confirmed_telegram_rejections(), post(), test_rich_success_without_valid_receipt_is_uncertain(), post()

### Community 170 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 171 - "TransientBot"
Cohesion: 0.33
Nodes (6): Intercept only messages sent in the scope of a manual command/callback., _tracking(), TransientBot, with_close_button(), ExtBot, test_close_markup_preserves_other_actions_and_does_not_duplicate()

### Community 172 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 173 - "bot/reports.py"
Cohesion: 0.07
Nodes (42): schedule_report_cache_generation(), Market report use-case entrypoints., _build_daily_report_message(), _build_deterministic_report_decision(), _build_market_report_input(), _build_report_coin_payload(), _build_weekly_breadth(), _build_weekly_coin_context() (+34 more)

### Community 174 - "_runner_private.py"
Cohesion: 0.28
Nodes (15): call_once(), classify(), fail(), main(), persist(), datetime, quota_allows(), Finite direct-provider CCW-16 canary runner; Python stdlib only. This script… (+7 more)

### Community 175 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 176 - "test_alembic_migrations.py"
Cohesion: 0.15
Nodes (20): ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment(), _migration_config() (+12 more)

### Community 177 - "test_database_comments.py"
Cohesion: 0.29
Nodes (9): alembic_script, _alembic_head(), _load_comments_migration(), _load_event_alert_policy_migration(), _load_market_heartbeat_migration(), asyncio, test_all_tables_and_columns_have_comments(), test_database_comments_migration_applies_to_head() (+1 more)

### Community 178 - "test_price_handlers.py"
Cohesion: 0.40
Nodes (12): clear_manual_price_rate_limits(), _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users(), test_price_maps_provider_errors_to_safe_user_messages(), test_price_normalizes_legacy_ton_alias_before_lookup(), test_price_rejects_unsupported_symbol_without_provider_call() (+4 more)

### Community 180 - "/graphify"
Cohesion: 0.09
Nodes (18): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+10 more)

### Community 181 - "bot"
Cohesion: 0.50
Nodes (4): bot, Replay published CCW-20 final-copy candidates offline through actual assembly.…, _recorded_candidate_pairs(), test_ccw20_replay_all_20_recorded_candidate_final_pairs_without_llm_calls()

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.33
Nodes (5): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps

### Community 184 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 185 - "decimal"
Cohesion: 0.24
Nodes (11): calculate_price_change_percent(), is_cooldown_active(), datetime, Decimal, Core alert-rule helpers used by automatic market checks., Calculate a percent change without mixing binary floats and ``Decimal`` values., Return True while a previous alert is still inside the cooldown window., decimal (+3 more)

### Community 186 - "alembic/env.py"
Cohesion: 0.24
Nodes (10): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), downgrade(), _replace_event_name_check(), upgrade() (+2 more)

### Community 188 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 189 - "normalize_symbol"
Cohesion: 0.05
Nodes (69): _build_event_instance_key(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _event_instance_bucket(), _event_instance_key_for_decision(), _stable_related_news_ids(), _candidate_news_relevance_label(), _coin_name() (+61 more)

### Community 190 - "clean_news_title"
Cohesion: 0.32
Nodes (10): _format_event_related_context(), _format_market_heartbeat_related_context(), _format_related_context(), _safe_telegram_link_url(), _utf16_length(), clean_news_title(), clean_related_news_text(), test_clean_news_title_preserves_non_matching_titles() (+2 more)

### Community 192 - "generate_report_cache"
Cohesion: 0.14
Nodes (17): Mark news items as seen in PostgreSQL after they were used by the bot., remember_news_context(), generate_report_cache(), _schema_check(), Exception, Collapse a validation message to one log-safe token. Validation messages are…, Generate one market-wide LLM report and cache the completed or failed attempt., _sanitize_schema_failure_detail() (+9 more)

### Community 193 - "schedule_automatic_btc_check"
Cohesion: 0.40
Nodes (3): Compatibility wrapper for older imports; schedules the market-wide check., schedule_automatic_btc_check(), test_legacy_automatic_btc_scheduler_alias_uses_market_job_name()

### Community 194 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 195 - "db/reports.py"
Cohesion: 0.32
Nodes (7): get_latest_market_report(), AsyncSession, datetime, Market report cache persistence. Belongs here: daily/weekly market report cache…, Save one cached market report generation attempt., Return the newest cached market report for a cadence., save_market_report()

### Community 196 - "asyncio"
Cohesion: 0.11
Nodes (9): asyncio, test_event_chart_file_id_reused_across_recipients_in_one_dispatch(), test_heartbeat_falls_back_to_styled_html_if_rich_adapter_has_no_token(), test_rich_ambiguous_error_never_falls_back_or_retries(), test_rich_confirmed_bad_request_falls_back_once(), test_rich_httpx_transport_uncertainty_prevents_fallback(), test_transport_reuses_file_id_and_handles_valid_response(), post() (+1 more)

### Community 197 - "CCW-25 — Self-hosted LLM owner decision"
Cohesion: 0.25
Nodes (7): Actual local screen, CCW-25 — Self-hosted LLM owner decision, Low-risk next decision, Monthly EUR / DKK comparison, Specific candidates and serving stack, Volume sensitivity and break-even, What is measured

### Community 198 - "CCW-41 owner-reviewed significance reference v1"
Cohesion: 0.29
Nodes (6): Asset-specific labels, CCW-41 owner-reviewed significance reference v1, Historical bot against reference (selected benchmark only), How disputed labels changed, Using this reference for future model prompts, Warrant distributions

### Community 199 - "_working_code_backup.py"
Cohesion: 0.14
Nodes (32): event_alert_benchmark, Private CCW16 summary: downloads only restricted experiment ledger, never keys…, _aggregate_markdown(), _cli(), compare_reviewers(), _field_exists(), _group_metrics(), import_results() (+24 more)

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

### Community 210 - "graphify reference: extra exports and benchmark"
Cohesion: 0.18
Nodes (10): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000) (+2 more)

### Community 213 - "Provider fallback (redundancy)"
Cohesion: 0.17
Nodes (11): Admin OpenAI Platform Costs monitoring (optional, read-only), Current Event Alert Luna-only policy (owner update 2026-10-29), Event Analysis timeout and operation budget, Groq free-tier admission control (Event Analysis), Historical CCW-20 Event Alert provider order (superseded), Historical Gemini 429 quota classification and backoff, LLM Usage Reporting, Ops-Agent LLM Usage Evidence (+3 more)

### Community 214 - "FakeResponse"
Cohesion: 0.20
Nodes (5): FakeClient, FakeResponse, test_get_coin_price_429_triggers_retry(), __init__(), test_get_with_retry_sends_demo_api_key()

### Community 222 - "pytest"
Cohesion: 0.14
Nodes (9): pytest, socket, parametrize, Guards the test-suite network safety net installed in tests/conftest.py. If…, test_fallback_provider_hosts_are_blocked(), asyncio, Regression coverage for the disabled standalone-news Event Alert path., test_news_driven_alerts_warning_logs_once_not_per_cycle() (+1 more)

### Community 223 - "build_review.py"
Cohesion: 0.32
Nodes (11): candidate(), canon(), context(), csvwrite(), main(), Private read-only CCWBot market benchmark and independent review CSV exporter., run_psql(), safe() (+3 more)

### Community 227 - "coin_icons.py"
Cohesion: 0.22
Nodes (13): Escape all model/news wording; only safely link explicit HTTP(S) sources., _report_coin_icon_html(), _safe_rich_line(), _coin_fallback_emoji(), build_coin_icon_html(), build_coin_icon_prefix(), coin_custom_emoji_id(), coin_fallback_emoji() (+5 more)

### Community 229 - "0003_premium_watchlist_foundation.py"
Cohesion: 0.80
Nodes (4): _column_names(), downgrade(), _table_names(), upgrade()

### Community 233 - "build_owner_reference_candidate_v1.py"
Cohesion: 0.13
Nodes (17): csv, hashfile(), main(), metrics(), Versioned private calibration reference from owner's 66 A/C re-decisions.…, write(), main(), Convert complete HTML human reviews to PR1 pinned independent labels. Place… (+9 more)

### Community 246 - "CCW-12 matched Luna significance comparison"
Cohesion: 0.40
Nodes (4): CCW-12 matched Luna significance comparison, Changed binary decisions, Limits, Matched comparison

## Knowledge Gaps
- **463 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+458 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1771 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `Observability Snippets` to `Ops-Agent Service`, `asyncio`, `CCWBot Ops-Agent Report Analysis`, `RichDeliveryUncertain`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `test_event_alert_rich_chart_ux.py`, `_deliver_market_event_alert`, `asyncio`, `test_rich_market_report_delivery.py`, `test_rich_403_preserves_safe_blocked_classification_without_raw_errors`, `Observability Snippets`, `bot/alerts.py`, `bot/reports.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `CCWBot` connect `CCWBot` to `Observability Snippets`, `Development`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 170 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 170 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _463 weakly-connected nodes found - possible documentation gaps or missing edges._