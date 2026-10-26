# Graph Report - CCWBot  (2026-10-26)

## Corpus Check
- 323 files · ~296,198 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 27 file(s) not represented in the graph (top: .toml 12, (none) 8, .example 2)

## Summary
- 5000 nodes · 15110 edges · 217 communities (182 shown, 35 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1213 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `aa916068`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- replay_event_significance.py
- database.py
- test_onboarding.py
- Period
- test_llm_breaker.py
- ai_agent_groq.py
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
- test_event_alert_real_benchmark.py
- bootstrap.py
- test_news_intelligence_schema.py
- runtime/state.py
- test_heartbeat_silence.py
- BundleWriter
- event_text.py
- test_bundle_and_cli.py
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
- test_gemini_quota_backoff.py
- error_file_logging.py
- LLMRouter
- json
- test_event_alert_pipeline.py
- get_alert_recipients
- test_multicoin_alerts.py
- db/alerts.py
- bot/news.py
- User
- ccw15_prompt_pack.py
- db/news.py
- refresh_report_cache_scheduled
- test_llm_fallback.py
- market_report_rich.py
- test_event_alert_render_provider_chain.py
- test_ai_agent_groq.py
- test_event_alert_delivery_quality_regressions.py
- test_llm_outage_detectors.py
- automatic_price_check
- CCWBot Growth Strategy: 0 -> 1 Premium
- system_status.py
- price_service.py
- utc_now
- cli.py
- test_ccw41_reviewer_c_audit.py
- test_event_analysis_health.py
- settings
- RedactionReport
- /graphify
- test_heartbeat_postgres.py
- MarketReportDecision
- 0001_initial_schema.py
- validate_event_significance_output
- CCWBot
- decimal
- event_analysis.py
- 0024_gram_symbol.py
- Provider fallback (redundancy)
- test_agent_workflow_contract.py
- callbacks.py
- ProviderResult
- canonicalize_event_key
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- audit
- _fixture
- event_identity.py
- bot/config.py
- event_chart.py
- test_event_alert_historical_diagnostics.py
- collections_abc
- button_router
- ContractTests
- health_response
- test_price_service.py
- Development
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- TransientBot
- validate_market_heartbeat_output
- test_event_analysis_cloudflare_schema.py
- Ops-Agent Service
- test_market_heartbeat.py
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- test_news_driven_alerts.py
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
- conftest.py
- product-policy.md
- security-review.md
- telegram-stars-payments.md
- What You Must Do When Invoked
- AGENTS.md
- agents/README.md
- codex_task_prompt_template.md
- Project Context
- db/premium.py
- event_alert_benchmark.py
- _build_exact_event_context_fingerprint
- alembic/env.py
- test_event_alert_composition_investigation.py
- asyncio
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
- schemas.py
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
- test_transport_reuses_file_id_and_handles_valid_response
- test_exhausted_provider_chain_uses_verified_data_fallback
- 0003_premium_watchlist_foundation.py
- TransientSessions
- handlers/reports.py
- test_ccw9_ccw10.py
- FakeAsyncClient
- 0026_growth_analytics.py
- 0027_market_heartbeat_defaults.py
- log
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- test_heartbeat_does_not_query_previous_event
- 0004_multicoin_delivery_idempotency.py
- 0005_telegram_stars_payments.py
- 0006_payment_recurring_metadata.py
- 0007_unique_telegram_user_id.py
- 0009_error_file_logging_toggle.py
- normalize_symbol
- 0025_llm_operation_correlation.py
- .__init__
- 0028_premium_trials.py
- test_price_handlers.py
- _extract_ton_coin_data_from_simple_price
- bot/health.py
- Base
- NoopAsyncClient
- .__init__
- event_alert_benchmark
- telegram_error
- FakeResponse
- db/settings.py
- user.py
- CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21)
- Repository-backed Graphify
- 0030_event_alert_policy_cleanup.py
- 0031_onboarding_customize_event.py
- backfill_blocked_users.py
- Event Alert acceptance criteria (approved 2026-10-16)
- test_related_news_context_emits_selection_observability_log
- test_automatic_check_startup_log_shows_separated_symbol_first_delays
- test_heartbeat_generation_uses_active_symbols
- Presentation only; heartbeat timing and eligibility stay unchanged.
- Compact, legible rich-message metrics. Keep labels and values contiguous.

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
- `Which 4xx responses fall back` --references--> `AIInvalidJsonError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Read-only local check` --references--> `load_frozen()`  [INFERRED]
  benchmarks/ccw15-v1/README.md → scripts/event_alert_benchmark.py
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py
- `Event Alert Regression Evidence` --references--> `unknown()`  [INFERRED]
  docs/ops_agent_service.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (217 total, 35 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.14
Nodes (47): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), alert_analysis_result(), event_analysis_result(), factual_market_input() (+39 more)

### Community 1 - "replay_event_significance.py"
Cohesion: 0.09
Nodes (34): GroqProvider, scripts, blind_packet(), classify_replay_error(), effort_budget(), groq_significance_response_format(), live_report(), load_cases() (+26 more)

### Community 2 - "database.py"
Cohesion: 0.04
Nodes (80): LlmOperationOutcome, MarketHeartbeat, MarketReport, Database infrastructure for optional PostgreSQL runtime storage., Run Alembic migrations without blocking the active event loop., run_async_upgrade(), _run_upgrade(), AsyncSession (+72 more)

