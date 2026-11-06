# Graph Report - CCWBot  (2026-11-06)

## Corpus Check
- 673 files · ~1,175,764 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 36 file(s) not represented in the graph (top: .toml 12, .csv 9, (none) 8)

## Summary
- 6115 nodes · 17996 edges · 250 communities (213 shown, 37 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1495 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `df898a39`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- ai_agent_groq.py
- datetime
- onboarding.py
- test_db_queries_and_detectors.py
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
- BundleWriter
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- watchlist.py
- news_context.py
- ProviderResult
- cli.py
- test_heartbeat_silence.py
- LlmUsageLog
- event_text.py
- properties
- os
- test_product_analytics.py
- validate_market_report_output
- properties
- health_response
- ccw41_reviewer_c_audit.py
- detectors.py
- user.py
- log
- test_report_cooldowns.py
- build_event_significance_prompt
- logging
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- utc_now
- Observability Snippets
- select
- bot/news.py
- AIProviderRateLimitError
- news_intelligence_service.py
- make_news_key
- runtime/state.py
- router.py
- ccw47_runner.py
- AISchemaValidationError
- test_event_analysis_health.py
- _create_event_analysis_decision
- test_llm_outage_detectors.py
- manifest.json
- CCWBot Growth Strategy: 0 -> 1 Premium
- _deliver_market_event_alert
- test_price_service.py
- system_status.py
- test_bundle_and_cli.py
- RichDeliveryUncertain
- pytest
- OpenAICompatibleProvider
- RedactionReport
- test_admin_cleanup.py
- test_event_alert_historical_diagnostics.py
- _fixture
- 0001_initial_schema.py
- event_analysis.py
- CCWBot
- llm/config.py
- replay_event_significance.py
- 0024_gram_symbol.py
- test_event_alert_composition_investigation.py
- test_agent_workflow_contract.py
- test_event_alert_previous_delivery_time.py
- openai_costs.py
- test_news_ingestion.py
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- time
- json
- bootstrap.py
- CCW-20 paired final messages
- event_chart.py
- test_llm_config_budgets.py
- test_watchlist_ux.py
- CCW-47 Final Event Significance Prompt Comparison
- Context Audit Report
- test_event_analysis_prompt_tokens.py
- grant_premium_command
- refresh_report_cache_scheduled
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- collections_abc
- EventAnalysisDecision
- test_event_alert_rich_chart_ux.py
- Ops-Agent Service
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- _build_exact_event_context_fingerprint
- AlertFailureStreaks
- test_event_alert_chart_markers.py
- validate_market_heartbeat_output
- Event Alert logic
- Repository Source of Truth
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
- OpenAIProvider
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
- event_identity.py
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
- payments.py
- test_openai_costs.py
- test_news_intelligence_schema.py
- Development
- test_market_heartbeat.py
- conftest.py
- test_heartbeat_postgres.py
- ChatGPT / Bridge / Codex Workflow
- provider_attempts
- collectors/__init__.py
- ops_agent/__init__.py
- test_multicoin_alerts.py
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- db.py
- graphify reference: GitHub clone and cross-repo merge
- admin.py
- pkgutil
- test_heartbeat_does_not_query_previous_event
- reviewer-c-rubric.md
- What You Must Do When Invoked
- extraction-spec.md
- LLMJsonResult
- test_rich_403_preserves_safe_blocked_classification_without_raw_errors
- CCW-41 exploratory Reviewer-C agreement/disagreement
- automatic_price_check
- 0008_database_comments.py
- bot/reports.py
- _runner_private.py
- _StructuredRecordBuffer
- test_alembic_migrations.py
- database.py
- test_price_handlers.py
- FakeAsyncClient
- /graphify
- test_network_guard.py
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- test_event_alert_pr2_cooldown.py
- CCW-43 — Evidence-based Event Analysis prompt redesign
- decimal
- 0031_onboarding_customize_event.py
- P
- 0025_llm_operation_correlation.py
- normalize_symbol
- get_alert_recipients
- .__init__
- unittest_mock
- User
- CCWBot Operational Report — Unverified (No Production Bundle)
- db/reports.py
- test_rich_httpx_transport_uncertainty_prevents_fallback
- CCW-25 — Self-hosted LLM owner decision
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- CCWBot — blind owner disagreement-only replay
- openai_budget.py
- Repository-backed Graphify
- CCW-25 research evidence
- datetime
- operator_prompt.md
- graphify reference: extra exports and benchmark
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- LLM Usage Reporting
- price_service.py
- README_RU.md
- 0026_growth_analytics.py
- fresh200_luna_wait_start.sh
- openai_luna_wait_start.sh
- _parse_json
- build_review.py
- 0027_market_heartbeat_defaults.py
- CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21)
- 0004_multicoin_delivery_idempotency.py
- coin_icons.py
- 0005_telegram_stars_payments.py
- 0003_premium_watchlist_foundation.py
- 0006_payment_recurring_metadata.py
- 0007_unique_telegram_user_id.py
- CCW20_FINAL_MESSAGE_BASELINE_20261026.md
- convert_human_reviews.py
- 0009_error_file_logging_toggle.py
- 0028_premium_trials.py
- _event_alert_for_recipient
- 0030_event_alert_policy_cleanup.py
- test_automatic_check_startup_log_shows_separated_symbol_first_delays
- FakeResponse
- test_event_alert_24h_now_continuity.py
- AIInvalidJsonError
- clean_news_title
- TransientSessions
- CCW-12 matched Luna significance comparison
- telegram_error
- TransientBot
- get_report_market_data_batch
- Event Alert cadence evaluation — CCW-50 (2026-11-06)
- test_schedule_automatic_price_check_coalesces_overlapping_runs

## God Nodes (most connected - your core abstractions)
1. `select()` - 173 edges
2. `Period` - 117 edges
3. `LLMRouter` - 102 edges
4. `Base` - 100 edges
5. `normalize_symbol()` - 92 edges
6. `EventAnalysisValidationError` - 87 edges
7. `User` - 68 edges
8. `run_detectors()` - 66 edges
9. `utc_now()` - 64 edges
10. `Alert` - 60 edges

## Surprising Connections (you probably didn't know these)
- `Event Alert chart reference markers (2026-10-26)` --references--> `price()`  [INFERRED]
  docs/alert_logic.md → bot/handlers/price.py
