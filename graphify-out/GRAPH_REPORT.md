# Graph Report - CCWBot  (2026-10-26)

## Corpus Check
- 636 files · ~1,133,301 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 33 file(s) not represented in the graph (top: .toml 12, (none) 8, .csv 6)

## Summary
- 5559 nodes · 16369 edges · 241 communities (204 shown, 37 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1230 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e159b0aa`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- replay_event_significance.py
- LlmUsageLog
- test_onboarding.py
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
- bootstrap.py
- test_news_intelligence_schema.py
- runtime/state.py
- test_heartbeat_silence.py
- test_bundle_and_cli.py
- event_text.py
- test_seen_news_dedup.py
- bot/reports.py
- _StructuredRecordBuffer
- validate_market_report_output
- properties
- types
- ccw41_reviewer_c_audit.py
- detectors.py
- handlers/__init__.py
- Observability Snippets
- test_report_cooldowns.py
- classify_ai_error_reason
- logging
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- provider_attempts
- automatic_price_check
- db/alerts.py
- bot/news.py
- get_or_create_user
- ccw15_prompt_pack.py
- make_news_key
- refresh_report_cache_scheduled
- test_llm_rate_limit_backoff.py
- coin_icons.py
- test_event_alert_render_provider_chain.py
- test_event_analysis_cloudflare_schema.py
- test_event_alert_delivery_quality_regressions.py
- test_llm_outage_detectors.py
- llm/config.py
- CCWBot Growth Strategy: 0 -> 1 Premium
- system_status.py
- price_service.py
- bot/health.py
- cli.py
- json
- test_event_analysis_health.py
- properties
- RedactionReport
- /graphify
- database.py
- test_report_content_rich_and_llm_summary.py
- 0001_initial_schema.py
- validate_event_significance_output
- CCWBot
- decimal
- event_analysis.py
- 0024_gram_symbol.py
- AIInvalidJsonError
- test_agent_workflow_contract.py
- admin.py
- ProviderResult
- canonicalize_event_key
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- datetime
- _fixture
- _event_market_decision_detail
- bot/config.py
- event_chart.py
- ai_agent_groq.py
- breaker.py
- test_admin_cleanup.py
- Context Audit Report
- test_product_analytics.py
- manifest.json
- Development
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- openai_budget.py
- BundleWriter
- display_symbol
- Ops-Agent Service
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- test_ai_agent_groq.py
- graphify reference: extra exports and benchmark
- test_event_alert_chart_markers.py
- test_news_ingestion.py
- Event Alert logic
- README.md
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
- _create_event_analysis_decision
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
- test_alert_recipients.py
- test_permissions.py
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
- watchlist.py
- event_identity.py
- os
- test_event_alert_composition_investigation.py
- test_market_heartbeat.py
- User
- test_llm_config_budgets.py
- ChatGPT / Bridge / Codex Workflow
- test_event_alert_rich_chart_ux.py
- collectors/__init__.py
- ops_agent/__init__.py
- validate_market_heartbeat_output
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- db.py
- graphify reference: GitHub clone and cross-repo merge
- build_llm_messages
- pkgutil
- news_intelligence_service.py
- reviewer-c-rubric.md
- 0008_database_comments.py
- extraction-spec.md
- test_alembic_migrations.py
- CCW-41 exploratory Reviewer-C agreement/disagreement
- LLMJsonResult
- conftest.py
- _send_alert_to_recipient_once
- test_exhausted_provider_chain_uses_verified_data_fallback
- collections_abc
- TransientSessions
- handlers/reports.py
- test_ccw9_ccw10.py
- CCW-43 — Evidence-based Event Analysis prompt redesign
- telegram_error
- resolve_period
- log
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- test_heartbeat_does_not_query_previous_event
- 0004_multicoin_delivery_idempotency.py
- RichDeliveryUncertain
- test_report_all_providers_schema_invalid_uses_deterministic_fallback
- P
- CCWBot Operational Report — Unverified (No Production Bundle)
- normalize_symbol
- 0025_llm_operation_correlation.py
- .__init__
- FakeResponse
- test_price_handlers.py
- LlmOperationOutcome
- CCW-25 — Self-hosted LLM owner decision
- _build_event_analysis_input
- NoopAsyncClient
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- test_chart_prepared_once_and_shared_not_in_recipient_loop
- test_price_service.py
- Base
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- TransientBot
- Repository-backed Graphify
- 0031_onboarding_customize_event.py
- get_int_env
- pytest
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- test_transport_reuses_file_id_and_handles_valid_response
- 0026_growth_analytics.py
- 0027_market_heartbeat_defaults.py
- convert_human_reviews.py
- stage_economical_200.py
- CCW-25 research evidence
- operator_prompt.md
- 0005_telegram_stars_payments.py
- 0007_unique_telegram_user_id.py
- 0028_premium_trials.py
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- README_RU.md
- CCWBot — blind owner disagreement-only replay
- FakeAsyncClient
- 0003_premium_watchlist_foundation.py
- 0006_payment_recurring_metadata.py
- 0009_error_file_logging_toggle.py
- 0030_event_alert_policy_cleanup.py
- _build_market_heartbeat_rich_html
- sanitize_alert_message
- _pr2_commit_quality_runner_private.py
- ProviderHttpError
- _render_market_direction
- .__init__

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
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py
- `Event Alert Regression Evidence` --references--> `unknown()`  [INFERRED]
  docs/ops_agent_service.md → tests/test_event_alert_rich_chart_ux.py
- `Final Report Flow` --references--> `unknown()`  [INFERRED]
  docs/ops_agent_service.md → tests/test_event_alert_rich_chart_ux.py
- `Safety Rules` --references--> `unknown()`  [INFERRED]
  docs/ops_agent_service.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (241 total, 37 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.14
Nodes (47): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), alert_analysis_result(), event_analysis_result(), factual_market_input() (+39 more)

### Community 1 - "replay_event_significance.py"
Cohesion: 0.08
Nodes (52): _groq_json_mode_enabled(), scripts, blind_packet(), compare_recorded_run(), Compare recorded, already-validated model results without an API call. A…, reconcile(), report(), classify_replay_error() (+44 more)

### Community 2 - "LlmUsageLog"
Cohesion: 0.12
Nodes (32): LlmUsageLog, Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider… (+24 more)

### Community 3 - "test_onboarding.py"
Cohesion: 0.17
Nodes (36): ProductEvent, UserCoinSubscription, build_instant_brief(), handle_onboarding_callback(), _premium_intent_count(), Update, Render a brief from persisted PriceState only; never call LLMs or providers., Send a first-run BTC brief or a concise returning-user dashboard. (+28 more)

### Community 4 - "Period"
Cohesion: 0.05
Nodes (62): alembic_migration, alembic_operations, ops_agent_collectors, run_detectors(), Period, sqlite3, _AlertEvidenceFakeEngine, _assert_malformed_numeric_context_is_safe() (+54 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.17
Nodes (40): AllProvidersFailedError, Raised when every provider in the fallback chain has been exhausted.…, _call(), _configure(), _error(), FakeProvider, _groq_decommissioned_error(), _ok() (+32 more)

### Community 6 - "telemetry.py"
Cohesion: 0.06
Nodes (65): bot_services_llm, Provider interface and the shared OpenAI-compatible provider implementation.…, AIProviderRateLimitError, Provider-agnostic LLM error types shared across the provider router. These were…, Raised when a provider refuses a request because the account is rate limited., LLM provider fallback package. Groq stays the primary provider; disabled-by-…, current_llm_operation_id(), new_llm_operation_id() (+57 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.08
Nodes (46): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report(), market_report_change_chart() (+38 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.10
Nodes (54): Payment, build_premium_activation_keyboard(), build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date(), _get_payment_attr() (+46 more)

### Community 9 - "common.py"
Cohesion: 0.12
Nodes (26): decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, Best-effort deletion of a user's slash command in a private chat., _role_label() (+18 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.18
Nodes (47): PriceState, build_admin_llm_diagnostics_text(), build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health., build_session_factory(), _event_analysis(), _final_failed_alert() (+39 more)

### Community 12 - "test_openai_budget.py"
Cohesion: 0.16
Nodes (27): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., OpenAIBudget, OpenAIBudgetExhausted, RuntimeError, OpenAI was skipped before HTTP because safe authorization was unavailable., budget_db(), asyncio (+19 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.04
Nodes (78): bot_alerting, alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.… (+70 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.15
Nodes (22): BudgetLease, _Charge, GroqBudget, GroqBudgetExhausted, datetime, Conservative zero-cost Groq admission control, shared across all call types. A…, Test-only reset; production restarts reload persisted usage., asyncio (+14 more)

### Community 15 - "test_watchlist_ux.py"
Cohesion: 0.07
Nodes (44): ensure_default_coin_subscriptions(), Ensure one subscription row per supported symbol for a user., build_subscribe_message(), build_watchlist_render(), handle_watchlist_callback(), AsyncFalse, AsyncNoop, AsyncTrue (+36 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (65): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+57 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.25
Nodes (26): _configure(), ContentProvider, _grounded_alert(), _grounding_market(), _grounding_schema_check(), _install_router(), asyncio, parametrize (+18 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (81): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+73 more)

### Community 19 - "event_alert_benchmark.py"
Cohesion: 0.09
Nodes (25): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Read-only local check, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, Private CCW16 summary: downloads only restricted experiment ledger, never keys…, hashfile(), main(), metrics() (+17 more)

### Community 20 - "bootstrap.py"
Cohesion: 0.10
Nodes (31): AbstractEventLoop, AppRunner, asyncio, Application, register_bot_handlers(), start_health_server(), handle_health(), stop_health_server() (+23 more)

### Community 21 - "test_news_intelligence_schema.py"
Cohesion: 0.25
Nodes (17): _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), schema_check(), asyncio, parametrize, Offline News Intelligence symbol-contract regression tests; no provider calls. (+9 more)

### Community 22 - "runtime/state.py"
Cohesion: 0.15
Nodes (12): Runtime state and startup helpers., close_database(), initialize_database(), Any, Dispose database resources created during startup., SessionFactoryRef, _sync_package_database_engine(), asyncio (+4 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.13
Nodes (24): pytest_asyncio, add_delivery(), delivery_db(), asyncio, parametrize, test_concurrent_checks_send_one_heartbeat_and_reset_timer(), test_delayed_success_uses_completion_not_reservation(), test_event_resets_timer_during_generation_market_fetch() (+16 more)

### Community 24 - "test_bundle_and_cli.py"
Cohesion: 0.06
Nodes (47): ops_agent, _mark_report_success(), OpsAgentConfig, OpsAgentLimits, Path, load_state(), _collect_args(), MonkeyPatch (+39 more)

### Community 25 - "event_text.py"
Cohesion: 0.09
Nodes (42): compact_elapsed_since(), compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback(), _has_persistent_snapshot_direction(), _is_safe_llm_situation() (+34 more)

### Community 26 - "test_seen_news_dedup.py"
Cohesion: 0.17
Nodes (24): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), get_or_create_market_event(), Decimal, Return the market event for event_instance_key, creating it when needed., init_db(), Create SQLAlchemy async engine/session factory. Alembic migrations are… (+16 more)

### Community 27 - "bot/reports.py"
Cohesion: 0.07
Nodes (59): MarketReport, datetime, Return timezone-aware UTC timestamp., utc_now(), get_latest_market_report(), AsyncSession, datetime, Save one cached market report generation attempt. (+51 more)

### Community 28 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 29 - "validate_market_report_output"
Cohesion: 0.16
Nodes (37): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+29 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "types"
Cohesion: 0.21
Nodes (27): _as_aware_utc(), can_deliver_market_heartbeat_now(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active() (+19 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.07
Nodes (72): audit(), positive_age_minutes(), ranking(), main(), _number(), _time(), _aggregate_markdown(), _cli() (+64 more)

### Community 33 - "detectors.py"
Cohesion: 0.11
Nodes (31): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+23 more)

### Community 34 - "handlers/__init__.py"
Cohesion: 0.18
Nodes (37): acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_error_logging_status_text(), chat_id(), error_logging_off(), error_logging_on() (+29 more)

### Community 35 - "Observability Snippets"
Cohesion: 0.08
Nodes (27): consecutive_failures(), Output, Rules you enforce, What you review, Admin System Status, Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis (+19 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.17
Nodes (33): reports(), _build_report_telegram_message(), get_or_generate_report(), One shared refresh on old content; never fan out LLM/RSS per recipient., send_daily_report_message(), AsyncClock, build_session_factory(), _daily_message() (+25 more)

### Community 37 - "classify_ai_error_reason"
Cohesion: 0.15
Nodes (25): LLMRateLimitBackoffActive, Raised when a provider/model is already in temporary rate-limit backoff., GeminiProvider, get_provider(), Gemini provider (second fallback). Reached through Google's OpenAI-compatible…, Gemini 3.x deprecates explicit sampling parameters in generation config., classify_ai_error_reason(), Return an admin-safe LLM failure reason (stable across all providers). (+17 more)

### Community 38 - "logging"
Cohesion: 0.08
Nodes (47): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports(), _collect_secret_values() (+39 more)

### Community 39 - "LLMRouter"
Cohesion: 0.15
Nodes (54): api_key_env(), LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider, _http_error() (+46 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.05
Nodes (70): EventAnalysisDecision, _event_input_hash(), is_news_centered_event_action(), Keep trading-oriented guidance conditional and proportionate., Keep monitoring copy focused on market evidence, not supporting headlines., Reject direct trading instructions in every user-visible Event Alert field., sanitize_financial_instruction(), soften_possible_action() (+62 more)

### Community 42 - "provider_attempts"
Cohesion: 0.12
Nodes (18): provider_attempts(), provider_priority(), Resolve the ordered provider chain for a call type. Per-call-type override env…, Return the ordered concrete provider/model attempts for one logical LLM…, Case schema, Commands (offline by default), Frozen evidence contract, Independent blinded evaluation (+10 more)

### Community 43 - "automatic_price_check"
Cohesion: 0.13
Nodes (34): _build_event_analysis_id(), AlertRecipientResolution, automatic_price_check(), _enabled_subscription_by_symbol(), get_alert_recipients(), _get_or_create_event_alert_market_event(), Return active market symbols independently of current recipient eligibility., Resolve eligible recipients once for one market event. (+26 more)

### Community 44 - "db/alerts.py"
Cohesion: 0.07
Nodes (66): attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery(), get_event_ai_analysis(), get_last_sent_alert_at(), get_last_sent_event_alert_at_for_event_key(), get_latest_event_analysis_attempt() (+58 more)

### Community 45 - "bot/news.py"
Cohesion: 0.16
Nodes (29): _dedupe_report_news(), fetch_report_news_context(), within_window(), _has_report_news_identity(), _item_link(), _item_published_at(), _item_related_symbols(), _news_row_rank() (+21 more)

### Community 46 - "get_or_create_user"
Cohesion: 0.44
Nodes (12): get_or_create_user(), Create or update profile fields for the current Telegram interaction., build_session(), asyncio, test_get_or_create_user_allows_missing_username(), test_get_or_create_user_demotes_existing_admin_removed_from_allowlist(), test_get_or_create_user_keeps_non_admin_role_with_allowlist(), test_get_or_create_user_marks_second_admin_id_from_allowlist() (+4 more)

### Community 47 - "ccw15_prompt_pack.py"
Cohesion: 0.13
Nodes (19): build_event_significance_prompt(), Stage verified model-visible pilot calls into isolated CCW-16 workspace. No…, CCW-43 offline source verification, paired scoring, and restricted case error…, build_prompt(), check_production_parity(), inspect_private_frozen(), instruction(), main() (+11 more)

### Community 48 - "make_news_key"
Cohesion: 0.10
Nodes (34): _collapse_whitespace(), make_news_key(), _normalize_news_link(), Normalize repeated spaces so keys stay stable across feed formatting., Return a stable URL string for news identity checks., Build a stable key for a news item. Links are preferred because RSS titles can…, SeenNews, cleanup_seen_news() (+26 more)

### Community 49 - "refresh_report_cache_scheduled"
Cohesion: 0.30
Nodes (14): _is_report_provider_backoff_active(), Scheduled cache refresh: regenerate unless the cache stays fresh past the grace…, refresh_report_cache_scheduled(), _cached_report(), asyncio, Scheduled report cache refresh: cadence, grace window, and explicit skip…, test_daily_cache_fresh_by_seconds_at_fire_time_regenerates(), test_expired_weekly_cache_triggers_regeneration() (+6 more)

### Community 50 - "test_llm_rate_limit_backoff.py"
Cohesion: 0.07
Nodes (41): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions… (+33 more)

### Community 51 - "coin_icons.py"
Cohesion: 0.25
Nodes (10): _report_coin_icon_html(), _coin_fallback_emoji(), _sanitize_alert_payload(), build_coin_icon_prefix(), coin_custom_emoji_id(), coin_fallback_emoji(), MessageEntity, parametrize (+2 more)

### Community 52 - "test_event_alert_render_provider_chain.py"
Cohesion: 0.26
Nodes (19): call_render(), FakeProvider, good_render(), input_payload(), install(), patch_significance_and_storage(), ProviderError, asyncio (+11 more)

### Community 53 - "test_event_analysis_cloudflare_schema.py"
Cohesion: 0.12
Nodes (32): ask_event_alert_render_raw(), ask_event_significance_raw(), ask_market_heartbeat_raw(), ask_market_report_raw(), ask_news_intelligence_raw(), build_market_heartbeat_prompt(), build_market_report_prompt(), _json_response_validator() (+24 more)

### Community 54 - "test_event_alert_delivery_quality_regressions.py"
Cohesion: 0.20
Nodes (19): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, _event_alert_render_prompt_payload(), test_specific_next_observation_is_not_generic(), _decision(), _market(), parametrize, Regressions from 2026-10-13 delivered Event Alerts. These assertions inspect… (+11 more)

### Community 55 - "test_llm_outage_detectors.py"
Cohesion: 0.19
Nodes (23): _detector(), _evidence(), parametrize, Detectors and evidence quality for an LLM-side Event Analysis outage. Covers…, Mimic the collector: newest bucket first, each bucket capped by remaining…, _row(), _simulate_row_cap(), test_a_failure_storm_no_longer_starves_delivered_analyses_of_the_row_cap() (+15 more)

### Community 56 - "llm/config.py"
Cohesion: 0.07
Nodes (41): api_key(), base_url(), _format_chain(), global_provider_priority(), is_thinking_model(), _model_from_env(), openai_enabled(), _parse_priority_list() (+33 more)

### Community 57 - "CCWBot Growth Strategy: 0 -> 1 Premium"
Cohesion: 0.15
Nodes (12): Acquisition limitation, CCWBot Growth Strategy: 0 -> 1 Premium, Change, Current comparable cohort, Decision rule, Experiment 1 - Premium-only onboarding selector, Handoff prompt for a new chat, Primary metric (+4 more)

### Community 58 - "system_status.py"
Cohesion: 0.13
Nodes (35): _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, ComponentStatus, _delivery_failure_category(), _delivery_health() (+27 more)

### Community 59 - "price_service.py"
Cohesion: 0.13
Nodes (29): supported_symbols_display(), _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), _extract_sparkline_prices(), get_btc_market_data(), get_btc_price(), _get_cached_price() (+21 more)

### Community 60 - "bot/health.py"
Cohesion: 0.10
Nodes (23): aiohttp, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any, datetime, Authoritative last successful Event Analysis time, or None when unavailable.…, Event Analysis health, as a nested block that never changes the top-level… (+15 more)

### Community 61 - "cli.py"
Cohesion: 0.14
Nodes (31): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+23 more)

### Community 62 - "json"
Cohesion: 0.03
Nodes (41): collections, csv, html_parser, json, math, pathlib, re, main() (+33 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.10
Nodes (27): _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, bot_observability, evaluate_state(), failure_escalation_threshold(), max_success_age_seconds(), datetime, In-process health signal for Event Analysis. Event Alerts were fully dead for… (+19 more)

### Community 64 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 65 - "RedactionReport"
Cohesion: 0.07
Nodes (55): dataclasses, httpx, collect_health(), Any, collect_local_state(), Any, collect_logs(), _empty_counts() (+47 more)

### Community 66 - "/graphify"
Cohesion: 0.20
Nodes (9): CCWBot safety overrides, For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Usage (+1 more)

### Community 67 - "database.py"
Cohesion: 0.07
Nodes (40): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.… (+32 more)

### Community 68 - "test_report_content_rich_and_llm_summary.py"
Cohesion: 0.14
Nodes (17): MarketReportDecision, _build_daily_report_message(), _build_weekly_report_message(), _format_report_coin_watchpoints(), _format_weekly_breadth(), Bound LLM verbosity without replacing or manufacturing market claims., One price/change table, plus model watchpoints with no repeated quotes., Non-repeated per-coin watchpoints carry useful weekly analysis. (+9 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "validate_event_significance_output"
Cohesion: 0.18
Nodes (15): empirical_absolute_move_percentile(), EventSignificanceDecision, Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., validate_event_significance_output(), _payload(), parametrize, test_empirical_absolute_move_percentile_returns_none_for_insufficient_or_missing_data() (+7 more)

### Community 71 - "CCWBot"
Cohesion: 0.10
Nodes (20): Admin System Status, CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables (+12 more)

### Community 72 - "decimal"
Cohesion: 0.24
Nodes (11): calculate_price_change_percent(), is_cooldown_active(), datetime, Decimal, Core alert-rule helpers used by automatic market checks., Calculate a percent change without mixing binary floats and ``Decimal`` values., Return True while a previous alert is still inside the cooldown window., decimal (+3 more)

### Community 73 - "event_analysis.py"
Cohesion: 0.14
Nodes (36): CanonicalEventKey, _claim_clause(), _claimed_percent(), _decimal_market_value(), _direction_for_claim(), directional_market_family(), _duration_minutes(), _duration_minutes_from_claim() (+28 more)

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
Nodes (45): schedule_automatic_market_check(), _build_admin_llm_diagnostics_text(), _build_admin_system_status_text(), _format_acquisition_link(), _format_admin_alert_settings(), _llm_diagnostics_menu(), _parse_acquisition_link_arguments(), _premium_grant_usage_text() (+37 more)

### Community 78 - "ProviderResult"
Cohesion: 0.13
Nodes (21): ABC, BaseProvider, ProviderResult, Normalized successful chat-completion result returned by every provider., Common interface for all LLM providers., True when this provider has all configuration required for an attempt., Run one chat completion and return a :class:`ProviderResult` on success.…, _configure() (+13 more)

### Community 79 - "canonicalize_event_key"
Cohesion: 0.11
Nodes (27): canonicalize_event_key(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal(), _fallback_event_key(), _is_random_event_key(), _normalize_event_key_text() (+19 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.23
Nodes (37): NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap(), build_session(), FakeNewsLlm, asyncio (+29 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "datetime"
Cohesion: 0.04
Nodes (67): argparse, concurrent_futures, datetime, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., Audit only aggregated benchmark budget and next-call feasibility (no inference). (+59 more)

### Community 83 - "_fixture"
Cohesion: 0.09
Nodes (30): _event_analysis_prompt_payload(), Return the compact semantic model view without runtime or repeated static…, Clear all breaker state (tests and controlled restarts)., reset_breakers(), Clear in-memory provider/model backoffs for tests and controlled restarts., reset_llm_rate_limit_backoffs(), _isolate_llm_breaker_state(), _single_groq_provider() (+22 more)

### Community 84 - "_event_market_decision_detail"
Cohesion: 0.13
Nodes (16): _numeric_context_payload(), _raw_event_key_from_payload(), _semantic_family_from_payload(), _stable_float(), _stable_related_news_ids(), _decision_describes_market_event(), _decision_is_primarily_news_context(), _decision_text() (+8 more)

### Community 85 - "bot/config.py"
Cohesion: 0.16
Nodes (8): combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids(), Centralized configuration loaded from environment variables. Notes about key…, test_admin_user_ids_ignore_empty_whitespace_and_invalid_values(), test_multi_admin_user_ids_parse_comma_list(), test_single_admin_user_id_parses_for_backward_compatibility(), test_single_and_multi_admin_user_ids_are_combined_and_deduplicated()

### Community 86 - "event_chart.py"
Cohesion: 0.18
Nodes (15): ChartResult, _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw, Deterministic PNG chart from persisted, timestamped price observations only., Auditable reference value and its actual, not nominal, UTC timestamp. (+7 more)

### Community 87 - "ai_agent_groq.py"
Cohesion: 0.05
Nodes (49): Ground-truth evidence and limitations, Versioned artifacts, _json_dumps(), Canonical JSON that writes Decimal market values without binary-float loss., build_event_alert_render_prompt(), _event_analysis_percent(), _event_significance_prompt_payload(), Structured LLM facade used by Event Analysis, heartbeats, reports, and news.… (+41 more)

### Community 88 - "breaker.py"
Cohesion: 0.13
Nodes (30): _backoff_schedule(), breaker_snapshot(), _BreakerState, _failure_threshold(), is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics. (+22 more)

### Community 89 - "test_admin_cleanup.py"
Cohesion: 0.13
Nodes (17): bot_handlers, AsyncFalse, AsyncTrue, _callback_update(), _callback_values(), FakeMessage, FakeQuery, asyncio (+9 more)

### Community 90 - "Context Audit Report"
Cohesion: 0.09
Nodes (14): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+6 more)

### Community 91 - "test_product_analytics.py"
Cohesion: 0.07
Nodes (60): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+52 more)

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
Cohesion: 0.17
Nodes (18): Return the fully resolved per-call-type LLM configuration. Model identifiers,…, resolved_configuration(), _cost(), monthly_budget_usd(), OpenAIBudgetLease, _positive_decimal_env(), _positive_int_env(), pricing_usd_per_million() (+10 more)

### Community 97 - "BundleWriter"
Cohesion: 0.12
Nodes (15): BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk., sha256_file() (+7 more)

### Community 98 - "display_symbol"
Cohesion: 0.08
Nodes (41): display_symbol(), premium_symbols_display(), Supported coin metadata shared by price checks and Premium watchlists., build_admin_back_keyboard(), build_admin_keyboard(), build_admin_logs_keyboard(), build_admin_premium_keyboard(), build_first_run_brief_keyboard() (+33 more)

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

### Community 105 - "test_ai_agent_groq.py"
Cohesion: 0.12
Nodes (16): ask_event_analysis_raw(), build_event_analysis_prompt(), _parse_json(), Parse a JSON-object response without relaxing schema validation., parametrize, _set_groq_client(), test_event_alert_render_schema_only_contains_model_generated_fields(), test_event_analysis_prompt_makes_llm_the_market_significance_decider() (+8 more)

### Community 106 - "graphify reference: extra exports and benchmark"
Cohesion: 0.20
Nodes (9): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000) (+1 more)

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.33
Nodes (17): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+9 more)

### Community 108 - "test_news_ingestion.py"
Cohesion: 0.08
Nodes (25): ingest_news_job(), Hourly market-wide RSS ingestion; never creates alerts or resolves recipients., fetch_crypto_news(), headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources. (+17 more)

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

### Community 113 - "_create_event_analysis_decision"
Cohesion: 0.12
Nodes (31): _as_news_only_rejected_decision(), _create_event_analysis_decision(), _render_schema_check(), _significance_schema_check(), _event_alert_render_result_for_validation(), _event_alert_render_validation_reason(), _no_alert_decision_from_significance(), Use only backend-derived presentation after invalid LLM output exhausts… (+23 more)

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

### Community 128 - "test_alert_recipients.py"
Cohesion: 0.24
Nodes (9): FakeSession, asyncio, test_event_alert_eligibility_ignores_market_heartbeat_preference(), fake_get_active_users_with_alert_preferences(), test_event_recipient_resolution_is_isolated_from_trial_expiry_failures(), test_get_alert_recipients_deduplicates_active_db_users(), fake_get_active_users_with_alert_preferences(), test_get_alert_recipients_skips_non_btc_events() (+1 more)

### Community 129 - "test_permissions.py"
Cohesion: 0.27
Nodes (14): is_admin_update(), is_admin_user(), Update, sync_user_from_update(), asyncio, SessionContext, test_admin_check_ignores_invalid_user_id(), test_db_admin_check_accepts_second_admin_from_combined_allowlist() (+6 more)

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
Cohesion: 0.11
Nodes (17): _CapturingClient, _CapturingCompletions, _mock_openai_admission(), _provider_payload(), asyncio, Captures the kwargs the router passes, without making any provider call., _RecordingProvider, _route() (+9 more)

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

### Community 145 - "watchlist.py"
Cohesion: 0.22
Nodes (21): build_user_settings_render(), _current_telegram_user_id(), edit_myplan_message(), edit_user_settings_message(), edit_watchlist_message(), grant_premium_command(), _load_current_user(), myplan_command() (+13 more)

### Community 146 - "event_identity.py"
Cohesion: 0.08
Nodes (42): AnalysedWindowReference, _build_exact_event_context_fingerprint(), _canonical_decimal_string(), _canonical_event_analysis_context(), _event_analysis_datetime(), _event_analysis_news_age_hours(), _event_analysis_news_summary(), datetime (+34 more)

### Community 147 - "os"
Cohesion: 0.10
Nodes (18): asyncpg, bot_services, ctypes, dotenv, openai, os, call(), memory() (+10 more)

### Community 148 - "test_event_alert_composition_investigation.py"
Cohesion: 0.20
Nodes (26): market_direction_claims_supported(), Check explicit period directions and the direction implied by relationships., market(), parametrize, Synthetic regressions for the October alert-composition investigation., test_alignment_fallback_names_direction_and_verified_size_relationship(), test_alignment_without_monotonic_snapshots_survives_compaction(), test_consistent_with_describes_alignment_not_snapshot_persistence() (+18 more)

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.08
Nodes (50): _build_market_heartbeat_html_message(), _build_market_heartbeat_payload(), _decimal_numeric_context_value(), _deliver_market_heartbeat(), generate_market_heartbeats(), _heartbeat_numeric_context(), _is_fresh_heartbeat(), Decimal (+42 more)

### Community 150 - "User"
Cohesion: 0.08
Nodes (48): AlertRecipient, _automatic_delivery_lock(), _deliver_market_event_alert(), _get_due_market_heartbeat_recipients(), Send one sanitized event analysis to every resolved recipient., _recipient_decision_key(), _record_alert_delivery(), _record_alert_delivery_outcome() (+40 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.07
Nodes (56): effective_max_tokens_for(), is_reasoning_model(), log_resolved_configuration(), max_tokens_for(), model_for(), Resolve the model for a (provider, call_type) pair from env, with defaults., Resolve the completion-token budget for a call type. The current ``LLM_*`` name…, Return the completion budget for one concrete provider attempt. The public… (+48 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.16
Nodes (23): prepare_chart_points(), Never extrapolate over missing time or label a partial day as 24h., Event-specific references are opt-in; Heartbeat is exactly the old chart., render_price_chart(), _build_event_alert_rich_html(), _event_alert_for_recipient(), Insert the actual recipient's last delivered notification, never the global one., build_coin_icon_html() (+15 more)

### Community 156 - "validate_market_heartbeat_output"
Cohesion: 0.19
Nodes (18): MarketHeartbeatDecision, MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body(), sanitize_heartbeat_possible_action() (+10 more)

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

### Community 162 - "build_llm_messages"
Cohesion: 0.33
Nodes (6): build_llm_messages(), graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), base(), prepare(), add()

### Community 164 - "news_intelligence_service.py"
Cohesion: 0.11
Nodes (31): _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text(), _dedup_hint_is_specific_to_title(), _dedup_terms() (+23 more)

### Community 166 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.15
Nodes (20): ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment(), _migration_config() (+12 more)

### Community 169 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 170 - "LLMJsonResult"
Cohesion: 0.29
Nodes (5): LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., test_backward_compatible_public_api(), CorrelatedFallbackNewsLlm, tuple

### Community 171 - "conftest.py"
Cohesion: 0.15
Nodes (11): _real_socket, socket, _guarded_create_connection(), _guarded_getaddrinfo(), _GuardedSocket, _is_loopback(), _is_loopback_address(), _raise_external_network_block() (+3 more)

### Community 172 - "_send_alert_to_recipient_once"
Cohesion: 0.09
Nodes (27): cleanup_seen_news_job(), _delivery_error_class_name(), _delivery_retry_delay_seconds(), _disable_recipient_if_bot_blocked(), _is_permanent_telegram_delivery_error(), _is_transient_telegram_delivery_error(), Application, BaseException (+19 more)

### Community 173 - "test_exhausted_provider_chain_uses_verified_data_fallback"
Cohesion: 0.50
Nodes (5): asyncio, parametrize, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload()

### Community 174 - "collections_abc"
Cohesion: 0.09
Nodes (4): downgrade(), _is_sqlite(), upgrade(), collections_abc

### Community 176 - "handlers/reports.py"
Cohesion: 0.23
Nodes (10): daily_report(), DEFAULT_TYPE, Update, Market report command handlers., weekly_report(), send_weekly_report_message(), Groq free-tier admission control (Event Analysis), LLM Usage Reporting (+2 more)

### Community 177 - "test_ccw9_ccw10.py"
Cohesion: 0.18
Nodes (14): get_coin_price(), Get current coin price and 24h change from CoinGecko. Unsupported symbols raise…, fetch(), asyncio, parametrize, Regression coverage for CCW-9 transient command screens and CCW-10 price cache., test_admin_settings_navigation_remembers_entry_origin(), test_close_deletes_entire_result_and_stale_callback_is_rejected() (+6 more)

### Community 178 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 179 - "telegram_error"
Cohesion: 0.31
Nodes (8): handle_application_error(), Global python-telegram-bot error handler. Log-only: never sends anything to…, telegram_error, asyncio, parametrize, Global PTB error handler: concise WARNING for transient network errors, ERROR…, test_non_network_error_logs_error_with_traceback(), test_transient_network_error_logs_one_concise_warning()

### Community 180 - "resolve_period"
Cohesion: 0.24
Nodes (16): parse_timestamp(), Any, datetime, Path, record_collection(), record_report_success(), resolve_period(), save_state() (+8 more)

### Community 181 - "log"
Cohesion: 0.08
Nodes (26): schedule_report_cache_generation(), Market report use-case entrypoints., expire_due_premium_trials(), process_due_trial_expiries(), Application, DEFAULT_TYPE, Independent scheduling for durable Premium-trial lifecycle transitions., Lazy import keeps the scheduler independent of database compatibility exports. (+18 more)

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.17
Nodes (10): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps, Data handling, Event Alert research archive, Existing evidence (+2 more)

### Community 183 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 184 - "0004_multicoin_delivery_idempotency.py"
Cohesion: 0.83
Nodes (3): downgrade(), _unique_constraint_names(), upgrade()

### Community 185 - "RichDeliveryUncertain"
Cohesion: 0.14
Nodes (11): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert() (+3 more)

### Community 186 - "test_report_all_providers_schema_invalid_uses_deterministic_fallback"
Cohesion: 0.23
Nodes (11): _empty_report_news_context(), _install_report_inputs(), fake_market_data(), fake_news(), _market_data(), test_report_all_providers_schema_invalid_uses_deterministic_fallback(), fake_market_data(), fake_news() (+3 more)

### Community 188 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 189 - "normalize_symbol"
Cohesion: 0.05
Nodes (71): _automatic_market_check_job_name(), _build_event_instance_key(), _build_market_heartbeat_id(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _event_instance_bucket(), _event_instance_key_for_decision(), _candidate_news_relevance_label() (+63 more)

### Community 190 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 192 - "FakeResponse"
Cohesion: 0.19
Nodes (6): FakeClient, FakeResponse, test_get_coin_price_429_triggers_retry(), __init__(), test_get_with_retry_can_disable_stale_cache_after_429_retries(), test_get_with_retry_returns_stale_cache_after_429_retries()

### Community 193 - "test_price_handlers.py"
Cohesion: 0.19
Nodes (22): log_custom_emoji_ids(), price(), DEFAULT_TYPE, Update, Manual price lookup and text-message utility handlers., build_supported_symbols_message(), send_manual_rate_limit_message(), send_price_message() (+14 more)

### Community 194 - "LlmOperationOutcome"
Cohesion: 0.19
Nodes (11): LlmOperationOutcome, AsyncSession, LLM usage telemetry persistence. Belongs here: saving and updating…, Update a usage row when downstream JSON schema validation fails., Persist one sanitized terminal outcome for a logical LLM operation., save_llm_operation_outcome(), update_llm_usage_log_status(), count_recent_news_intelligence_llm_calls() (+3 more)

### Community 195 - "CCW-25 — Self-hosted LLM owner decision"
Cohesion: 0.25
Nodes (7): Actual local screen, CCW-25 — Self-hosted LLM owner decision, Low-risk next decision, Monthly EUR / DKK comparison, Specific candidates and serving stack, Volume sensitivity and break-even, What is measured

### Community 196 - "_build_event_analysis_input"
Cohesion: 0.14
Nodes (27): get_analysed_window_minutes(), _build_event_analysis_input(), _compact_event_snapshot(), _compact_event_snapshots(), _get_previous_event_alert_for_input(), _get_previous_event_alert_id(), _get_recent_event_analysis_decision_by_exact_context(), _parse_state_alert_at() (+19 more)

### Community 198 - "CCW-41 owner-reviewed significance reference v1"
Cohesion: 0.29
Nodes (6): Asset-specific labels, CCW-41 owner-reviewed significance reference v1, Historical bot against reference (selected benchmark only), How disputed labels changed, Using this reference for future model prompts, Warrant distributions

### Community 199 - "_working_code_backup.py"
Cohesion: 0.15
Nodes (31): event_alert_benchmark, _aggregate_markdown(), _cli(), compare_reviewers(), _field_exists(), _group_metrics(), import_results(), _label_counts() (+23 more)

### Community 201 - "test_chart_prepared_once_and_shared_not_in_recipient_loop"
Cohesion: 0.17
Nodes (8): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, Interpreter guard for subcommands, test_chart_prepared_once_and_shared_not_in_recipient_loop(), query()

### Community 202 - "test_price_service.py"
Cohesion: 0.15
Nodes (22): _extract_ton_coin_data_from_simple_price(), get_coin_market_data_batch(), Fetch market data for supported symbols with one CoinGecko request. Missing…, Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., clean_price_caches(), clear_price_caches(), isolate_http_client_construction(), asyncio (+14 more)

### Community 203 - "Base"
Cohesion: 0.08
Nodes (35): alembic_config, alembic_script, _count_suppression(), EventRecipientFilterResult, _filter_event_recipients_for_cooldown(), Base, Base class for all SQLAlchemy models., Save one LLM usage telemetry row. (+27 more)

### Community 204 - "CCW-29 Handoff — New CCW-43 Event Analysis Prompts"
Cohesion: 0.29
Nodes (6): Artifacts and cryptographic identity, CCW-29 Handoff — New CCW-43 Event Analysis Prompts, Current status, Exact prompt construction, Proposed bounded CCW-29 execution (requires separate owner approval), Provider-specific comparison settings to freeze

### Community 205 - "TransientBot"
Cohesion: 0.27
Nodes (8): Manual rich sends bypass PTB's normal send_message override., Intercept only messages sent in the scope of a manual command/callback., rich_reply_markup(), _tracking(), TransientBot, with_close_button(), ExtBot, test_close_markup_preserves_other_actions_and_does_not_duplicate()

### Community 206 - "Repository-backed Graphify"
Cohesion: 0.33
Nodes (5): One-time migration from existing Windows graph, Repository-backed Graphify, Retention, Shared state in dev, Updates after migration

### Community 208 - "0031_onboarding_customize_event.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_event_name_check(), upgrade()

### Community 209 - "get_int_env"
Cohesion: 0.20
Nodes (9): _get_int_env(), event_analysis_operation_budget_seconds(), Choose a per-attempt HTTP timeout; explicit caller overrides remain…, Bound the complete Event Analysis provider chain, not each provider…, request_timeout_seconds_for(), get_int_env(), Read an int env var, warning once when the configured value is unusable., test_credential_like_variable_value_is_never_logged() (+1 more)

### Community 210 - "pytest"
Cohesion: 0.13
Nodes (18): bot, compact_event_alert_possible_action(), Keep Event Alert actions short, conditional, and non-prescriptive., _load_news_driven_alert_candidates(), pytest, parametrize, Production-pattern regression fixtures; synthetic inputs, never recipient data., test_absent_current_move_does_not_invent_price_direction() (+10 more)

### Community 211 - "CCW-25 — Owner decision"
Cohesion: 0.33
Nodes (5): CCW-25 — Owner decision, Economics and next step, Evidence behind the decision, Models actually screened, What each option costs

### Community 212 - "CCWBot — итоги оценки alerts (16 октября 2026)"
Cohesion: 0.33
Nodes (5): CCWBot — итоги оценки alerts (16 октября 2026), Значимость, Полезность текста, Следующая инженерная работа, Файлы

### Community 213 - "test_transport_reuses_file_id_and_handles_valid_response"
Cohesion: 0.13
Nodes (8): asyncio, test_heartbeat_falls_back_to_styled_html_if_rich_adapter_has_no_token(), test_heartbeat_uses_existing_shared_price_snapshot_chart(), read_snapshots(), test_rich_ambiguous_error_never_falls_back_or_retries(), test_rich_confirmed_bad_request_falls_back_once(), test_transport_reuses_file_id_and_handles_valid_response(), post()

### Community 214 - "0026_growth_analytics.py"
Cohesion: 0.90
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 215 - "0027_market_heartbeat_defaults.py"
Cohesion: 0.70
Nodes (4): downgrade(), _has_alert_frequency_column(), _set_default(), upgrade()

### Community 217 - "convert_human_reviews.py"
Cohesion: 0.42
Nodes (8): finalize_reconciled(), labels_for(), main(), normalize_yes_no(), Convert two completed independent reviewer CSV sets to PR1 benchmark labels.…, rows(), score_disagreements(), validate_phase()

### Community 218 - "stage_economical_200.py"
Cohesion: 0.43
Nodes (5): as_utc(), compact(), pct(), CCW-45: freeze ONE compact matched Luna candidate; no source-control or…, rounded()

### Community 219 - "CCW-25 research evidence"
Cohesion: 0.40
Nodes (4): Billing assumptions, CCW-25 research evidence, Interpretation limits, Reproduce

### Community 220 - "operator_prompt.md"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C operator prompt, CCW-41 Reviewer C significance rubric v1, Frozen output schema, Frozen rubric

### Community 221 - "0005_telegram_stars_payments.py"
Cohesion: 0.83
Nodes (3): downgrade(), _table_names(), upgrade()

### Community 222 - "0007_unique_telegram_user_id.py"
Cohesion: 0.83
Nodes (3): _constraint_names(), downgrade(), upgrade()

### Community 223 - "0028_premium_trials.py"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 229 - "CCWBot — blind owner disagreement-only replay"
Cohesion: 0.33
Nodes (5): CCWBot — blind owner disagreement-only replay, Limitations and next actions, Operational recommendation, Owner comparison, disagreement subset only, Per coin (TP/FP/FN/TN)

### Community 231 - "0003_premium_watchlist_foundation.py"
Cohesion: 0.80
Nodes (4): _column_names(), downgrade(), _table_names(), upgrade()

### Community 232 - "0006_payment_recurring_metadata.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 233 - "0009_error_file_logging_toggle.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 235 - "_build_market_heartbeat_rich_html"
Cohesion: 0.50
Nodes (4): _build_market_heartbeat_rich_html(), Presentation only; heartbeat timing and eligibility stay unchanged., Compact, legible rich-message metrics. Keep labels and values contiguous., _rich_metric_html()

### Community 236 - "sanitize_alert_message"
Cohesion: 0.67
Nodes (3): Keep user-visible LLM text concise and remove accidental diagnostic lines., sanitize_alert_message(), test_sanitize_alert_message_drops_backend_diagnostic_lines()

## Knowledge Gaps
- **401 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+396 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1604 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `Observability Snippets` to `Ops-Agent Service`, `CCWBot Ops-Agent Report Analysis`, `test_transport_reuses_file_id_and_handles_valid_response`, `RichDeliveryUncertain`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `Observability Snippets`, `test_rich_market_report_delivery.py`, `_send_alert_to_recipient_once`, `bot/alerts.py`, `test_transport_reuses_file_id_and_handles_valid_response`, `test_event_alert_rich_chart_ux.py`, `bot/reports.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `summary()` connect `Market Reports` to `os`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 74 inferred relationships involving `LLMRouter` (e.g. with `AIInvalidJsonError` and `AIProviderRateLimitError`) actually correct?**
  _`LLMRouter` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 36 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _401 weakly-connected nodes found - possible documentation gaps or missing edges._