### Community 3 - "test_onboarding.py"
Cohesion: 0.15
Nodes (40): ProductEvent, UserCoinSubscription, _as_aware_utc(), build_instant_brief(), _first_run_btc_subscription(), handle_onboarding_callback(), _premium_intent_count(), datetime (+32 more)

### Community 4 - "Period"
Cohesion: 0.04
Nodes (66): alembic_migration, alembic_operations, importlib_util, ops_agent_collectors, _alert_evidence_windows(), datetime, run_detectors(), Period (+58 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.08
Nodes (79): _backoff_schedule(), breaker_snapshot(), _BreakerState, is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics., True when this triple is open and must be skipped in favour of the next… (+71 more)

### Community 6 - "ai_agent_groq.py"
Cohesion: 0.05
Nodes (79): _create_market_heartbeat(), ask_event_alert_render_raw(), ask_market_heartbeat_raw(), ask_news_intelligence_raw(), build_event_alert_render_prompt(), build_market_heartbeat_prompt(), _json_response_validator(), _validate() (+71 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.09
Nodes (44): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report(), market_report_change_chart() (+36 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.09
Nodes (55): Payment, build_premium_activation_keyboard(), build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date(), _get_payment_attr() (+47 more)

### Community 9 - "common.py"
Cohesion: 0.13
Nodes (21): _callback_command_update(), decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, _role_label() (+13 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.17
Nodes (50): AppSettings, LlmUsageLog, PriceState, build_admin_llm_diagnostics_text(), build_admin_system_status_text(), _get_status_interval_seconds(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health. (+42 more)

### Community 12 - "test_openai_budget.py"
Cohesion: 0.09
Nodes (46): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., Return the fully resolved per-call-type LLM configuration. Model identifiers,…, resolved_configuration(), _cost(), monthly_budget_usd(), OpenAIBudget, OpenAIBudgetExhausted (+38 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.06
Nodes (58): bot_alerting, alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.… (+50 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.15
Nodes (22): BudgetLease, _Charge, GroqBudget, GroqBudgetExhausted, datetime, Test-only reset; production restarts reload persisted usage., asyncio, Regression checks for zero-cost Groq pacing, day quota, symbol fairness and… (+14 more)

### Community 15 - "test_watchlist_ux.py"
Cohesion: 0.06
Nodes (47): ensure_default_coin_subscriptions(), Ensure one subscription row per supported symbol for a user., _load_private_callback_user(), build_subscribe_message(), build_watchlist_render(), handle_watchlist_callback(), AsyncFalse, AsyncNoop (+39 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (65): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+57 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.11
Nodes (50): _schema_check(), generate_report_cache(), _schema_check(), Generate one market-wide LLM report and cache the completed or failed attempt., ask_event_analysis_raw(), AISchemaValidationError, Raised when validated JSON does not match the expected schema. ``raw_content``…, _configure() (+42 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (79): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+71 more)

### Community 19 - "test_event_alert_real_benchmark.py"
Cohesion: 0.24
Nodes (23): compare_recorded_run(), load_frozen(), Path, Compare recorded, already-validated model results without an API call. A…, _read_evaluations(), reconcile(), report(), _case() (+15 more)

### Community 20 - "bootstrap.py"
Cohesion: 0.10
Nodes (29): AbstractEventLoop, AppRunner, asyncio, Application, register_bot_handlers(), start_health_server(), stop_health_server(), bot_runtime (+21 more)

### Community 21 - "test_news_intelligence_schema.py"
Cohesion: 0.27
Nodes (16): _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), asyncio, parametrize, Offline News Intelligence symbol-contract regression tests; no provider calls., _router() (+8 more)

### Community 22 - "runtime/state.py"
Cohesion: 0.15
Nodes (12): Runtime state and startup helpers., close_database(), initialize_database(), Any, Dispose database resources created during startup., SessionFactoryRef, _sync_package_database_engine(), asyncio (+4 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.13
Nodes (25): pytest_asyncio, fake_get_active_users_with_alert_preferences(), add_delivery(), asyncio, parametrize, test_cache_expiring_before_lock_acquisition_is_not_sent(), test_concurrent_checks_send_one_heartbeat_and_reset_timer(), test_delayed_success_uses_completion_not_reservation() (+17 more)

### Community 24 - "BundleWriter"
Cohesion: 0.08
Nodes (28): ops_agent, BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk. (+20 more)

### Community 25 - "event_text.py"
Cohesion: 0.09
Nodes (43): compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback(), _has_persistent_snapshot_direction(), _is_safe_llm_situation(), _is_safe_structured_market_interpretation() (+35 more)

### Community 26 - "test_bundle_and_cli.py"
Cohesion: 0.06
Nodes (51): _mark_report_success(), load_state(), parse_timestamp(), Any, datetime, Path, record_collection(), record_report_success() (+43 more)

### Community 27 - "bot/reports.py"
Cohesion: 0.08
Nodes (43): _build_deterministic_report_decision(), _build_market_report_input(), _build_report_coin_payload(), _build_weekly_breadth(), _build_weekly_coin_context(), _build_weekly_context(), _build_weekly_timeline(), _deterministic_coin_summary() (+35 more)

### Community 28 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "watchlist.py"
Cohesion: 0.12
Nodes (48): _as_aware_utc(), can_deliver_market_heartbeat_now(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active() (+40 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.14
Nodes (32): random, _aggregate_markdown(), _cli(), compare_reviewers(), _field_exists(), _group_metrics(), _label_counts(), _load_manifest() (+24 more)

### Community 33 - "detectors.py"
Cohesion: 0.12
Nodes (31): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+23 more)

### Community 34 - "admin.py"
Cohesion: 0.16
Nodes (45): build_acquisition_telegram_url(), Build a Telegram deep link only from a valid configured bot username and opaque…, acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_admin_llm_diagnostics_text(), _build_admin_system_status_text() (+37 more)

### Community 35 - "Observability Snippets"
Cohesion: 0.09
Nodes (25): Output, Rules you enforce, What you review, Admin System Status, Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis, Event Alert Exact Context Reuse (+17 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.17
Nodes (32): reports(), _build_report_telegram_message(), get_or_generate_report(), One shared refresh on old content; never fan out LLM/RSS per recipient., AsyncClock, build_session_factory(), _daily_message(), _empty_report_news_context() (+24 more)

### Community 37 - "test_gemini_quota_backoff.py"
Cohesion: 0.09
Nodes (25): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., CloudflareProvider, Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions…, GeminiProvider (+17 more)

### Community 38 - "error_file_logging.py"
Cohesion: 0.08
Nodes (47): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports(), _collect_secret_values() (+39 more)

### Community 39 - "LLMRouter"
Cohesion: 0.15
Nodes (53): LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider, _http_error(), _parse_json_validate() (+45 more)

### Community 40 - "json"
Cohesion: 0.09
Nodes (38): argparse, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, _returned_photo_file_id(), walk(), http_server, json, _clean_text(), collect_docker() (+30 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.04
Nodes (80): EventAnalysisDecision, with_canonical_event_key(), compact_event_alert_possible_action(), is_news_centered_event_action(), Keep trading-oriented guidance conditional and proportionate., Keep Event Alert actions short, conditional, and non-prescriptive., Keep monitoring copy focused on market evidence, not supporting headlines., Reject direct trading instructions in every user-visible Event Alert field. (+72 more)

### Community 42 - "get_alert_recipients"
Cohesion: 0.24
Nodes (10): get_alert_recipients(), Resolve eligible recipients once for one market event., FakeSession, asyncio, test_event_alert_eligibility_ignores_market_heartbeat_preference(), test_event_recipient_resolution_is_isolated_from_trial_expiry_failures(), test_get_alert_recipients_deduplicates_active_db_users(), fake_get_active_users_with_alert_preferences() (+2 more)

### Community 43 - "test_multicoin_alerts.py"
Cohesion: 0.10
Nodes (31): _classify_news_context(), Return active market symbols independently of current recipient eligibility., resolve_symbols_to_check(), set_user_coin_subscription(), build_session_factory(), create_user(), asyncio, test_automatic_fallback_state_persists_decimal_prices() (+23 more)

### Community 44 - "db/alerts.py"
Cohesion: 0.06
Nodes (87): attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery(), get_event_ai_analysis(), get_last_sent_alert(), get_last_sent_alert_at(), get_last_sent_event_alert_at_for_event_key() (+79 more)

### Community 45 - "bot/news.py"
Cohesion: 0.16
Nodes (29): _dedupe_report_news(), fetch_report_news_context(), within_window(), _has_report_news_identity(), _item_link(), _item_published_at(), _item_related_symbols(), _news_row_rank() (+21 more)

### Community 46 - "User"
Cohesion: 0.09
Nodes (44): User, backfill_blocked_users_from_alerts(), get_active_users_with_chat_ids(), get_or_create_user(), get_user_by_telegram_chat_id(), get_user_role(), is_telegram_chat_delivery_enabled(), mark_user_bot_blocked() (+36 more)

### Community 47 - "ccw15_prompt_pack.py"
Cohesion: 0.21
Nodes (17): _event_significance_prompt_payload(), Return the small always-on model view used only for significance., hashlib, build_prompt(), check_production_parity(), inspect_private_frozen(), instruction(), main() (+9 more)

### Community 48 - "db/news.py"
Cohesion: 0.16
Nodes (22): SeenNews, cleanup_seen_news(), count_recent_news_intelligence_llm_calls(), get_news_item_by_key(), get_recent_seen_news(), get_retryable_failed_news_items(), mark_news_items_seen(), mark_news_seen() (+14 more)

### Community 49 - "refresh_report_cache_scheduled"
Cohesion: 0.33
Nodes (13): Scheduled cache refresh: regenerate unless the cache stays fresh past the grace…, refresh_report_cache_scheduled(), _cached_report(), asyncio, Scheduled report cache refresh: cadence, grace window, and explicit skip…, test_daily_cache_fresh_by_seconds_at_fire_time_regenerates(), test_expired_weekly_cache_triggers_regeneration(), test_failed_memory_refresh_preserves_still_valid_report() (+5 more)

### Community 50 - "test_llm_fallback.py"
Cohesion: 0.10
Nodes (31): get_provider(), get_provider(), Groq provider (primary). OpenAI-compatible chat-completions API., get_provider(), OpenAI paid fallback, guarded by an explicit kill switch and durable budget., _default_registry(), get_llm_rate_limit_backoff(), Return the active provider/model backoff expiry, if any. (+23 more)

### Community 51 - "market_report_rich.py"
Cohesion: 0.07
Nodes (37): calculate_price_change_percent(), Decimal, Core alert-rule helpers used by automatic market checks., Calculate a percent change without mixing binary floats and ``Decimal`` values., _event_alert_change_label(), _format_analysed_window_label(), compact_elapsed_since(), MarketHeartbeatDecision (+29 more)

### Community 52 - "test_event_alert_render_provider_chain.py"
Cohesion: 0.26
Nodes (19): call_render(), FakeProvider, good_render(), input_payload(), install(), patch_significance_and_storage(), ProviderError, asyncio (+11 more)

### Community 53 - "test_ai_agent_groq.py"
Cohesion: 0.08
Nodes (22): ask_market_report_raw(), build_event_analysis_prompt(), build_market_report_prompt(), _parse_json(), Parse a JSON-object response without relaxing schema validation., bot_services_llm, The ops-agent's copy of the shipped model defaults must not drift from the…, parametrize (+14 more)

### Community 54 - "test_event_alert_delivery_quality_regressions.py"
Cohesion: 0.16
Nodes (22): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, _event_alert_render_prompt_payload(), Return only a supported sign; no rounded or raw market numbers reach Render., _render_market_direction(), test_specific_next_observation_is_not_generic(), _decision(), _market() (+14 more)

### Community 55 - "test_llm_outage_detectors.py"
Cohesion: 0.19
Nodes (23): _detector(), _evidence(), parametrize, Detectors and evidence quality for an LLM-side Event Analysis outage. Covers…, Mimic the collector: newest bucket first, each bucket capped by remaining…, _row(), _simulate_row_cap(), test_a_failure_storm_no_longer_starves_delivered_analyses_of_the_row_cap() (+15 more)

### Community 56 - "automatic_price_check"
Cohesion: 0.09
Nodes (34): directional_market_family(), Direction supported by the primary market window; not a significance threshold., _analysed_window_minutes_from_payload(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _news_driven_identity(), AlertRecipientResolution, automatic_price_check() (+26 more)

### Community 57 - "CCWBot Growth Strategy: 0 -> 1 Premium"
Cohesion: 0.15
Nodes (12): Acquisition limitation, CCWBot Growth Strategy: 0 -> 1 Premium, Change, Current comparable cohort, Decision rule, Experiment 1 - Premium-only onboarding selector, Handoff prompt for a new chat, Primary metric (+4 more)

### Community 58 - "system_status.py"
Cohesion: 0.12
Nodes (37): _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, ComponentStatus, _delivery_failure_category(), _delivery_health() (+29 more)

### Community 59 - "price_service.py"
Cohesion: 0.13
Nodes (28): _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), _extract_sparkline_prices(), get_btc_market_data(), get_btc_price(), _get_cached_price(), get_report_market_data_batch() (+20 more)

### Community 60 - "utc_now"
Cohesion: 0.06
Nodes (65): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+57 more)

### Community 61 - "cli.py"
Cohesion: 0.14
Nodes (31): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+23 more)

### Community 62 - "test_ccw41_reviewer_c_audit.py"
Cohesion: 0.19
Nodes (30): import_results(), _narrative_findings(), digest(), _case(), _dataset(), _labels(), prepared(), MonkeyPatch (+22 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.11
Nodes (19): _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, evaluate_state(), failure_escalation_threshold(), max_success_age_seconds(), Return ``(state, last_success_age_seconds)`` for the Event Analysis health…, Event Analysis health: /health reporting, log escalation, and suppression…, test_a_long_failure_streak_is_degraded() (+11 more)

### Community 64 - "settings"
Cohesion: 0.20
Nodes (16): Edit a transient callback screen without exposing Telegram failures., Best-effort deletion of a user's slash command in a private chat., safe_delete_command_invocation(), safe_edit_callback_message(), DEFAULT_TYPE, Update, settings(), _edit_onboarding_message() (+8 more)

### Community 65 - "RedactionReport"
Cohesion: 0.07
Nodes (63): collections, httpx, _collect_alert_repetition_rows(), collect_db(), _collector_error(), _jsonable(), Any, Exception (+55 more)

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

### Community 70 - "validate_event_significance_output"
Cohesion: 0.19
Nodes (14): empirical_absolute_move_percentile(), Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., _required_choice(), validate_event_significance_output(), _significance_schema_check(), parametrize, test_empirical_absolute_move_percentile_returns_none_for_insufficient_or_missing_data() (+6 more)

### Community 71 - "CCWBot"
Cohesion: 0.10
Nodes (20): Admin System Status, CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables (+12 more)

### Community 72 - "decimal"
Cohesion: 0.29
Nodes (7): is_cooldown_active(), datetime, Return True while a previous alert is still inside the cooldown window., decimal, test_calculate_price_change_percent_accepts_mixed_decimal_and_float_operands(), test_calculate_price_change_percent_preserves_direction(), test_cooldown_active_only_inside_window()

### Community 73 - "event_analysis.py"
Cohesion: 0.16
Nodes (31): _claim_clause(), _claimed_percent(), _decimal_market_value(), _direction_for_claim(), _duration_minutes(), _duration_minutes_from_claim(), _elapsed_minutes(), _has_last_message_context() (+23 more)

### Community 74 - "0024_gram_symbol.py"
Cohesion: 0.33
Nodes (13): _coerce_related_symbols(), _column_names(), downgrade(), _has_table_and_symbol(), _has_table_columns(), _merge_price_state(), _merge_user_coin_subscriptions(), _merge_user_symbol_alert_state() (+5 more)

### Community 75 - "Provider fallback (redundancy)"
Cohesion: 0.33
Nodes (6): Circuit breaker, Event Analysis timeout and operation budget, Historical Gemini 429 quota classification and backoff, Optional OpenAI activation and spend cap, Provider fallback (redundancy), Which 4xx responses fall back

### Community 76 - "test_agent_workflow_contract.py"
Cohesion: 0.19
Nodes (10): _adapter_path(), _agent_names(), _agent_paths(), _load_toml(), Path, test_agent_definitions_have_matching_claude_adapters(), test_agent_definitions_have_required_schema(), test_agent_routing_references_existing_agents() (+2 more)

### Community 77 - "callbacks.py"
Cohesion: 0.15
Nodes (26): Central callback-query router for Telegram inline keyboards., log_custom_emoji_ids(), price(), DEFAULT_TYPE, Update, Manual price lookup and text-message utility handlers., User settings command handler., build_price_keyboard() (+18 more)

### Community 78 - "ProviderResult"
Cohesion: 0.12
Nodes (21): ABC, BaseProvider, ProviderResult, Normalized successful chat-completion result returned by every provider., Common interface for all LLM providers., True when this provider has all configuration required for an attempt., Run one chat completion and return a :class:`ProviderResult` on success.…, _configure() (+13 more)

### Community 79 - "canonicalize_event_key"
Cohesion: 0.10
Nodes (29): CanonicalEventKey, canonicalize_event_key(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal(), _fallback_event_key(), _is_random_event_key() (+21 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.24
Nodes (37): NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap(), build_session(), FakeNewsLlm, asyncio (+29 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "audit"
Cohesion: 0.24
Nodes (12): audit(), positive_age_minutes(), ranking(), main(), _number(), _time(), Production timeline review tests: decision counts are not ground-truth FP/FN., _row() (+4 more)

### Community 83 - "_fixture"
Cohesion: 0.10
Nodes (28): _event_analysis_percent(), _event_analysis_prompt_payload(), Bound model-visible percent precision without erasing a non-zero sign., Return the compact semantic model view without runtime or repeated static…, Clear all breaker state (tests and controlled restarts)., reset_breakers(), _isolate_llm_breaker_state(), _reset_state() (+20 more)

### Community 84 - "event_identity.py"
Cohesion: 0.08
Nodes (38): AnalysedWindowReference, _automatic_market_check_job_name(), _build_event_analysis_id(), _build_event_instance_key(), _canonical_decimal_string(), _canonical_event_analysis_context(), _event_analysis_datetime(), _event_analysis_news_age_hours() (+30 more)

### Community 85 - "bot/config.py"
Cohesion: 0.11
Nodes (23): combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids(), Centralized configuration loaded from environment variables. Notes about key…, is_admin_update(), is_admin_user(), Update, sync_user_from_update() (+15 more)

### Community 86 - "event_chart.py"
Cohesion: 0.15
Nodes (22): ChartResult, _draw_reference_shape(), _font(), _observed(), prepare_chart_points(), datetime, ImageDraw, Deterministic PNG chart from persisted, timestamped price observations only. (+14 more)

### Community 87 - "test_event_alert_historical_diagnostics.py"
Cohesion: 0.13
Nodes (17): bot, build_event_significance_prompt(), copy, _market(), parametrize, Historical alert defect contracts: never call an external provider or Telegram.…, test_contradictory_period_alignment_is_never_delivered_as_factual_claim(), test_exact_reuse_excludes_changed_micro_moves_and_news() (+9 more)

### Community 88 - "collections_abc"
Cohesion: 0.09
Nodes (4): downgrade(), _is_sqlite(), upgrade(), collections_abc

### Community 89 - "button_router"
Cohesion: 0.13
Nodes (21): bot_handlers, button_router(), DEFAULT_TYPE, Update, build_interval_keyboard(), AsyncFalse, AsyncTrue, _callback_update() (+13 more)

### Community 91 - "health_response"
Cohesion: 0.13
Nodes (14): health_response(), Any, handle_health(), asyncio, test_a_slow_database_degrades_the_block_instead_of_stalling_health(), test_health_counts_no_alert_as_a_successful_analysis(), _logical_success(), test_health_payload_carries_no_secrets_or_environment_values() (+6 more)

### Community 92 - "test_price_service.py"
Cohesion: 0.15
Nodes (19): get_coin_price(), Get current coin price and 24h change from CoinGecko. Unsupported symbols raise…, clean_price_caches(), clear_price_caches(), isolate_http_client_construction(), asyncio, test_get_btc_market_data_does_not_request_unreliable_simple_price_7d(), test_get_coin_market_data_batch_accepts_gram_alias() (+11 more)

### Community 93 - "Development"
Cohesion: 0.25
Nodes (8): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.17
Nodes (11): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Log pattern counting, News-candidate signal (+3 more)

### Community 96 - "TransientBot"
Cohesion: 0.27
Nodes (8): Manual rich sends bypass PTB's normal send_message override., Intercept only messages sent in the scope of a manual command/callback., rich_reply_markup(), _tracking(), TransientBot, with_close_button(), ExtBot, test_close_markup_preserves_other_actions_and_does_not_duplicate()

### Community 97 - "validate_market_heartbeat_output"
Cohesion: 0.23
Nodes (13): MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), validate_market_heartbeat_output(), heartbeat_result(), parametrize (+5 more)

### Community 98 - "test_event_analysis_cloudflare_schema.py"
Cohesion: 0.20
Nodes (19): ask_event_significance_raw(), _groq_json_mode_enabled(), Return JSON mode and provider-specific schemas for verified model attempts., _structured_response_formats(), llm_operation_scope(), Make one operation identifier visible to every nested provider attempt., _configure(), asyncio (+11 more)

### Community 99 - "Ops-Agent Service"
Cohesion: 0.18
Nodes (10): Boundaries, Bundle Publication Contract, Event Alert Regression Evidence, Final Report Flow, Forensic Correlation Evidence, Local References, Ops-Agent Service, Production Access Model (+2 more)

### Community 100 - "test_market_heartbeat.py"
Cohesion: 0.10
Nodes (12): heartbeat_raw_input(), test_custom_emoji_entity_is_used_when_id_exists(), test_custom_emoji_logging_helper_logs_admin_entities(), test_event_and_heartbeat_rendering_use_new_labels_and_fallback_emoji(), test_heartbeat_decimal_context_reader_rejects_nonfinite_prior_price(), test_heartbeat_related_context_empty_selection_is_hidden(), test_heartbeat_related_context_missing_url_stays_plain_text(), test_heartbeat_related_context_uses_direct_article_links_and_escaping() (+4 more)

### Community 101 - "ccwbot-ops-agent-collect"
Cohesion: 0.40
Nodes (8): ccwbot-ops-agent-collect script, fail_preflight(), interrupted(), is_utc_timestamp(), reject(), usage(), validate_period(), write_receipt()

### Community 103 - "Dev Ops Guide"
Cohesion: 0.12
Nodes (15): Dependency updates, Deploying Ops-Agent Changes, Dev Ops Guide, Environment Rules, Future approved deployment and incident recovery, Legacy wrapper installation (historical, not routine after operator cutover), Manual Production Deploy (exceptional releases only), Non-interactive, least-privilege bot deploys (+7 more)

### Community 104 - "Event Alert benchmark and historical diagnostics (PR 1)"
Cohesion: 0.29
Nodes (4): Event Alert benchmark and historical diagnostics (PR 1), Historical investigation: evidence status, Next-stage dependency and acceptance, Technical baseline, not product-quality scores

### Community 105 - "test_news_driven_alerts.py"
Cohesion: 0.47
Nodes (5): _load_news_driven_alert_candidates(), asyncio, Regression coverage for the disabled standalone-news Event Alert path., test_news_driven_alerts_warning_logs_once_not_per_cycle(), test_news_driven_flag_cannot_bypass_product_policy()

### Community 106 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.27
Nodes (19): io, pil, event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history() (+11 more)

### Community 108 - "test_news_ingestion.py"
Cohesion: 0.08
Nodes (23): headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Low-cost, word-boundary-aware prefilter; not an alert decision., Bound provider latency/response size; parse only successfully fetched bytes., _read_rss_feed() (+15 more)

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
Cohesion: 0.10
Nodes (36): _calculate_price_change(), _build_event_analysis_input(), _build_market_heartbeat_input(), _compact_event_snapshot(), _compact_event_snapshots(), _get_recent_event_analysis_decision_by_exact_context(), _historical_event_analysis_moves(), _parse_state_alert_at() (+28 more)

### Community 129 - "onboarding.py"
Cohesion: 0.13
Nodes (26): build_admin_alert_settings_keyboard(), build_admin_back_keyboard(), build_admin_keyboard(), build_admin_logs_keyboard(), build_admin_premium_keyboard(), build_first_run_brief_keyboard(), build_onboarding_customize_keyboard(), build_onboarding_keyboard() (+18 more)

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

### Community 135 - "conftest.py"
Cohesion: 0.15
Nodes (11): _real_socket, socket, _guarded_create_connection(), _guarded_getaddrinfo(), _GuardedSocket, _is_loopback(), _is_loopback_address(), _raise_external_network_block() (+3 more)

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

### Community 145 - "event_alert_benchmark.py"
Cohesion: 0.33
Nodes (9): canonical_json(), _check_private_data(), _confusion(), _delivered_precision(), _quality(), _ratio(), Privacy-safe frozen real-market evaluation for the existing significance…, scope() (+1 more)

### Community 146 - "_build_exact_event_context_fingerprint"
Cohesion: 0.32
Nodes (13): _build_exact_event_context_fingerprint(), _payload(), parametrize, test_decimal_json_is_full_precision_json_number_not_float_or_string(), test_exact_context_does_not_reuse_the_ambiguous_change_field_contract(), test_exact_context_ignores_previous_title_not_sent_to_model(), test_exact_context_ignores_runtime_metadata_and_normalizes_decimal_representation(), test_exact_context_includes_last_message_time_for_grounding_reuse() (+5 more)

### Community 147 - "alembic/env.py"
Cohesion: 0.33
Nodes (8): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), Connection, logging_config, sqlalchemy_engine

### Community 148 - "test_event_alert_composition_investigation.py"
Cohesion: 0.20
Nodes (26): market_direction_claims_supported(), Check explicit period directions and the direction implied by relationships., market(), parametrize, Synthetic regressions for the October alert-composition investigation., test_alignment_fallback_names_direction_and_verified_size_relationship(), test_alignment_without_monotonic_snapshots_survives_compaction(), test_consistent_with_describes_alignment_not_snapshot_persistence() (+18 more)

### Community 149 - "asyncio"
Cohesion: 0.26
Nodes (22): build_session_factory(), create_heartbeat(), create_user(), fake_app(), asyncio, The real automatic path passes Decimal prices into a DB-backed heartbeat…, A no-alert automatic check must reach its completion log after heartbeat…, test_automatic_llm_no_alert_cycle_delivers_decimal_heartbeat_and_completes() (+14 more)

### Community 150 - "_deliver_market_event_alert"
Cohesion: 0.07
Nodes (45): Send one rich message; reuse Telegram photo file_id when the API returns one.…, send_rich_event_alert(), AlertRecipient, _automatic_delivery_lock(), _decimal_numeric_context_value(), _deliver_market_event_alert(), _deliver_market_heartbeat(), _delivery_error_class_name() (+37 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.03
Nodes (144): _get_int_env(), _failure_threshold(), api_key(), api_key_env(), base_url(), effective_max_tokens_for(), event_analysis_operation_budget_seconds(), _format_chain() (+136 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.19
Nodes (11): _observations(), Event Alert UX, chart evidence and single-send fallback contracts., test_chart_downtime_selects_latest_gap_free_run_without_inventing_prices(), test_chart_full_day_uses_observed_timestamps_and_png(), test_chart_ignores_invalid_price_or_timestamp_without_fabricating_points(), test_half_hour_persisted_samples_use_true_24h_axis_without_fabrication(), test_heartbeat_uses_existing_shared_price_snapshot_chart(), read_snapshots() (+3 more)

### Community 156 - "event_analysis_health.py"
Cohesion: 0.22
Nodes (12): consecutive_failures(), datetime, In-process health signal for Event Analysis. Event Alerts were fully dead for…, A successful event analysis clears the failure streak., Count one failed event analysis and return the new consecutive-failure count., Sanitized view for diagnostics: counters and timestamps only, never payload…, record_failure(), record_success() (+4 more)

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

### Community 164 - "news_intelligence_service.py"
Cohesion: 0.09
Nodes (37): get_cached_news_item_analysis(), get_cooling_failed_news_keys(), Return a reusable structured news analysis for the exact model-aware input hash., Prevent immediate retries after LLM failure or a budget skip., _budget_priority_score(), build_llm_messages(), build_llm_payload(), build_post_llm_dedup_group_id() (+29 more)

### Community 166 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.14
Nodes (21): alembic_script, ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment() (+13 more)

### Community 169 - "Repository Source of Truth"
Cohesion: 0.33
Nodes (5): Canonical ownership, Conflict resolution, No standing rules outside the repository, Repository bootstrap, Repository Source of Truth

### Community 170 - "LLMJsonResult"
Cohesion: 0.25
Nodes (5): LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., test_backward_compatible_public_api(), CorrelatedFallbackNewsLlm, tuple

### Community 171 - "clean_news_title"
Cohesion: 0.32
Nodes (10): _format_event_related_context(), _format_market_heartbeat_related_context(), _format_related_context(), _safe_telegram_link_url(), _utf16_length(), clean_news_title(), clean_related_news_text(), test_clean_news_title_preserves_non_matching_titles() (+2 more)

### Community 173 - "test_exhausted_provider_chain_uses_verified_data_fallback"
Cohesion: 0.50
Nodes (5): asyncio, parametrize, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload()

### Community 174 - "0003_premium_watchlist_foundation.py"
Cohesion: 0.80
Nodes (4): _column_names(), downgrade(), _table_names(), upgrade()

### Community 176 - "handlers/reports.py"
Cohesion: 0.23
Nodes (10): daily_report(), DEFAULT_TYPE, Update, Market report command handlers., weekly_report(), send_weekly_report_message(), Groq free-tier admission control (Event Analysis), LLM Usage Reporting (+2 more)

### Community 177 - "test_ccw9_ccw10.py"
Cohesion: 0.22
Nodes (11): bot_services, asyncio, parametrize, Regression coverage for CCW-9 transient command screens and CCW-10 price cache., test_admin_settings_navigation_remembers_entry_origin(), test_close_deletes_entire_result_and_stale_callback_is_rejected(), test_coingecko_429_sets_provider_backoff_without_ui_rate_limit(), test_consecutive_commands_retire_all_prior_results_by_chat_and_user() (+3 more)

### Community 179 - "0026_growth_analytics.py"
Cohesion: 0.90
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 180 - "0027_market_heartbeat_defaults.py"
Cohesion: 0.70
Nodes (4): downgrade(), _has_alert_frequency_column(), _set_default(), upgrade()

### Community 181 - "log"
Cohesion: 0.09
Nodes (37): _build_market_heartbeat_id(), cleanup_seen_news_job(), generate_market_heartbeats(), _is_fresh_heartbeat(), Application, DEFAULT_TYPE, Compatibility wrapper for older imports; schedules the market-wide check., schedule_automatic_btc_check() (+29 more)

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.17
Nodes (10): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps, Data handling, Event Alert research archive, Existing evidence (+2 more)

### Community 183 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 184 - "0004_multicoin_delivery_idempotency.py"
Cohesion: 0.83
Nodes (3): downgrade(), _unique_constraint_names(), upgrade()

### Community 185 - "0005_telegram_stars_payments.py"
Cohesion: 0.83
Nodes (3): downgrade(), _table_names(), upgrade()

### Community 186 - "0006_payment_recurring_metadata.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 187 - "0007_unique_telegram_user_id.py"
Cohesion: 0.83
Nodes (3): _constraint_names(), downgrade(), upgrade()

### Community 188 - "0009_error_file_logging_toggle.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 189 - "normalize_symbol"
Cohesion: 0.06
Nodes (67): _stable_float(), _candidate_news_relevance_label(), classify_news_relevance(), _coin_name(), filter_news_for_symbol(), _format_candidate_news(), _has_gram_crypto_context(), _is_clearly_market_wide_news() (+59 more)

### Community 190 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 192 - "0028_premium_trials.py"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 193 - "test_price_handlers.py"
Cohesion: 0.40
Nodes (12): clear_manual_price_rate_limits(), _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users(), test_price_maps_provider_errors_to_safe_user_messages(), test_price_normalizes_legacy_ton_alias_before_lookup(), test_price_rejects_unsupported_symbol_without_provider_call() (+4 more)

### Community 194 - "_extract_ton_coin_data_from_simple_price"
Cohesion: 0.50
Nodes (4): _extract_ton_coin_data_from_simple_price(), Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., test_ton_simple_price_extractor_accepts_only_current_gram_id(), test_ton_simple_price_extractor_rejects_arbitrary_symbol_candidates()

### Community 195 - "bot/health.py"
Cohesion: 0.33
Nodes (9): aiohttp, _event_analysis_block(), _isoformat_timestamp(), datetime, Authoritative last successful Event Analysis time, or None when unavailable.…, Event Analysis health, as a nested block that never changes the top-level…, _read_event_analysis_logical_health(), _read_last_btc_check_at() (+1 more)

### Community 196 - "Base"
Cohesion: 0.08
Nodes (31): alembic_config, Base, Base class for all SQLAlchemy models., DeclarativeBase, _alembic_head(), _load_comments_migration(), _load_event_alert_policy_migration(), _load_market_heartbeat_migration() (+23 more)

### Community 201 - "telegram_error"
Cohesion: 0.31
Nodes (8): handle_application_error(), Global python-telegram-bot error handler. Log-only: never sends anything to…, telegram_error, asyncio, parametrize, Global PTB error handler: concise WARNING for transient network errors, ERROR…, test_non_network_error_logs_error_with_traceback(), test_transient_network_error_logs_one_concise_warning()

### Community 202 - "FakeResponse"
Cohesion: 0.27
Nodes (5): FakeClient, FakeResponse, __init__(), test_get_with_retry_can_disable_stale_cache_after_429_retries(), test_get_with_retry_returns_stale_cache_after_429_retries()

### Community 203 - "db/settings.py"
Cohesion: 0.47
Nodes (8): UserSettings, _get_app_settings_row(), get_or_create_app_settings(), get_or_create_user_settings(), AsyncSession, Global and legacy per-user settings persistence. Belongs here: app-wide alert…, update_app_settings(), update_user_settings()

### Community 204 - "user.py"
Cohesion: 0.42
Nodes (8): DEFAULT_TYPE, Update, General user command handlers., Best-effort product measurement that never exposes deep-link data to users., _record_start_analytics(), start(), _start_payload(), user_id()

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

### Community 211 - "test_related_news_context_emits_selection_observability_log"
Cohesion: 0.50
Nodes (3): test_related_news_context_emits_selection_observability_log(), test_related_news_context_falls_back_to_existing_rss_selection(), fake_fetch_news_context()

## Knowledge Gaps
- **272 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+267 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1328 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `Observability Snippets` to `Ops-Agent Service`, `test_rich_market_report_delivery.py`, `CCWBot Ops-Agent Report Analysis`, `_deliver_market_event_alert`, `event_analysis_health.py`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `test_rich_market_report_delivery.py` to `Observability Snippets`, `json`, `bot/alerts.py`, `_deliver_market_event_alert`, `test_event_alert_rich_chart_ux.py`, `bot/reports.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `query()` connect `/graphify` to `test_event_alert_rich_chart_ux.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 74 inferred relationships involving `LLMRouter` (e.g. with `AIInvalidJsonError` and `AIProviderRateLimitError`) actually correct?**
  _`LLMRouter` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 36 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _272 weakly-connected nodes found - possible documentation gaps or missing edges._