- `Read-only local check` --references--> `load_frozen()`  [INFERRED]
  benchmarks/ccw15-v1/README.md → scripts/event_alert_benchmark.py
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py
- `Event Alert Regression Evidence` --references--> `unknown()`  [INFERRED]
  docs/ops_agent_service.md → tests/test_event_alert_rich_chart_ux.py
- `Final Report Flow` --references--> `unknown()`  [INFERRED]
  docs/ops_agent_service.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (250 total, 37 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.10
Nodes (59): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), check(), check(), check() (+51 more)

### Community 1 - "ai_agent_groq.py"
Cohesion: 0.04
Nodes (68): _json_dumps(), Canonical JSON that writes Decimal market values without binary-float loss., compact_elapsed_since(), build_event_analysis_prompt(), build_market_heartbeat_prompt(), build_market_report_prompt(), _event_alert_render_market_metrics(), _event_analysis_percent() (+60 more)

### Community 2 - "datetime"
Cohesion: 0.08
Nodes (15): datetime, math, Audit only aggregated benchmark budget and next-call feasibility (no inference)., Direct GPT-6 review of 145 cases where three Luna prompts all reject., CCW-29 direct reasoned audit packet, no external calls or artificial labels., fmt(), CCW-44: optional quality-first enhancement with actual read-only historical…, reduce_history() (+7 more)

### Community 3 - "onboarding.py"
Cohesion: 0.10
Nodes (57): ProductEvent, UserCoinSubscription, build_first_run_brief_keyboard(), build_onboarding_customize_keyboard(), build_onboarding_keyboard(), Premium-only onboarding selector. BTC stays as the free default during…, _as_aware_utc(), build_instant_brief() (+49 more)

