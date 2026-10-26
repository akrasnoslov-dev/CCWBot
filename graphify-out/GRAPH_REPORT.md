# Graph Report - CCWBot  (2026-10-26)

## Corpus Check
- 638 files · ~1,135,088 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 33 file(s) not represented in the graph (top: .toml 12, (none) 8, .csv 6)

## Summary
- 5574 nodes · 16576 edges · 229 communities (194 shown, 35 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1399 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `51830892`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- replay_event_significance.py
- test_logical_llm_health.py
- onboarding.py
- Period
- test_llm_breaker.py
- telemetry.py
- test_rich_market_report_delivery.py
- test_telegram_stars_payments.py
- common.py
- test_system_status.py
- alembic
- test_openai_budget.py
- bot/alerts.py
- test_groq_budget.py
- test_watchlist_ux.py
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- event_alert_benchmark.py
- log
- User
- runtime/state.py
- test_heartbeat_silence.py
- test_bundle_and_cli.py
- event_text.py
- test_seen_news_dedup.py
- bot/reports.py
- _StructuredRecordBuffer
- validate_market_report_output
- properties
- watchlist.py
- ccw41_reviewer_c_audit.py
- detectors.py
- admin.py
- Observability Snippets
- test_report_cooldowns.py
- classify_ai_error_reason
- logging
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- provider_attempts
- test_multicoin_alerts.py
- select
- bot/news.py
- _runner_private.py
- test_prod_runtime_diagnostic_fixes.py
- db/news.py
- utc_now
- router.py
- _build_market_heartbeat_payload
- test_event_alert_render_provider_chain.py
- test_event_analysis_cloudflare_schema.py
- test_event_alert_delivery_quality_regressions.py
- test_llm_outage_detectors.py
- llm/config.py
- CCWBot Growth Strategy: 0 -> 1 Premium
- system_status.py
- price_service.py
- resolve_alert_recipient_outcomes
- cli.py
- json
- test_event_analysis_health.py
- properties
- RedactionReport
- test_admin_cleanup.py
- users.py
- Base
- 0001_initial_schema.py
- validate_event_significance_output
- CCWBot
- decimal
- event_analysis.py
- 0024_gram_symbol.py
- test_event_alert_historical_diagnostics.py
- test_agent_workflow_contract.py
- collections_abc
- AIProviderRateLimitError
- canonicalize_event_key
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- datetime
- _fixture
- new_llm_operation_id
- test_news_intelligence_schema.py
- event_chart.py
- hashlib
- test_heartbeat_postgres.py
- button_router
- Context Audit Report
- database.py
- manifest.json
- Development
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- openai_budget.py
- BundleWriter
- test_event_alert_rich_chart_ux.py
- Ops-Agent Service
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- asyncio
- telegram_error
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
- llm/env.py
- bot/config.py
- architecture-guardian.md
- code-quality.md
- db-migration-guardian.md
- devops-release.md
- market-pipeline.md
- OpenAIProvider
- product-policy.md
- security-review.md
- telegram-stars-payments.md
- /graphify
- AGENTS.md
- agents/README.md
- codex_task_prompt_template.md
- Project Context
- db/premium.py
- get_or_create_user
- event_identity.py
- ai_agent_groq.py
- test_event_alert_composition_investigation.py
- test_market_heartbeat.py
- _deliver_market_event_alert
- test_llm_config_budgets.py
- ChatGPT / Bridge / Codex Workflow
- news_service.py
- collectors/__init__.py
- ops_agent/__init__.py
- validate_market_heartbeat_output
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
- CCW-41 exploratory Reviewer-C agreement/disagreement
- user.py
- test_heartbeat_does_not_query_previous_event
- generate_market_heartbeats
- test_report_llm_exhaustion_recovery.py
- RichDeliveryUncertain
- TransientSessions
- telegram
- test_ccw9_ccw10.py
- CCW-43 — Evidence-based Event Analysis prompt redesign
- LLMJsonResult
- alembic/env.py
- test_rich_403_preserves_safe_blocked_classification_without_raw_errors
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- 0008_database_comments.py
- test_growth_analytics_migration.py
- test_transport_reuses_file_id_and_handles_valid_response
- 0027_market_heartbeat_defaults.py
- P
- CCWBot Operational Report — Unverified (No Production Bundle)
- normalize_symbol
- 0025_llm_operation_correlation.py
- .__init__
- FakeResponse
- test_price_handlers.py
- 0004_multicoin_delivery_idempotency.py
- CCW-25 — Self-hosted LLM owner decision
- _build_event_analysis_input
- NoopAsyncClient
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- 0005_telegram_stars_payments.py
- test_price_service.py
- 0006_payment_recurring_metadata.py
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- SessionContext
- Repository-backed Graphify
- 0031_onboarding_customize_event.py
- 0007_unique_telegram_user_id.py
- automatic_price_check
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- 0009_error_file_logging_toggle.py
- 0026_growth_analytics.py
- 0028_premium_trials.py
- build_review.py
- _SessionContext
- CCW-25 research evidence
- operator_prompt.md
- test_final_section_sql_handles_newlines_fanout_and_missing_sections
- .__init__
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- README_RU.md
- 0003_premium_watchlist_foundation.py

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
- `Read-only local check` --references--> `load_frozen()`  [INFERRED]
  benchmarks/ccw15-v1/README.md → scripts/event_alert_benchmark.py
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py
- `Event Alert Regression Evidence` --references--> `unknown()`  [INFERRED]
  docs/ops_agent_service.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (229 total, 35 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.14
Nodes (47): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), alert_analysis_result(), event_analysis_result(), factual_market_input() (+39 more)

### Community 1 - "replay_event_significance.py"
Cohesion: 0.09
Nodes (31): _groq_json_mode_enabled(), scripts, classify_replay_error(), effort_budget(), groq_significance_response_format(), live_report(), load_cases(), NonObjectSignificanceError (+23 more)

### Community 2 - "test_logical_llm_health.py"
Cohesion: 0.11
Nodes (33): Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider…, Compute 24h terminal outcomes. Raises on DB errors; never returns fake OK. (+25 more)

### Community 3 - "onboarding.py"
Cohesion: 0.10
Nodes (53): ProductEvent, UserCoinSubscription, build_onboarding_customize_keyboard(), Premium-only onboarding selector. BTC stays as the free default during…, _as_aware_utc(), build_instant_brief(), build_onboarding_message(), build_returning_user_message() (+45 more)

### Community 4 - "Period"
Cohesion: 0.05
Nodes (62): alembic_migration, alembic_operations, ops_agent_collectors, run_detectors(), Period, sqlite3, _AlertEvidenceFakeEngine, _assert_malformed_numeric_context_is_safe() (+54 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.09
Nodes (69): _backoff_schedule(), breaker_snapshot(), _BreakerState, is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics., True when this triple is open and must be skipped in favour of the next… (+61 more)

### Community 6 - "telemetry.py"
Cohesion: 0.05
Nodes (70): AsyncOpenAI, _json_response_validator(), _validate(), OpenAICompatibleProvider, Provider interface and the shared OpenAI-compatible provider implementation.…, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers. (+62 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.08
Nodes (48): MarketReportDecision, _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report() (+40 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.10
Nodes (53): Payment, build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date(), _get_payment_attr(), _is_private_update() (+45 more)

### Community 9 - "common.py"
Cohesion: 0.09
Nodes (34): _format_admin_alert_settings(), _callback_command_update(), decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,… (+26 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.18
Nodes (46): LlmUsageLog, PriceState, build_admin_llm_diagnostics_text(), Return admin-safe provider-attempt diagnostics separate from feature health., build_session_factory(), _event_analysis(), _final_failed_alert(), _now() (+38 more)

### Community 12 - "test_openai_budget.py"
Cohesion: 0.16
Nodes (27): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., OpenAIBudget, OpenAIBudgetExhausted, RuntimeError, OpenAI was skipped before HTTP because safe authorization was unavailable., budget_db(), asyncio (+19 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.05
Nodes (70): bot_alerting, alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.… (+62 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.15
Nodes (22): BudgetLease, _Charge, GroqBudget, GroqBudgetExhausted, datetime, Conservative zero-cost Groq admission control, shared across all call types. A…, Test-only reset; production restarts reload persisted usage., asyncio (+14 more)

### Community 15 - "test_watchlist_ux.py"
Cohesion: 0.07
Nodes (44): build_subscribe_message(), build_watchlist_message(), _subscription_by_symbol(), AsyncFalse, AsyncNoop, AsyncTrue, build_session(), CallbackQuery (+36 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (65): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+57 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.12
Nodes (46): ask_event_analysis_raw(), AISchemaValidationError, Raised when validated JSON does not match the expected schema. ``raw_content``…, _configure(), ContentProvider, _empty_report_news_context(), _grounded_alert(), _grounding_market() (+38 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (79): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+71 more)

### Community 19 - "event_alert_benchmark.py"
Cohesion: 0.09
Nodes (46): random, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, Private CCW16 summary: downloads only restricted experiment ledger, never keys…, CCW-29 fresh private holdout: collect real POST-200 market cases via…, choose(), Freeze fresh 200 real CCWBot market cases, excluding both earlier sets;…, hashfile(), main() (+38 more)

### Community 20 - "log"
Cohesion: 0.07
Nodes (49): AbstractEventLoop, AppRunner, schedule_market_heartbeat_generation(), expire_due_premium_trials(), process_due_trial_expiries(), Application, DEFAULT_TYPE, Independent scheduling for durable Premium-trial lifecycle transitions. (+41 more)

### Community 21 - "User"
Cohesion: 0.21
Nodes (16): User, build_session_factory(), create_market_event(), create_user(), asyncio, test_backfill_marks_historical_blocked_users_and_is_idempotent(), test_bad_request_delivery_failure_is_not_retried(), test_blocked_telegram_error_disables_user_and_keeps_failed_alert() (+8 more)

### Community 22 - "runtime/state.py"
Cohesion: 0.15
Nodes (12): Runtime state and startup helpers., close_database(), initialize_database(), Any, Dispose database resources created during startup., SessionFactoryRef, _sync_package_database_engine(), asyncio (+4 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.16
Nodes (22): can_deliver_market_heartbeat_now(), pytest_asyncio, add_delivery(), asyncio, parametrize, test_delayed_success_uses_completion_not_reservation(), test_event_resets_timer_during_generation_market_fetch(), market() (+14 more)

### Community 24 - "test_bundle_and_cli.py"
Cohesion: 0.06
Nodes (38): ops_agent, _validate_bundle(), OpsAgentLimits, _collect_args(), MonkeyPatch, Namespace, Path, _stub_collectors() (+30 more)

### Community 25 - "event_text.py"
Cohesion: 0.10
Nodes (41): compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback(), _has_persistent_snapshot_direction(), _is_safe_llm_situation(), _is_safe_structured_market_interpretation() (+33 more)

### Community 26 - "test_seen_news_dedup.py"
Cohesion: 0.13
Nodes (32): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), get_event_ai_analysis(), get_or_create_market_event(), Decimal, Return the market event for event_instance_key, creating it when needed., Return an existing AI analysis for the event/input pair if present. (+24 more)

### Community 27 - "bot/reports.py"
Cohesion: 0.07
Nodes (50): Mark news items as seen in PostgreSQL after they were used by the bot., remember_news_context(), _build_daily_report_message(), _build_deterministic_report_decision(), _build_market_report_input(), _build_report_coin_payload(), _build_weekly_breadth(), _build_weekly_coin_context() (+42 more)

### Community 28 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 29 - "validate_market_report_output"
Cohesion: 0.16
Nodes (37): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+29 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "watchlist.py"
Cohesion: 0.11
Nodes (52): _as_aware_utc(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active(), is_user_trial_active() (+44 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.07
Nodes (72): audit(), positive_age_minutes(), ranking(), main(), _number(), _time(), _aggregate_markdown(), _cli() (+64 more)

### Community 33 - "detectors.py"
Cohesion: 0.13
Nodes (30): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+22 more)

### Community 34 - "admin.py"
Cohesion: 0.18
Nodes (40): build_acquisition_telegram_url(), Build a Telegram deep link only from a valid configured bot username and opaque…, acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_admin_llm_diagnostics_text(), _build_admin_system_status_text() (+32 more)

### Community 35 - "Observability Snippets"
Cohesion: 0.09
Nodes (26): Output, Rules you enforce, What you review, Admin System Status, Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis, Event Alert Exact Context Reuse (+18 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.12
Nodes (44): MarketReport, reports(), _build_report_telegram_message(), get_or_generate_report(), Only full persisted report inputs qualify; preserve test/minimal caches., One shared refresh on old content; never fan out LLM/RSS per recipient., _report_requires_content_upgrade(), send_daily_report_message() (+36 more)

### Community 37 - "classify_ai_error_reason"
Cohesion: 0.10
Nodes (33): AIInvalidJsonError, AllProvidersFailedError, LLMRateLimitBackoffActive, datetime, Exception, RuntimeError, Provider-agnostic LLM error types shared across the provider router. These were…, Raised when a provider/model is already in temporary rate-limit backoff. (+25 more)

### Community 38 - "logging"
Cohesion: 0.08
Nodes (47): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports(), _collect_secret_values() (+39 more)

### Community 39 - "LLMRouter"
Cohesion: 0.16
Nodes (52): LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider, _http_error(), _parse_json_validate() (+44 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.05
Nodes (71): EventAnalysisDecision, _event_input_hash(), _as_news_only_rejected_decision(), _build_event_alert_html_message(), _build_event_alert_payload(), _create_event_analysis_decision(), _decision_describes_market_event(), _decision_is_primarily_news_context() (+63 more)

### Community 42 - "provider_attempts"
Cohesion: 0.13
Nodes (16): _model_from_env(), provider_attempts(), Reject blank or retired identifiers from env and internal override paths., Resolve a model identifier, treating invalid overrides as unset.…, Validate a non-environment runtime override against retired model policy., Return the ordered concrete provider/model attempts for one logical LLM…, resolve_model_override(), _validated_model_identifier() (+8 more)

### Community 43 - "test_multicoin_alerts.py"
Cohesion: 0.13
Nodes (24): Return active market symbols independently of current recipient eligibility., resolve_symbols_to_check(), set_user_coin_subscription(), build_session_factory(), create_user(), asyncio, test_automatic_fallback_state_persists_decimal_prices(), test_automatic_price_check_analyzes_before_no_recipient_outcome() (+16 more)

### Community 44 - "select"
Cohesion: 0.08
Nodes (63): attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery(), get_last_sent_alert(), get_last_sent_alert_at(), get_last_sent_event_alert_at_for_event_key(), get_latest_event_analysis_attempt() (+55 more)

### Community 45 - "bot/news.py"
Cohesion: 0.11
Nodes (39): _collapse_whitespace(), make_news_key(), _normalize_news_link(), Normalize repeated spaces so keys stay stable across feed formatting., Return a stable URL string for news identity checks., Build a stable key for a news item. Links are preferred because RSS titles can…, _dedupe_report_news(), fetch_news_context() (+31 more)

### Community 46 - "_runner_private.py"
Cohesion: 0.28
Nodes (15): call_once(), classify(), fail(), main(), persist(), datetime, quota_allows(), Finite direct-provider CCW-16 canary runner; Python stdlib only. This script… (+7 more)

### Community 48 - "db/news.py"
Cohesion: 0.13
Nodes (27): SeenNews, cleanup_seen_news(), count_recent_news_intelligence_llm_calls(), get_cached_news_item_analysis(), get_cooling_failed_news_keys(), get_news_item_by_key(), get_recent_seen_news(), get_retryable_failed_news_items() (+19 more)

### Community 49 - "utc_now"
Cohesion: 0.13
Nodes (28): schedule_report_cache_generation(), Market report use-case entrypoints., datetime, Return timezone-aware UTC timestamp., utc_now(), generate_daily_report_cache_job(), generate_weekly_report_cache_job(), _is_report_provider_backoff_active() (+20 more)

### Community 50 - "router.py"
Cohesion: 0.10
Nodes (36): bot_services_llm, CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions…, get_provider(), GroqProvider, Groq provider (primary). OpenAI-compatible chat-completions API., get_provider() (+28 more)

### Community 51 - "_build_market_heartbeat_payload"
Cohesion: 0.07
Nodes (39): _event_alert_change_label(), _format_analysed_window_label(), compact_elapsed_since(), Escape all model/news wording; only safely link explicit HTTP(S) sources., _report_coin_icon_html(), _safe_rich_line(), _build_event_alert_rich_html(), _build_market_heartbeat_html_message() (+31 more)

### Community 52 - "test_event_alert_render_provider_chain.py"
Cohesion: 0.26
Nodes (19): call_render(), FakeProvider, good_render(), input_payload(), install(), patch_significance_and_storage(), ProviderError, asyncio (+11 more)

### Community 53 - "test_event_analysis_cloudflare_schema.py"
Cohesion: 0.18
Nodes (21): ask_event_significance_raw(), ask_news_intelligence_raw(), Return JSON mode and provider-specific schemas for verified model attempts., _structured_response_formats(), llm_operation_scope(), Make one operation identifier visible to every nested provider attempt., get_router(), Return the process-wide router singleton (lazily created). (+13 more)

### Community 54 - "test_event_alert_delivery_quality_regressions.py"
Cohesion: 0.17
Nodes (21): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, _event_alert_render_prompt_payload(), Return only a supported sign; no rounded or raw market numbers reach Render., _render_market_direction(), test_specific_next_observation_is_not_generic(), _decision(), _market() (+13 more)

### Community 55 - "test_llm_outage_detectors.py"
Cohesion: 0.19
Nodes (23): _detector(), _evidence(), parametrize, Detectors and evidence quality for an LLM-side Event Analysis outage. Covers…, Mimic the collector: newest bucket first, each bucket capped by remaining…, _row(), _simulate_row_cap(), test_a_failure_storm_no_longer_starves_delivered_analyses_of_the_row_cap() (+15 more)

### Community 56 - "llm/config.py"
Cohesion: 0.08
Nodes (32): api_key(), api_key_env(), base_url(), _format_chain(), global_provider_priority(), is_thinking_model(), openai_enabled(), _parse_priority_list() (+24 more)

### Community 57 - "CCWBot Growth Strategy: 0 -> 1 Premium"
Cohesion: 0.15
Nodes (12): Acquisition limitation, CCWBot Growth Strategy: 0 -> 1 Premium, Change, Current comparable cohort, Decision rule, Experiment 1 - Premium-only onboarding selector, Handoff prompt for a new chat, Primary metric (+4 more)

### Community 58 - "system_status.py"
Cohesion: 0.15
Nodes (35): _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), build_admin_system_status_text(), ComponentHealth, _delivery_failure_category(), _delivery_health() (+27 more)

### Community 59 - "price_service.py"
Cohesion: 0.11
Nodes (33): _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), _extract_sparkline_prices(), get_btc_market_data(), get_btc_price(), _get_cached_price(), get_report_market_data_batch() (+25 more)

### Community 60 - "resolve_alert_recipient_outcomes"
Cohesion: 0.12
Nodes (22): _decimal_numeric_context_value(), _enabled_subscription_by_symbol(), get_alert_recipients(), _get_due_market_heartbeat_recipients(), _heartbeat_numeric_context(), Decimal, Resolve eligible recipients once for one market event., Resolve recipients and preserve queryable reasons for filtered users. (+14 more)

### Community 61 - "cli.py"
Cohesion: 0.08
Nodes (57): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+49 more)

### Community 62 - "json"
Cohesion: 0.04
Nodes (41): argparse, collections, html, importlib_util, json, math, pathlib, re (+33 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.05
Nodes (52): aiohttp, _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any, datetime (+44 more)

### Community 64 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 65 - "RedactionReport"
Cohesion: 0.07
Nodes (56): dataclasses, httpx, collect_health(), Any, collect_local_state(), Any, collect_logs(), _empty_counts() (+48 more)

### Community 66 - "test_admin_cleanup.py"
Cohesion: 0.13
Nodes (17): bot_handlers, AsyncFalse, AsyncTrue, _callback_update(), _callback_values(), FakeMessage, FakeQuery, asyncio (+9 more)

### Community 67 - "users.py"
Cohesion: 0.17
Nodes (18): backfill_blocked_users_from_alerts(), get_active_users_with_chat_ids(), get_user_by_telegram_chat_id(), get_user_role(), is_telegram_chat_delivery_enabled(), mark_user_bot_blocked(), AsyncSession, datetime (+10 more)

### Community 68 - "Base"
Cohesion: 0.15
Nodes (21): alembic_script, AppSettings, Base, Base class for all SQLAlchemy models., UserSettings, _get_app_settings_row(), get_or_create_app_settings(), get_or_create_user_settings() (+13 more)

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

### Community 73 - "event_analysis.py"
Cohesion: 0.11
Nodes (44): CanonicalEventKey, _claim_clause(), _claimed_percent(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal(), _decimal_market_value(), _direction_for_claim() (+36 more)

### Community 74 - "0024_gram_symbol.py"
Cohesion: 0.33
Nodes (13): _coerce_related_symbols(), _column_names(), downgrade(), _has_table_and_symbol(), _has_table_columns(), _merge_price_state(), _merge_user_coin_subscriptions(), _merge_user_symbol_alert_state() (+5 more)

### Community 75 - "test_event_alert_historical_diagnostics.py"
Cohesion: 0.08
Nodes (34): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Ground-truth evidence and limitations, Read-only local check, Versioned artifacts, build_event_significance_prompt(), _event_significance_prompt_payload(), Return the small always-on model view used only for significance. (+26 more)

### Community 76 - "test_agent_workflow_contract.py"
Cohesion: 0.19
Nodes (10): _adapter_path(), _agent_names(), _agent_paths(), _load_toml(), Path, test_agent_definitions_have_matching_claude_adapters(), test_agent_definitions_have_required_schema(), test_agent_routing_references_existing_agents() (+2 more)

### Community 77 - "collections_abc"
Cohesion: 0.09
Nodes (4): downgrade(), _is_sqlite(), upgrade(), collections_abc

### Community 78 - "AIProviderRateLimitError"
Cohesion: 0.14
Nodes (22): ABC, BaseProvider, ProviderResult, Normalized successful chat-completion result returned by every provider., Common interface for all LLM providers., True when this provider has all configuration required for an attempt., Run one chat completion and return a :class:`ProviderResult` on success.…, AIProviderRateLimitError (+14 more)

### Community 79 - "canonicalize_event_key"
Cohesion: 0.09
Nodes (31): bot, canonicalize_event_key(), _collapse_event_key(), _fallback_event_key(), _is_random_event_key(), _normalize_event_key_text(), Return a stable backend key for semantic event identity., _semantic_event_key() (+23 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.25
Nodes (37): LlmOperationOutcome, NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap(), build_session(), FakeNewsLlm (+29 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "datetime"
Cohesion: 0.06
Nodes (49): concurrent_futures, datetime, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., Audit only aggregated benchmark budget and next-call feasibility (no inference)., atom() (+41 more)

### Community 83 - "_fixture"
Cohesion: 0.06
Nodes (42): _event_analysis_prompt_payload(), Return the compact semantic model view without runtime or repeated static…, Clear all breaker state (tests and controlled restarts)., reset_breakers(), Clear in-memory provider/model backoffs for tests and controlled restarts., reset_llm_rate_limit_backoffs(), _real_socket, socket (+34 more)

### Community 84 - "new_llm_operation_id"
Cohesion: 0.13
Nodes (19): AsyncSession, Update a usage row when downstream JSON schema validation fails., Save one LLM usage telemetry row., save_llm_usage_log(), update_llm_usage_log_status(), get_latest_market_report(), AsyncSession, datetime (+11 more)

### Community 85 - "test_news_intelligence_schema.py"
Cohesion: 0.23
Nodes (17): _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), asyncio, parametrize, Offline News Intelligence symbol-contract regression tests; no provider calls., RecordedProvider (+9 more)

### Community 86 - "event_chart.py"
Cohesion: 0.17
Nodes (16): ChartResult, _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw, Deterministic PNG chart from persisted, timestamped price observations only., Auditable reference value and its actual, not nominal, UTC timestamp. (+8 more)

### Community 87 - "hashlib"
Cohesion: 0.04
Nodes (37): copy, hashlib, html_parser, io, Change only the CCW-16 experiment user cron cadence, preserving all other jobs., Read-only provider credential authentication probe on isolated Hetzner…, Stage and execute a finite, blind, genuine new-event holdout replay. No…, Replace Groq holdout runner with exact Retry-After compliant resumption,… (+29 more)

### Community 88 - "test_heartbeat_postgres.py"
Cohesion: 0.22
Nodes (12): automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, postgres_url(), asyncio, Real PostgreSQL locking checks; the SQLite process mutex cannot prove these…, test_postgres_lock_serializes_separate_workers_and_releases_on_cancellation() (+4 more)

### Community 89 - "button_router"
Cohesion: 0.10
Nodes (47): _automatic_market_check_job_name(), schedule_automatic_market_check(), send_admin_callback_response(), _standalone_settings_origin(), button_router(), DEFAULT_TYPE, Update, Central callback-query router for Telegram inline keyboards. (+39 more)

### Community 90 - "Context Audit Report"
Cohesion: 0.09
Nodes (14): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+6 more)

### Community 91 - "database.py"
Cohesion: 0.06
Nodes (69): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+61 more)

### Community 92 - "manifest.json"
Cohesion: 0.06
Nodes (35): batch_size, batches, path, sha256, case_count, cases, dataset_sha256, operator_prompt_sha256 (+27 more)

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
Cohesion: 0.13
Nodes (23): event_analysis_operation_budget_seconds(), Choose a per-attempt HTTP timeout; explicit caller overrides remain…, Bound the complete Event Analysis provider chain, not each provider…, Return the fully resolved per-call-type LLM configuration. Model identifiers,…, request_timeout_seconds_for(), resolved_configuration(), _cost(), monthly_budget_usd() (+15 more)

### Community 97 - "BundleWriter"
Cohesion: 0.11
Nodes (16): BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk., sha256_file() (+8 more)

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

### Community 105 - "asyncio"
Cohesion: 0.17
Nodes (10): asyncio, ask_market_report_raw(), _set_groq_client(), test_event_analysis_prompt_makes_llm_the_market_significance_decider(), test_event_analysis_raw_uses_strict_groq_schema_and_returns_provider_attribution(), test_event_analysis_unknown_groq_model_keeps_json_object_mode(), test_market_heartbeat_raw_uses_strict_groq_schema(), test_market_report_raw_uses_strict_groq_schema() (+2 more)

### Community 106 - "telegram_error"
Cohesion: 0.31
Nodes (8): handle_application_error(), Global python-telegram-bot error handler. Log-only: never sends anything to…, telegram_error, asyncio, parametrize, Global PTB error handler: concise WARNING for transient network errors, ERROR…, test_non_network_error_logs_error_with_traceback(), test_transient_network_error_logs_one_concise_warning()

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.33
Nodes (17): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+9 more)

### Community 108 - "test_news_ingestion.py"
Cohesion: 0.14
Nodes (10): _entry(), _feed(), asyncio, datetime, Regression tests for the independent, bounded RSS ingestion path., test_report_and_hourly_ingestion_share_serial_llm_budget_gate(), test_rss_merges_sources_by_publication_time_before_limit(), test_rss_source_failure_is_isolated_and_safely_counted() (+2 more)

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
Cohesion: 0.25
Nodes (14): build_event_alert_render_prompt(), test_event_alert_render_schema_only_contains_model_generated_fields(), _payload(), asyncio, parametrize, Regression contracts for production Event Alert Render rejection categories.…, test_flat_news_led_input_cannot_be_recovered_as_market_alert(), test_invalid_provider_chain_exhaustion_uses_validated_evidence_fallback() (+6 more)

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

### Community 128 - "llm/env.py"
Cohesion: 0.13
Nodes (19): _get_int_env(), _failure_threshold(), Substrings that mark a model identifier as reasoning-capable (overridable via…, reasoning_model_markers(), get_choice_env(), get_int_env(), _is_secret_name(), _looks_like_secret_value() (+11 more)

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

### Community 135 - "OpenAIProvider"
Cohesion: 0.10
Nodes (19): OpenAIProvider, _CapturingClient, _CapturingCompletions, _mock_openai_admission(), _provider_payload(), asyncio, Captures the kwargs the router passes, without making any provider call., _RecordingProvider (+11 more)

### Community 136 - "product-policy.md"
Cohesion: 0.50
Nodes (3): Output, Product rules you enforce, What you review

### Community 137 - "security-review.md"
Cohesion: 0.50
Nodes (3): Hard rules you enforce, Output, What you review

### Community 138 - "telegram-stars-payments.md"
Cohesion: 0.50
Nodes (3): Output, Rules you enforce, What you review

### Community 139 - "/graphify"
Cohesion: 0.09
Nodes (17): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+9 more)

### Community 143 - "Project Context"
Cohesion: 0.29
Nodes (6): Current product behavior, Event Alerts, Manual command UX and price lookups, Market Heartbeat, Permanent guardrails, Project Context

### Community 144 - "db/premium.py"
Cohesion: 0.18
Nodes (37): UserPremiumSubscription, UserPremiumTrial, activate_premium_from_telegram_stars_payment(), _activate_premium_from_telegram_stars_payment_locked(), ensure_default_coin_subscriptions(), expire_due_premium_trials(), get_payment_by_provider_id(), get_user_premium_subscription() (+29 more)

### Community 145 - "get_or_create_user"
Cohesion: 0.44
Nodes (12): get_or_create_user(), Create or update profile fields for the current Telegram interaction., build_session(), asyncio, test_get_or_create_user_allows_missing_username(), test_get_or_create_user_demotes_existing_admin_removed_from_allowlist(), test_get_or_create_user_keeps_non_admin_role_with_allowlist(), test_get_or_create_user_marks_second_admin_id_from_allowlist() (+4 more)

### Community 146 - "event_identity.py"
Cohesion: 0.07
Nodes (40): AnalysedWindowReference, _build_exact_event_context_fingerprint(), _canonical_decimal_string(), _canonical_event_analysis_context(), _event_analysis_datetime(), _event_analysis_news_age_hours(), _event_analysis_news_summary(), _json_dumps() (+32 more)

### Community 147 - "ai_agent_groq.py"
Cohesion: 0.06
Nodes (38): asyncpg, bot_services, ask_market_heartbeat_raw(), build_event_analysis_prompt(), build_market_heartbeat_prompt(), build_market_report_prompt(), _event_analysis_percent(), _parse_json() (+30 more)

### Community 148 - "test_event_alert_composition_investigation.py"
Cohesion: 0.20
Nodes (26): market_direction_claims_supported(), Check explicit period directions and the direction implied by relationships., market(), parametrize, Synthetic regressions for the October alert-composition investigation., test_alignment_fallback_names_direction_and_verified_size_relationship(), test_alignment_without_monotonic_snapshots_survives_compaction(), test_consistent_with_describes_alignment_not_snapshot_persistence() (+18 more)

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.09
Nodes (40): _deliver_market_heartbeat(), _select_related_news_context(), MarketHeartbeat, test_cache_expiring_before_lock_acquisition_is_not_sent(), test_concurrent_checks_send_one_heartbeat_and_reset_timer(), test_event_success_while_heartbeat_waits_cancels_stale_preflight(), due(), test_failed_telegram_send_does_not_reset_clock() (+32 more)

### Community 150 - "_deliver_market_event_alert"
Cohesion: 0.09
Nodes (40): AlertRecipient, _automatic_delivery_lock(), _count_suppression(), _deliver_market_event_alert(), _delivery_error_class_name(), _delivery_retry_delay_seconds(), _disable_recipient_if_bot_blocked(), EventRecipientFilterResult (+32 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.07
Nodes (56): effective_max_tokens_for(), is_reasoning_model(), log_resolved_configuration(), max_tokens_for(), model_for(), Resolve the model for a (provider, call_type) pair from env, with defaults., Resolve the completion-token budget for a call type. The current ``LLM_*`` name…, Return the completion budget for one concrete provider attempt. The public… (+48 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "news_service.py"
Cohesion: 0.22
Nodes (11): headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Low-cost, word-boundary-aware prefilter; not an alert decision., Bound provider latency/response size; parse only successfully fetched bytes., _read_rss_feed() (+3 more)

### Community 156 - "validate_market_heartbeat_output"
Cohesion: 0.18
Nodes (19): MarketHeartbeatDecision, MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body(), sanitize_heartbeat_possible_action() (+11 more)

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
Cohesion: 0.09
Nodes (34): Persist one sanitized terminal outcome for a logical LLM operation., save_llm_operation_outcome(), _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text() (+26 more)

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.15
Nodes (20): ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment(), _migration_config() (+12 more)

### Community 169 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 170 - "user.py"
Cohesion: 0.42
Nodes (8): DEFAULT_TYPE, Update, General user command handlers., Best-effort product measurement that never exposes deep-link data to users., _record_start_analytics(), start(), _start_payload(), user_id()

### Community 171 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 172 - "generate_market_heartbeats"
Cohesion: 0.28
Nodes (8): _build_market_heartbeat_id(), cleanup_seen_news_job(), generate_market_heartbeats(), DEFAULT_TYPE, Compatibility wrapper for older imports; schedules the market-wide check., schedule_automatic_btc_check(), schedule_seen_news_cleanup(), Alert and heartbeat use-case entrypoints.

### Community 173 - "test_report_llm_exhaustion_recovery.py"
Cohesion: 0.43
Nodes (6): asyncio, parametrize, Report availability must survive exhausted LLM providers, but not unrelated…, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload()

### Community 174 - "RichDeliveryUncertain"
Cohesion: 0.28
Nodes (8): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert()

### Community 176 - "telegram"
Cohesion: 0.19
Nodes (12): daily_report(), DEFAULT_TYPE, Update, Market report command handlers., weekly_report(), send_weekly_report_message(), Groq free-tier admission control (Event Analysis), LLM Usage Reporting (+4 more)

### Community 177 - "test_ccw9_ccw10.py"
Cohesion: 0.14
Nodes (18): Intercept only messages sent in the scope of a manual command/callback., _tracking(), TransientBot, with_close_button(), ExtBot, fetch(), asyncio, parametrize (+10 more)

### Community 178 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 179 - "LLMJsonResult"
Cohesion: 0.25
Nodes (5): LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., test_backward_compatible_public_api(), CorrelatedFallbackNewsLlm, tuple

### Community 180 - "alembic/env.py"
Cohesion: 0.39
Nodes (7): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), Connection, logging_config

### Community 181 - "test_rich_403_preserves_safe_blocked_classification_without_raw_errors"
Cohesion: 0.29
Nodes (3): parametrize, test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post()

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.10
Nodes (16): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps, CCWBot — blind owner disagreement-only replay, Limitations and next actions, Operational recommendation (+8 more)

### Community 183 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 184 - "test_growth_analytics_migration.py"
Cohesion: 0.47
Nodes (5): alembic_config, _alembic_config(), Config, test_growth_analytics_upgrade_backfills_existing_users(), test_premium_trials_upgrade_preserves_existing_premium_and_payment_rows()

### Community 186 - "0027_market_heartbeat_defaults.py"
Cohesion: 0.70
Nodes (4): downgrade(), _has_alert_frequency_column(), _set_default(), upgrade()

### Community 188 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 189 - "normalize_symbol"
Cohesion: 0.05
Nodes (77): _build_event_instance_key(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _event_instance_bucket(), _candidate_news_relevance_label(), classify_news_relevance(), _coin_name(), filter_news_for_symbol() (+69 more)

### Community 190 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 192 - "FakeResponse"
Cohesion: 0.13
Nodes (7): Response, FakeAsyncClient, FakeClient, FakeResponse, test_get_coin_price_429_triggers_retry(), __init__(), test_get_with_retry_sends_demo_api_key()

### Community 193 - "test_price_handlers.py"
Cohesion: 0.32
Nodes (14): CoinGeckoRateLimitError, Exception, Raised when CoinGecko returns HTTP 429., _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users(), test_price_maps_provider_errors_to_safe_user_messages() (+6 more)

### Community 194 - "0004_multicoin_delivery_idempotency.py"
Cohesion: 0.83
Nodes (3): downgrade(), _unique_constraint_names(), upgrade()

### Community 195 - "CCW-25 — Self-hosted LLM owner decision"
Cohesion: 0.25
Nodes (7): Actual local screen, CCW-25 — Self-hosted LLM owner decision, Low-risk next decision, Monthly EUR / DKK comparison, Specific candidates and serving stack, Volume sensitivity and break-even, What is measured

### Community 196 - "_build_event_analysis_input"
Cohesion: 0.10
Nodes (36): _calculate_price_change(), get_analysed_window_minutes(), _build_event_analysis_input(), _build_market_heartbeat_input(), _compact_event_snapshot(), _compact_event_snapshots(), _historical_event_analysis_moves(), _is_fresh_heartbeat() (+28 more)

### Community 198 - "CCW-41 owner-reviewed significance reference v1"
Cohesion: 0.29
Nodes (6): Asset-specific labels, CCW-41 owner-reviewed significance reference v1, Historical bot against reference (selected benchmark only), How disputed labels changed, Using this reference for future model prompts, Warrant distributions

### Community 199 - "_working_code_backup.py"
Cohesion: 0.16
Nodes (30): event_alert_benchmark, _aggregate_markdown(), _cli(), compare_reviewers(), _field_exists(), _group_metrics(), import_results(), _label_counts() (+22 more)

### Community 201 - "0005_telegram_stars_payments.py"
Cohesion: 0.83
Nodes (3): downgrade(), _table_names(), upgrade()

### Community 202 - "test_price_service.py"
Cohesion: 0.15
Nodes (20): _extract_ton_coin_data_from_simple_price(), get_coin_market_data_batch(), get_coin_price(), Get current coin price and 24h change from CoinGecko. Unsupported symbols raise…, Fetch market data for supported symbols with one CoinGecko request. Missing…, Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., clean_price_caches(), clear_price_caches() (+12 more)

### Community 203 - "0006_payment_recurring_metadata.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 204 - "CCW-29 Handoff — New CCW-43 Event Analysis Prompts"
Cohesion: 0.29
Nodes (6): Artifacts and cryptographic identity, CCW-29 Handoff — New CCW-43 Event Analysis Prompts, Current status, Exact prompt construction, Proposed bounded CCW-29 execution (requires separate owner approval), Provider-specific comparison settings to freeze

### Community 205 - "SessionContext"
Cohesion: 0.40
Nodes (3): asyncio, SessionContext, test_trial_expiry_job_contains_lifecycle_failures()

### Community 206 - "Repository-backed Graphify"
Cohesion: 0.33
Nodes (5): One-time migration from existing Windows graph, Repository-backed Graphify, Retention, Shared state in dev, Updates after migration

### Community 208 - "0031_onboarding_customize_event.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_event_name_check(), upgrade()

### Community 209 - "0007_unique_telegram_user_id.py"
Cohesion: 0.83
Nodes (3): _constraint_names(), downgrade(), upgrade()

### Community 210 - "automatic_price_check"
Cohesion: 0.08
Nodes (34): _analysed_window_minutes_from_payload(), _build_event_analysis_id(), _event_instance_key_for_decision(), _numeric_context_payload(), _raw_event_key_from_payload(), _semantic_family_from_payload(), _stable_float(), _stable_related_news_ids() (+26 more)

### Community 211 - "CCW-25 — Owner decision"
Cohesion: 0.33
Nodes (5): CCW-25 — Owner decision, Economics and next step, Evidence behind the decision, Models actually screened, What each option costs

### Community 212 - "CCWBot — итоги оценки alerts (16 октября 2026)"
Cohesion: 0.33
Nodes (5): CCWBot — итоги оценки alerts (16 октября 2026), Значимость, Полезность текста, Следующая инженерная работа, Файлы

### Community 213 - "0009_error_file_logging_toggle.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 214 - "0026_growth_analytics.py"
Cohesion: 0.90
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 215 - "0028_premium_trials.py"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 217 - "build_review.py"
Cohesion: 0.12
Nodes (23): csv, candidate(), canon(), context(), csvwrite(), main(), Private read-only CCWBot market benchmark and independent review CSV exporter., run_psql() (+15 more)

### Community 219 - "CCW-25 research evidence"
Cohesion: 0.40
Nodes (4): Billing assumptions, CCW-25 research evidence, Interpretation limits, Reproduce

### Community 220 - "operator_prompt.md"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C operator prompt, CCW-41 Reviewer C significance rubric v1, Frozen output schema, Frozen rubric

### Community 221 - "test_final_section_sql_handles_newlines_fanout_and_missing_sections"
Cohesion: 0.67
Nodes (3): asyncio, parametrize, test_final_section_sql_handles_newlines_fanout_and_missing_sections()

### Community 231 - "0003_premium_watchlist_foundation.py"
Cohesion: 0.80
Nodes (4): _column_names(), downgrade(), _table_names(), upgrade()

## Knowledge Gaps
- **401 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+396 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1603 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `select()` connect `select` to `test_logical_llm_health.py`, `onboarding.py`, `test_telegram_stars_payments.py`, `test_system_status.py`, `test_openai_budget.py`, `test_groq_budget.py`, `test_watchlist_ux.py`, `db/premium.py`, `get_or_create_user`, `User`, `test_market_heartbeat.py`, `test_seen_news_dedup.py`, `news_intelligence_service.py`, `test_report_cooldowns.py`, `test_event_alert_pipeline.py`, `test_multicoin_alerts.py`, `bot/news.py`, `db/news.py`, `router.py`, `system_status.py`, `resolve_alert_recipient_outcomes`, `users.py`, `_build_event_analysis_input`, `Base`, `test_news_intelligence_service.py`, `new_llm_operation_id`, `test_news_intelligence_schema.py`, `build_review.py`, `database.py`, `openai_budget.py`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `unknown()` connect `Observability Snippets` to `Ops-Agent Service`, `RichDeliveryUncertain`, `CCWBot Ops-Agent Report Analysis`, `_deliver_market_event_alert`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `test_event_alert_rich_chart_ux.py`, `Observability Snippets`, `test_report_cooldowns.py`, `test_rich_market_report_delivery.py`, `bot/alerts.py`, `_deliver_market_event_alert`, `bot/reports.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 168 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 168 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 74 inferred relationships involving `LLMRouter` (e.g. with `AIInvalidJsonError` and `AIProviderRateLimitError`) actually correct?**
  _`LLMRouter` has 74 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _401 weakly-connected nodes found - possible documentation gaps or missing edges._