### Community 4 - "test_db_queries_and_detectors.py"
Cohesion: 0.05
Nodes (59): alembic_migration, alembic_operations, ops_agent_collectors, run_detectors(), Period, sqlite3, _assert_malformed_numeric_context_is_safe(), _assert_reconciliation_joins_across_period_boundaries() (+51 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.08
Nodes (70): _backoff_schedule(), breaker_snapshot(), _BreakerState, is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics., True when this triple is open and must be skipped in favour of the next… (+62 more)

### Community 6 - "telemetry.py"
Cohesion: 0.06
Nodes (77): _json_response_validator(), _validate(), Provider interface and the shared OpenAI-compatible provider implementation.…, LLMRateLimitBackoffActive, Provider-agnostic LLM error types shared across the provider router. These were…, Raised when a provider/model is already in temporary rate-limit backoff., LLM provider fallback package. Groq stays the primary provider; disabled-by-…, current_llm_operation_id() (+69 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.09
Nodes (45): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report(), market_report_change_chart() (+37 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.14
Nodes (34): Payment, build_premium_invoice_payload(), send_subscribe_invoice(), sqlalchemy_pool, AsyncNoop, build_session(), build_session_factory_for_concurrency(), create_user() (+26 more)

### Community 9 - "common.py"
Cohesion: 0.12
Nodes (27): decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, Edit a transient callback screen without exposing Telegram failures., Best-effort deletion of a user's slash command in a private chat. (+19 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.15
Nodes (54): PriceState, build_admin_llm_diagnostics_text(), build_admin_system_status_text(), _get_status_interval_seconds(), _llm_failure_summary(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health., builtins (+46 more)

### Community 12 - "test_openai_budget.py"
Cohesion: 0.16
Nodes (28): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., OpenAIBudget, OpenAIBudgetExhausted, RuntimeError, OpenAI was skipped before HTTP because safe authorization was unavailable., budget_db(), asyncio (+20 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.04
Nodes (70): alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.…, SeverityEvaluation (+62 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.13
Nodes (24): BudgetLease, _Charge, GroqBudget, GroqBudgetExhausted, datetime, Conservative zero-cost Groq admission control, shared across all call types. A…, Test-only reset; production restarts reload persisted usage., GroqProvider (+16 more)

### Community 15 - "BundleWriter"
Cohesion: 0.11
Nodes (16): ops_agent, BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk. (+8 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (67): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+59 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.08
Nodes (56): generate_report_cache(), Generate one market-wide LLM report and cache the completed or failed attempt., ask_event_analysis_raw(), ask_market_heartbeat_raw(), ask_market_report_raw(), ask_news_intelligence_raw(), bot_services_llm, get_router() (+48 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (81): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+73 more)

### Community 19 - "watchlist.py"
Cohesion: 0.18
Nodes (34): _as_aware_utc(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active(), is_user_trial_active() (+26 more)

### Community 20 - "news_context.py"
Cohesion: 0.09
Nodes (39): _alert_news_rank(), _candidate_news_relevance_label(), classify_news_relevance(), _coin_name(), filter_news_for_symbol(), _format_candidate_news(), _has_gram_crypto_context(), _is_clearly_market_wide_news() (+31 more)

### Community 21 - "ProviderResult"
Cohesion: 0.07
Nodes (41): ABC, ask_event_alert_render_raw(), ask_event_significance_raw(), Return JSON mode and provider-specific schemas for verified model attempts., _structured_response_formats(), BaseProvider, ProviderResult, Normalized successful chat-completion result returned by every provider. (+33 more)

### Community 22 - "cli.py"
Cohesion: 0.11
Nodes (37): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+29 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.15
Nodes (25): can_deliver_market_heartbeat_now(), pytest_asyncio, add_delivery(), asyncio, parametrize, test_cache_expiring_before_lock_acquisition_is_not_sent(), test_concurrent_checks_send_one_heartbeat_and_reset_timer(), test_delayed_success_uses_completion_not_reservation() (+17 more)

### Community 24 - "LlmUsageLog"
Cohesion: 0.15
Nodes (30): LlmUsageLog, LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider…, Compute 24h terminal outcomes. Raises on DB errors; never returns fake OK., read_logical_llm_health() (+22 more)

### Community 25 - "event_text.py"
Cohesion: 0.04
Nodes (99): _action_price_levels_supported(), _action_without_negated_technical_levels(), compact_event_alert_possible_action(), compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback() (+91 more)

### Community 26 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 27 - "os"
Cohesion: 0.06
Nodes (29): argparse, asyncpg, bot_services, build_llm_messages(), graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), copy, ctypes (+21 more)

### Community 28 - "test_product_analytics.py"
Cohesion: 0.07
Nodes (59): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+51 more)

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "health_response"
Cohesion: 0.08
Nodes (20): health_response(), handle_health(), Clear all state (tests and controlled restarts)., reset(), _clean_state(), asyncio, test_a_slow_database_degrades_the_block_instead_of_stalling_health(), test_health_counts_no_alert_as_a_successful_analysis() (+12 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.07
Nodes (72): audit(), positive_age_minutes(), ranking(), main(), _number(), _time(), _aggregate_markdown(), _cli() (+64 more)

### Community 33 - "detectors.py"
Cohesion: 0.11
Nodes (34): consecutive_zero_success_runs(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query(), _incomplete_files_gap() (+26 more)

### Community 34 - "user.py"
Cohesion: 0.42
Nodes (8): DEFAULT_TYPE, Update, General user command handlers., Best-effort product measurement that never exposes deep-link data to users., _record_start_analytics(), start(), _start_payload(), user_id()

### Community 35 - "log"
Cohesion: 0.08
Nodes (34): cleanup_seen_news_job(), Application, Compatibility wrapper for older imports; schedules the market-wide check., schedule_automatic_btc_check(), schedule_market_heartbeat_generation(), schedule_report_cache_generation(), schedule_seen_news_cleanup(), Alert and heartbeat use-case entrypoints. (+26 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.18
Nodes (33): MarketReport, reports(), _build_report_telegram_message(), get_or_generate_report(), One shared refresh on old content; never fan out LLM/RSS per recipient., AsyncClock, build_session_factory(), _daily_message() (+25 more)

### Community 37 - "build_event_significance_prompt"
Cohesion: 0.14
Nodes (18): build_event_significance_prompt(), Stage verified model-visible pilot calls into isolated CCW-16 workspace. No…, CCW-43 offline source verification, paired scoring, and restricted case error…, build_prompt(), check_production_parity(), inspect_private_frozen(), instruction(), main() (+10 more)

### Community 38 - "logging"
Cohesion: 0.08
Nodes (48): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports(), _collect_secret_values() (+40 more)

### Community 39 - "LLMRouter"
Cohesion: 0.14
Nodes (59): api_key_env(), AllProvidersFailedError, Raised when every provider in the fallback chain has been exhausted.…, LLMRouter, _call(), _call_validated(), _configure(), _content_result() (+51 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.07
Nodes (41): _event_alert_presentation_title(), _has_non_flat_analysed_market_context(), _llm_no_alert_decision_reason(), Render the headline from the primary deterministic metric, not LLM prose., contextlib, _assert_invalid_stage2(), _event_input(), asyncio (+33 more)

### Community 42 - "utc_now"
Cohesion: 0.22
Nodes (12): datetime, Return timezone-aware UTC timestamp., utc_now(), _decision(), asyncio, parametrize, Regression contracts for content-rich cached reports and concise admin…, test_admin_llm_summary_is_compact_and_provider_details_are_separate() (+4 more)

### Community 43 - "Observability Snippets"
Cohesion: 0.08
Nodes (28): Output, Rules you enforce, What you review, Admin System Status, CCW-50 Event Alert reliability signals (2026-11), Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis (+20 more)

### Community 44 - "select"
Cohesion: 0.05
Nodes (104): get_analysed_window_minutes(), _build_event_analysis_input(), _get_previous_event_alert_for_input(), _historical_event_analysis_moves(), Extract comparable historical moves; malformed historical evidence is ignored., attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol() (+96 more)

### Community 45 - "bot/news.py"
Cohesion: 0.12
Nodes (34): _dedupe_report_news(), fetch_news_context(), fetch_report_news_context(), within_window(), _has_report_news_identity(), _incident_phase(), _item_link(), _item_published_at() (+26 more)

### Community 46 - "AIProviderRateLimitError"
Cohesion: 0.16
Nodes (26): global_provider_priority(), provider_priority(), Resolve the ordered provider chain for a call type. Per-call-type override env…, AIProviderRateLimitError, Raised when a provider refuses a request because the account is rate limited., Startup configuration log, _configure(), _event_call() (+18 more)

### Community 47 - "news_intelligence_service.py"
Cohesion: 0.09
Nodes (33): get_cached_news_item_analysis(), Return a reusable structured news analysis for the exact model-aware input hash., new_llm_operation_id(), Return an opaque identifier for exactly one logical LLM operation., _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id() (+25 more)

### Community 48 - "make_news_key"
Cohesion: 0.11
Nodes (32): _collapse_whitespace(), make_news_key(), _normalize_news_link(), Normalize repeated spaces so keys stay stable across feed formatting., Return a stable URL string for news identity checks., Build a stable key for a news item. Links are preferred because RSS titles can…, SeenNews, cleanup_seen_news() (+24 more)

### Community 49 - "runtime/state.py"
Cohesion: 0.15
Nodes (12): Runtime state and startup helpers., close_database(), initialize_database(), Any, Dispose database resources created during startup., SessionFactoryRef, _sync_package_database_engine(), asyncio (+4 more)

### Community 50 - "router.py"
Cohesion: 0.08
Nodes (38): CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions…, get_provider(), get_provider(), OpenAI paid fallback, guarded by an explicit kill switch and durable budget., _default_registry(), _monotonic() (+30 more)

### Community 51 - "ccw47_runner.py"
Cohesion: 0.10
Nodes (20): pct(), Path, quality(), sha(), canonical(), compact(), execute(), load() (+12 more)

### Community 52 - "AISchemaValidationError"
Cohesion: 0.13
Nodes (38): _schema_check(), AISchemaValidationError, Raised when validated JSON does not match the expected schema. ``raw_content``…, call_render(), FakeProvider, good_render(), input_payload(), install() (+30 more)

### Community 53 - "test_event_analysis_health.py"
Cohesion: 0.09
Nodes (28): _log_event_analysis_failure(), Log global Event Analysis degradation without changing its historical contract., consecutive_failures(), evaluate_state(), failure_escalation_threshold(), max_success_age_seconds(), datetime, In-process health signal for Event Analysis. Event Alerts were fully dead for… (+20 more)

### Community 54 - "_create_event_analysis_decision"
Cohesion: 0.08
Nodes (59): _event_instance_key_for_decision(), _stable_related_news_ids(), _as_news_only_rejected_decision(), _create_event_analysis_decision(), _render_schema_check(), _event_alert_render_result_for_validation(), _event_alert_render_validation_reason(), _event_market_decision_detail() (+51 more)

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
Cohesion: 0.09
Nodes (42): AlertRecipient, _automatic_delivery_lock(), _deliver_market_event_alert(), _delivery_error_class_name(), _delivery_retry_delay_seconds(), _disable_recipient_if_bot_blocked(), _is_permanent_telegram_delivery_error(), _is_transient_telegram_delivery_error() (+34 more)

### Community 59 - "test_price_service.py"
Cohesion: 0.13
Nodes (22): supported_symbols_display(), _extract_ton_coin_data_from_simple_price(), get_coin_market_data_batch(), get_coin_price(), Get current coin price and 24h change from CoinGecko. Unsupported symbols raise…, Fetch market data for supported symbols with one CoinGecko request. Missing…, Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., clean_price_caches() (+14 more)

### Community 60 - "system_status.py"
Cohesion: 0.11
Nodes (37): _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, ComponentStatus, _container_started_at(), _delivery_failure_category() (+29 more)

### Community 61 - "test_bundle_and_cli.py"
Cohesion: 0.06
Nodes (47): _mark_report_success(), load_state(), parse_timestamp(), Any, datetime, Path, record_collection(), record_report_success() (+39 more)

### Community 62 - "RichDeliveryUncertain"
Cohesion: 0.11
Nodes (12): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert() (+4 more)

### Community 63 - "pytest"
Cohesion: 0.06
Nodes (46): bot, final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, _log_event_news_trace(), Log one shared prepared payload, never validation attempts or recipient data., _event_alert_render_prompt_payload(), Return only a supported sign; no rounded or raw market numbers reach Render., _render_market_direction() (+38 more)

### Community 64 - "OpenAICompatibleProvider"
Cohesion: 0.15
Nodes (9): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., GeminiProvider, get_provider(), Gemini provider (second fallback). Reached through Google's OpenAI-compatible… (+1 more)

### Community 65 - "RedactionReport"
Cohesion: 0.07
Nodes (65): dataclasses, collect_health(), Any, collect_logs(), _empty_counts(), _line_patterns(), _log_file_sort_key(), parse_log_timestamp() (+57 more)

### Community 66 - "test_admin_cleanup.py"
Cohesion: 0.14
Nodes (16): AsyncFalse, AsyncTrue, _callback_update(), _callback_values(), FakeMessage, FakeQuery, asyncio, test_admin_alert_settings_keyboard_has_no_threshold_controls() (+8 more)

### Community 67 - "test_event_alert_historical_diagnostics.py"
Cohesion: 0.11
Nodes (25): empirical_absolute_move_percentile(), EventSignificanceDecision, Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., validate_event_significance_output(), _significance_schema_check(), _market(), parametrize (+17 more)

### Community 68 - "_fixture"
Cohesion: 0.13
Nodes (17): Clear all breaker state (tests and controlled restarts)., reset_breakers(), Clear in-memory provider/model backoffs for tests and controlled restarts., reset_llm_rate_limit_backoffs(), _isolate_llm_breaker_state(), _test_verified_groq_routing(), _single_groq_provider(), _reset_state() (+9 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "event_analysis.py"
Cohesion: 0.06
Nodes (74): CanonicalEventKey, canonicalize_event_key(), _claim_clause(), _claimed_percent(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal() (+66 more)

### Community 71 - "CCWBot"
Cohesion: 0.11
Nodes (19): CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables, Features (+11 more)

### Community 72 - "llm/config.py"
Cohesion: 0.05
Nodes (59): _get_int_env(), _failure_threshold(), api_key(), base_url(), event_analysis_operation_budget_seconds(), _format_chain(), is_thinking_model(), log_resolved_configuration() (+51 more)

### Community 73 - "replay_event_significance.py"
Cohesion: 0.07
Nodes (54): _groq_json_mode_enabled(), scripts, blind_packet(), compare_recorded_run(), Path, Compare recorded, already-validated model results without an API call. A…, reconcile(), report() (+46 more)

### Community 74 - "0024_gram_symbol.py"
Cohesion: 0.33
Nodes (13): _coerce_related_symbols(), _column_names(), downgrade(), _has_table_and_symbol(), _has_table_columns(), _merge_price_state(), _merge_user_coin_subscriptions(), _merge_user_symbol_alert_state() (+5 more)

### Community 75 - "test_event_alert_composition_investigation.py"
Cohesion: 0.18
Nodes (29): market_direction_claims_supported(), Check explicit period directions and the direction implied by relationships., market(), parametrize, Synthetic regressions for the October alert-composition investigation., test_alignment_fallback_names_direction_and_verified_size_relationship(), test_alignment_without_monotonic_snapshots_survives_compaction(), test_comparative_strength_does_not_reverse_explicit_direction() (+21 more)

### Community 76 - "test_agent_workflow_contract.py"
Cohesion: 0.19
Nodes (10): _adapter_path(), _agent_names(), _agent_paths(), _load_toml(), Path, test_agent_definitions_have_matching_claude_adapters(), test_agent_definitions_have_required_schema(), test_agent_routing_references_existing_agents() (+2 more)

### Community 77 - "test_event_alert_previous_delivery_time.py"
Cohesion: 0.22
Nodes (10): _numeric_context_payload(), _stable_float(), _build_price_movement_event_key(), _get_or_create_price_movement_market_event(), _previous_event_alert_context(), Build one key for one observed price movement. Prices are rounded to cents and…, _stable_id_set_hash(), The global previous-alert hint reflects confirmed delivery, never reservation… (+2 more)

### Community 78 - "openai_costs.py"
Cohesion: 0.15
Nodes (28): _amount(), CostsDataError, _fetch(), format_costs_screen(), InternalCosts, _official_trends(), _parse_page(), ProviderCosts (+20 more)

### Community 79 - "test_news_ingestion.py"
Cohesion: 0.07
Nodes (36): fetch_crypto_news(), headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Merge available feeds by publication age *before* applying the batch limit. A…, Low-cost, word-boundary-aware prefilter; not an alert decision. (+28 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.19
Nodes (41): LlmOperationOutcome, NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap(), build_session(), CorrelatedFallbackNewsLlm (+33 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "time"
Cohesion: 0.07
Nodes (44): concurrent_futures, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., atom(), call_one(), check_reply() (+36 more)

### Community 83 - "json"
Cohesion: 0.03
Nodes (40): csv, html_parser, json, pathlib, re, CCW-25: bounded read-only aggregate collection; never exports prompts or IDs., main(), Verify completed research, reconcile metrics and fill the decision reports. (+32 more)

### Community 84 - "bootstrap.py"
Cohesion: 0.06
Nodes (49): AbstractEventLoop, aiohttp, AppRunner, asyncio, _event_analysis_block(), _isoformat_timestamp(), Any, datetime (+41 more)

### Community 85 - "CCW-20 paired final messages"
Cohesion: 0.09
Nodes (21): 10. ev_3c7f3da2e73e4b90 — ETH, 11. ev_7804adc277bd3333 — GRAM, 12. ev_345fc49db8255adf — GRAM, 13. ev_7b3325d2f2609480 — GRAM, 14. ev_1b39a518ede3c14f — GRAM, 15. ev_6500c5ad9f5364bc — GRAM, 16. ev_4bba21dd01bc8372 — SOL, 17. ev_1ea4cea05b78ed5c — SOL (+13 more)

### Community 86 - "event_chart.py"
Cohesion: 0.14
Nodes (20): ChartResult, _connectable_now_segment(), _display_marker_label(), _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw (+12 more)

### Community 87 - "test_llm_config_budgets.py"
Cohesion: 0.07
Nodes (51): effective_max_tokens_for(), is_reasoning_model(), max_tokens_for(), model_for(), Resolve the model for a (provider, call_type) pair from env, with defaults., Resolve the completion-token budget for a call type. The current ``LLM_*`` name…, Return the completion budget for one concrete provider attempt. The public…, True when this model identifier is known to accept ``reasoning_effort``. (+43 more)

### Community 88 - "test_watchlist_ux.py"
Cohesion: 0.08
Nodes (34): build_watchlist_keyboard(), build_subscribe_message(), build_watchlist_render(), AsyncFalse, AsyncNoop, AsyncTrue, CallbackQuery, FakeMessage (+26 more)

### Community 89 - "CCW-47 Final Event Significance Prompt Comparison"
Cohesion: 0.08
Nodes (23): CCW-47 Final Event Significance Prompt Comparison, confidence, Coverage and per-coin decisions, Decision differences, Distributions, Eight owner-ambiguous cases (excluded from scoring), Final recommendation, Focused error analysis (+15 more)

### Community 90 - "Context Audit Report"
Cohesion: 0.07
Nodes (18): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+10 more)

### Community 91 - "test_event_analysis_prompt_tokens.py"
Cohesion: 0.15
Nodes (19): _canonical_event_analysis_context(), _event_analysis_news_summary(), Return compact useful news text, dropping RSS markup/noise before the LLM., Semantic model and grounding context used for exact pre-LLM reuse., _compact_event_analysis_news(), _event_analysis_prompt_payload(), Return the compact semantic model view without runtime or repeated static…, _estimate_tokens() (+11 more)

### Community 92 - "grant_premium_command"
Cohesion: 0.22
Nodes (17): is_admin_update(), Update, _current_telegram_user_id(), grant_premium_command(), _load_current_user(), myplan_command(), _parse_target_telegram_user_id(), Update (+9 more)

### Community 93 - "refresh_report_cache_scheduled"
Cohesion: 0.33
Nodes (13): Scheduled cache refresh: regenerate unless the cache stays fresh past the grace…, refresh_report_cache_scheduled(), _cached_report(), asyncio, Scheduled report cache refresh: cadence, grace window, and explicit skip…, test_daily_cache_fresh_by_seconds_at_fire_time_regenerates(), test_expired_weekly_cache_triggers_regeneration(), test_failed_memory_refresh_preserves_still_valid_report() (+5 more)

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.15
Nodes (12): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Event Alert degradation counters (CCW-50), Log pattern counting (+4 more)

### Community 96 - "collections_abc"
Cohesion: 0.09
Nodes (4): downgrade(), _is_sqlite(), upgrade(), collections_abc

### Community 97 - "EventAnalysisDecision"
Cohesion: 0.07
Nodes (51): EventAnalysisDecision, _log_news_selection_summary(), _build_event_alert_html_message(), _build_event_alert_payload(), _decision_describes_market_event(), _decision_is_primarily_news_context(), _decision_text(), _decision_tokens() (+43 more)

### Community 98 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.11
Nodes (22): prepare_chart_points(), Never extrapolate over missing time or label a partial day as 24h., Event-specific references are opt-in; Heartbeat is exactly the old chart., render_price_chart(), _observations(), asyncio, Event Alert UX, chart evidence and single-send fallback contracts., test_chart_accepts_normal_30_minute_scheduler_jitter_but_rejects_stale() (+14 more)

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

### Community 106 - "AlertFailureStreaks"
Cohesion: 0.10
Nodes (18): AlertFailureStreaks, In-process, per-symbol Event Alert reliability counters. These counters are…, Count consecutive failures for separate Stage-1 and Render operations., Reset after a proven successful stage; return preceding streak., Test isolation only; the bot creates one in-process tracker., _log_event_alert_render_streak(), _log_event_alert_stage1_failure_streak(), Persist terminal telemetry and log an independent per-symbol Render streak. (+10 more)

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.32
Nodes (18): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+10 more)

### Community 108 - "validate_market_heartbeat_output"
Cohesion: 0.18
Nodes (19): MarketHeartbeatDecision, MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body(), sanitize_heartbeat_possible_action() (+11 more)

### Community 109 - "Event Alert logic"
Cohesion: 0.10
Nodes (21): Eight mandatory acceptance gates, Event Alert 24h metric and title (2026-10-29), Event Alert acceptance criteria (approved 2026-10-16), Event Alert chart reference markers (2026-10-26), Event Alert logic, Execution and release gates, Independent evidence and evaluation, Related news pipeline (+13 more)

### Community 110 - "Repository Source of Truth"
Cohesion: 0.33
Nodes (5): Canonical ownership, Conflict resolution, No standing rules outside the repository, Repository bootstrap, Repository Source of Truth

### Community 111 - "CCW-41 Reviewer C offline audit"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C offline audit, Compare only after sealing, Prepare frozen blind packets, Review and import

### Community 112 - "ccwbot-ops-agent-mark-report-success"
Cohesion: 0.70
Nodes (4): ccwbot-ops-agent-mark-report-success script, reject(), safe_relative_path(), usage()

### Community 113 - "OpenAIProvider"
Cohesion: 0.10
Nodes (19): OpenAIProvider, _CapturingClient, _CapturingCompletions, _mock_openai_admission(), _provider_payload(), asyncio, Captures the kwargs the router passes, without making any provider call., _RecordingProvider (+11 more)

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
Cohesion: 0.12
Nodes (5): _AlertEvidenceFakeConnection, _AlertEvidenceFakeEngine, _FakeResult, _FakeRow, datetime

### Community 118 - "CCWBot ChatGPT Project Instructions"
Cohesion: 0.40
Nodes (4): Canonical entry points, CCWBot ChatGPT Project Instructions, Execution priority, Required repository bootstrap

### Community 127 - "Product analytics"
Cohesion: 0.25
Nodes (7): Attribution payload, Create and inspect acquisition links, Direct Telegram Ads measurement, Funnel query, Onboarding v3 selector experiment, Onboarding value-delivery semantics, Product analytics

### Community 128 - "bot/config.py"
Cohesion: 0.10
Nodes (23): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids(), Centralized configuration loaded from environment variables. Notes about key…, is_admin_user() (+15 more)

### Community 129 - "event_identity.py"
Cohesion: 0.17
Nodes (15): AnalysedWindowReference, _canonical_decimal_string(), _event_analysis_datetime(), _event_analysis_news_age_hours(), datetime, Decimal, Pure Event Alert identity, precision, and scheduling helpers., Return a compact freshness fact instead of sending two timestamp strings. (+7 more)

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
Cohesion: 0.19
Nodes (33): UserPremiumSubscription, UserPremiumTrial, activate_premium_from_telegram_stars_payment(), _activate_premium_from_telegram_stars_payment_locked(), expire_due_premium_trials(), get_payment_by_provider_id(), get_user_premium_subscription(), get_user_premium_trial() (+25 more)

### Community 145 - "payments.py"
Cohesion: 0.16
Nodes (22): Application, register_bot_handlers(), build_premium_activation_keyboard(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date(), _get_payment_attr() (+14 more)

### Community 146 - "test_openai_costs.py"
Cohesion: 0.26
Nodes (22): OpenAICostsMonitor, bucket(), bucket_at(), client_mock(), configured(), page(), asyncio, parametrize (+14 more)

### Community 147 - "test_news_intelligence_schema.py"
Cohesion: 0.23
Nodes (19): _default_llm_client(), _schema_check(), derive_impact_level(), Reject parseable provider output that does not satisfy the requested news…, validate_llm_output(), validate_news_intelligence_schema(), asyncio, parametrize (+11 more)

### Community 148 - "Development"
Cohesion: 0.11
Nodes (13): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries (+5 more)

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.09
Nodes (46): _build_market_heartbeat_html_message(), _build_market_heartbeat_payload(), _deliver_market_heartbeat(), generate_market_heartbeats(), _heartbeat_numeric_context(), _is_fresh_heartbeat(), Decimal, _sanitize_event_text() (+38 more)

### Community 150 - "conftest.py"
Cohesion: 0.36
Nodes (7): _real_socket, _guarded_create_connection(), _guarded_getaddrinfo(), _GuardedSocket, _is_loopback(), _is_loopback_address(), _raise_external_network_block()

### Community 151 - "test_heartbeat_postgres.py"
Cohesion: 0.20
Nodes (13): automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, importlib, postgres_url(), asyncio, Real PostgreSQL locking checks; the SQLite process mutex cannot prove these… (+5 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "provider_attempts"
Cohesion: 0.20
Nodes (11): provider_attempts(), Return the ordered concrete provider/model attempts for one logical LLM…, Case schema, Commands (offline by default), Frozen evidence contract, Independent blinded evaluation, test_explicit_event_provider_overrides_select_only_openai_luna(), render_chain() (+3 more)

### Community 156 - "test_multicoin_alerts.py"
Cohesion: 0.09
Nodes (43): _build_news_candidates(), _classify_news_context(), _coin_is_secondary_context(), _news_relevance_reason(), Return active market symbols independently of current recipient eligibility., resolve_symbols_to_check(), ensure_default_coin_subscriptions(), grant_user_premium() (+35 more)

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
Cohesion: 0.10
Nodes (26): _alert_evidence_windows(), _collect_alert_repetition_rows(), collect_db(), _collector_error(), _jsonable(), Any, datetime, Exception (+18 more)

### Community 162 - "admin.py"
Cohesion: 0.08
Nodes (81): schedule_automatic_market_check(), build_acquisition_telegram_url(), Build a Telegram deep link only from a valid configured bot username and opaque…, acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_admin_llm_diagnostics_text() (+73 more)

### Community 164 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "LLMJsonResult"
Cohesion: 0.17
Nodes (9): AsyncSession, Persist one sanitized terminal outcome for a logical LLM operation., Save one LLM usage telemetry row., save_llm_operation_outcome(), save_llm_usage_log(), LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., test_backward_compatible_public_api() (+1 more)

### Community 169 - "test_rich_403_preserves_safe_blocked_classification_without_raw_errors"
Cohesion: 0.11
Nodes (6): parametrize, test_integrity_conflict_preserves_terminal_delivery_reservation(), test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post(), test_rich_confirmed_telegram_rejections(), post()

### Community 170 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 171 - "automatic_price_check"
Cohesion: 0.06
Nodes (46): _analysed_window_minutes_from_payload(), _build_event_analysis_id(), _event_input_hash(), _raw_event_key_from_payload(), _semantic_family_from_payload(), AlertRecipientResolution, automatic_price_check(), _count_suppression() (+38 more)

### Community 172 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 173 - "bot/reports.py"
Cohesion: 0.06
Nodes (58): MarketReportDecision, display_symbol(), _build_daily_report_message(), _build_deterministic_report_decision(), _build_market_report_input(), _build_report_coin_payload(), _build_weekly_breadth(), _build_weekly_coin_context() (+50 more)

### Community 174 - "_runner_private.py"
Cohesion: 0.28
Nodes (15): call_once(), classify(), fail(), main(), persist(), datetime, quota_allows(), Finite direct-provider CCW-16 canary runner; Python stdlib only. This script… (+7 more)

### Community 175 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 176 - "test_alembic_migrations.py"
Cohesion: 0.15
Nodes (20): ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment(), _migration_config() (+12 more)

### Community 177 - "database.py"
Cohesion: 0.06
Nodes (53): alembic_config, do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), alembic_script, AppSettings (+45 more)

### Community 178 - "test_price_handlers.py"
Cohesion: 0.18
Nodes (23): log_custom_emoji_ids(), price(), DEFAULT_TYPE, Update, Manual price lookup and text-message utility handlers., build_price_result_keyboard(), build_supported_symbols_message(), send_manual_rate_limit_message() (+15 more)

### Community 180 - "/graphify"
Cohesion: 0.09
Nodes (18): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+10 more)

### Community 181 - "test_network_guard.py"
Cohesion: 0.22
Nodes (4): socket, parametrize, Guards the test-suite network safety net installed in tests/conftest.py. If…, test_fallback_provider_hosts_are_blocked()

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.33
Nodes (5): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps

### Community 183 - "test_event_alert_pr2_cooldown.py"
Cohesion: 0.39
Nodes (8): _db(), asyncio, parametrize, PR 2 regressions for confirmed semantic cooldown boundary defects. No provider,…, Two distinct event rows can pass prefilter before the first send finishes., test_incomplete_persisted_identity_uses_own_verified_market_move(), test_late_delivery_remains_in_semantic_cooldown_query(), test_stale_prefilter_cannot_bypass_in_lock_cooldown()

### Community 184 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 185 - "decimal"
Cohesion: 0.24
Nodes (11): calculate_price_change_percent(), is_cooldown_active(), datetime, Decimal, Core alert-rule helpers used by automatic market checks., Calculate a percent change without mixing binary floats and ``Decimal`` values., Return True while a previous alert is still inside the cooldown window., decimal (+3 more)

### Community 186 - "0031_onboarding_customize_event.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_event_name_check(), upgrade()

### Community 188 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 189 - "normalize_symbol"
Cohesion: 0.17
Nodes (18): _automatic_market_check_job_name(), _build_event_instance_key(), _build_market_heartbeat_id(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _event_instance_bucket(), _news_metadata_matches_symbol(), _enabled_subscription_by_symbol() (+10 more)

### Community 190 - "get_alert_recipients"
Cohesion: 0.22
Nodes (11): get_alert_recipients(), Resolve eligible recipients once for one market event., FakeSession, asyncio, test_event_alert_eligibility_ignores_market_heartbeat_preference(), fake_get_active_users_with_alert_preferences(), test_event_recipient_resolution_is_isolated_from_trial_expiry_failures(), test_get_alert_recipients_deduplicates_active_db_users() (+3 more)

### Community 192 - "unittest_mock"
Cohesion: 0.19
Nodes (10): asyncio, parametrize, Report availability must survive exhausted LLM providers, but not unrelated…, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload(), asyncio, SessionContext (+2 more)

### Community 193 - "User"
Cohesion: 0.14
Nodes (32): User, backfill_blocked_users_from_alerts(), get_active_users_with_alert_preferences(), get_active_users_with_chat_ids(), get_or_create_user(), get_user_by_telegram_chat_id(), get_user_role(), is_telegram_chat_delivery_enabled() (+24 more)

### Community 194 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 195 - "db/reports.py"
Cohesion: 0.32
Nodes (7): get_latest_market_report(), AsyncSession, datetime, Market report cache persistence. Belongs here: daily/weekly market report cache…, Save one cached market report generation attempt., Return the newest cached market report for a cadence., save_market_report()

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

### Community 205 - "openai_budget.py"
Cohesion: 0.17
Nodes (18): _openai_budget_status_line(), Return an admin-safe current UTC-month paid-provider budget summary., _cost(), monthly_budget_usd(), OpenAIBudgetLease, _positive_decimal_env(), pricing_usd_per_million(), datetime (+10 more)

### Community 206 - "Repository-backed Graphify"
Cohesion: 0.33
Nodes (5): Clones and local development, Repository-backed Graphify, Retention, Shared state in dev, Updates after migration

### Community 207 - "CCW-25 research evidence"
Cohesion: 0.40
Nodes (4): Billing assumptions, CCW-25 research evidence, Interpretation limits, Reproduce

### Community 208 - "datetime"
Cohesion: 0.10
Nodes (34): _calculate_price_change(), _build_market_heartbeat_input(), _compact_event_snapshot(), _compact_event_snapshots(), _load_news_driven_alert_candidates(), _parse_state_alert_at(), _prepare_event_alert_chart(), datetime (+26 more)

### Community 209 - "operator_prompt.md"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C operator prompt, CCW-41 Reviewer C significance rubric v1, Frozen output schema, Frozen rubric

### Community 210 - "graphify reference: extra exports and benchmark"
Cohesion: 0.18
Nodes (10): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000) (+2 more)

### Community 213 - "LLM Usage Reporting"
Cohesion: 0.40
Nodes (4): Admin OpenAI Platform Costs monitoring (optional, read-only), Groq free-tier admission control (Event Analysis), LLM Usage Reporting, Ops-Agent LLM Usage Evidence

### Community 214 - "price_service.py"
Cohesion: 0.15
Nodes (24): _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), get_btc_market_data(), get_btc_price(), _get_cached_price(), _get_stale_cached_price(), _get_with_retry() (+16 more)

### Community 217 - "0026_growth_analytics.py"
Cohesion: 0.90
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 222 - "_parse_json"
Cohesion: 0.29
Nodes (6): _parse_json(), Parse a JSON-object response without relaxing schema validation., parametrize, test_event_analysis_prompt_preserves_subpercent_values_as_percentages(), test_parse_json_keeps_object_only_contract(), test_parse_json_handles_whitespace_and_invalid_text()

### Community 223 - "build_review.py"
Cohesion: 0.32
Nodes (11): candidate(), canon(), context(), csvwrite(), main(), Private read-only CCWBot market benchmark and independent review CSV exporter., run_psql(), safe() (+3 more)

### Community 224 - "0027_market_heartbeat_defaults.py"
Cohesion: 0.70
Nodes (4): downgrade(), _has_alert_frequency_column(), _set_default(), upgrade()

### Community 225 - "CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21)"
Cohesion: 0.33
Nodes (5): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Ground-truth evidence and limitations, Read-only local check, Versioned artifacts

### Community 226 - "0004_multicoin_delivery_idempotency.py"
Cohesion: 0.83
Nodes (3): downgrade(), _unique_constraint_names(), upgrade()

### Community 227 - "coin_icons.py"
Cohesion: 0.22
Nodes (13): Escape all model/news wording; only safely link explicit HTTP(S) sources., _report_coin_icon_html(), _safe_rich_line(), _coin_fallback_emoji(), build_coin_icon_html(), build_coin_icon_prefix(), coin_custom_emoji_id(), coin_fallback_emoji() (+5 more)

### Community 228 - "0005_telegram_stars_payments.py"
Cohesion: 0.83
Nodes (3): downgrade(), _table_names(), upgrade()

### Community 229 - "0003_premium_watchlist_foundation.py"
Cohesion: 0.80
Nodes (4): _column_names(), downgrade(), _table_names(), upgrade()

### Community 230 - "0006_payment_recurring_metadata.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 231 - "0007_unique_telegram_user_id.py"
Cohesion: 0.83
Nodes (3): _constraint_names(), downgrade(), upgrade()

### Community 233 - "convert_human_reviews.py"
Cohesion: 0.42
Nodes (8): finalize_reconciled(), labels_for(), main(), normalize_yes_no(), Convert two completed independent reviewer CSV sets to PR1 benchmark labels.…, rows(), score_disagreements(), validate_phase()

### Community 234 - "0009_error_file_logging_toggle.py"
Cohesion: 0.83
Nodes (3): _column_names(), downgrade(), upgrade()

### Community 235 - "0028_premium_trials.py"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 236 - "_event_alert_for_recipient"
Cohesion: 0.33
Nodes (5): _decimal_numeric_context_value(), _event_alert_for_recipient(), Insert the actual recipient's last delivered notification, never the global one., Read stored price evidence without converting a JSON number through binary…, test_heartbeat_decimal_context_reader_rejects_nonfinite_prior_price()

### Community 240 - "FakeResponse"
Cohesion: 0.19
Nodes (6): FakeClient, FakeResponse, test_get_coin_price_429_triggers_retry(), __init__(), test_get_with_retry_can_disable_stale_cache_after_429_retries(), test_get_with_retry_sends_demo_api_key()

### Community 242 - "test_event_alert_24h_now_continuity.py"
Cohesion: 0.27
Nodes (11): bot_alerting, pil, decision(), history(), market_payload(), Event Alert metric/title and true observed NOW continuity regressions., test_24h_metric_and_unambiguous_header_in_all_delivery_formats(), test_now_connection_draws_real_segment_inside_chart_plot() (+3 more)

### Community 243 - "AIInvalidJsonError"
Cohesion: 0.12
Nodes (14): AIInvalidJsonError, datetime, Exception, RuntimeError, Raised when the provider response is not valid JSON., Circuit breaker, Current Event Alert Luna-only policy (owner update 2026-10-29), Event Analysis timeout and operation budget (+6 more)

### Community 244 - "clean_news_title"
Cohesion: 0.32
Nodes (10): _format_event_related_context(), _format_market_heartbeat_related_context(), _format_related_context(), _safe_telegram_link_url(), _utf16_length(), clean_news_title(), clean_related_news_text(), test_clean_news_title_preserves_non_matching_titles() (+2 more)

### Community 246 - "CCW-12 matched Luna significance comparison"
Cohesion: 0.40
Nodes (4): CCW-12 matched Luna significance comparison, Changed binary decisions, Limits, Matched comparison

### Community 247 - "telegram_error"
Cohesion: 0.31
Nodes (8): handle_application_error(), Global python-telegram-bot error handler. Log-only: never sends anything to…, telegram_error, asyncio, parametrize, Global PTB error handler: concise WARNING for transient network errors, ERROR…, test_non_network_error_logs_error_with_traceback(), test_transient_network_error_logs_one_concise_warning()

### Community 248 - "TransientBot"
Cohesion: 0.33
Nodes (6): Intercept only messages sent in the scope of a manual command/callback., _tracking(), TransientBot, with_close_button(), ExtBot, test_close_markup_preserves_other_actions_and_does_not_duplicate()

### Community 250 - "get_report_market_data_batch"
Cohesion: 0.29
Nodes (8): _extract_sparkline_prices(), get_report_market_data_batch(), _optional_float(), _optional_int(), _range_position(), Fetch richer market data for cached daily/weekly reports. This intentionally…, test_get_report_market_data_batch_keeps_btc_alert_cache_unchanged(), test_get_report_market_data_batch_uses_markets_endpoint()

### Community 251 - "Event Alert cadence evaluation — CCW-50 (2026-11-06)"
Cohesion: 0.29
Nodes (6): Decision, Event Alert cadence evaluation — CCW-50 (2026-11-06), Follow-up decision gates, Hypothetical comparison — not a historical replay, Reproducible baseline, What this can and cannot establish

## Knowledge Gaps
- **467 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+462 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1791 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `Observability Snippets` to `test_event_alert_rich_chart_ux.py`, `Ops-Agent Service`, `CCWBot Ops-Agent Report Analysis`, `test_event_analysis_health.py`, `RichDeliveryUncertain`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `test_event_alert_rich_chart_ux.py`, `test_rich_market_report_delivery.py`, `Observability Snippets`, `bot/alerts.py`, `bot/reports.py`, `_deliver_market_event_alert`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `select()` connect `select` to `onboarding.py`, `test_telegram_stars_payments.py`, `test_system_status.py`, `test_openai_budget.py`, `test_groq_budget.py`, `db/premium.py`, `test_news_intelligence_schema.py`, `test_market_heartbeat.py`, `test_heartbeat_silence.py`, `LlmUsageLog`, `test_product_analytics.py`, `test_multicoin_alerts.py`, `test_report_cooldowns.py`, `automatic_price_check`, `bot/news.py`, `news_intelligence_service.py`, `make_news_key`, `database.py`, `router.py`, `_deliver_market_event_alert`, `system_status.py`, `User`, `db/reports.py`, `openai_budget.py`, `openai_costs.py`, `datetime`, `test_news_intelligence_service.py`, `build_review.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 170 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 170 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 79 inferred relationships involving `LLMRouter` (e.g. with `AIInvalidJsonError` and `AIProviderRateLimitError`) actually correct?**
  _`LLMRouter` has 79 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _467 weakly-connected nodes found - possible documentation gaps or missing edges._