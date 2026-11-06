# Graph Report - CCWBot  (2026-11-06)

## Corpus Check
- 672 files · ~1,175,233 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 36 file(s) not represented in the graph (top: .toml 12, .csv 9, (none) 8)

## Summary
- 6099 nodes · 17940 edges · 257 communities (221 shown, 36 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1488 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c3bcf9fc`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- hashlib
- event_alert_benchmark.py
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
- domain/premium.py
- normalize_symbol
- test_event_analysis_cloudflare_schema.py
- cli.py
- test_heartbeat_silence.py
- LlmUsageLog
- event_text.py
- properties
- ai_agent_groq.py
- test_product_analytics.py
- validate_market_report_output
- properties
- health_response
- ccw41_reviewer_c_audit.py
- detectors.py
- user.py
- schedule_report_cache_generation
- test_report_cooldowns.py
- _event_significance_prompt_payload
- logging
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- MarketReportDecision
- Observability Snippets
- select
- bot/news.py
- ProviderResult
- news_intelligence_service.py
- db/news.py
- SessionFactoryRef
- router.py
- ccw47_runner.py
- test_event_alert_render_provider_chain.py
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
- test_gram_render_prompt_reliability.py
- LLMRateLimitBackoffActive
- RedactionReport
- button_router
- validate_event_significance_output
- _send_alert_to_recipient_once
- 0001_initial_schema.py
- event_analysis.py
- CCWBot
- llm/config.py
- replay_event_significance.py
- 0024_gram_symbol.py
- test_event_alert_composition_investigation.py
- test_agent_workflow_contract.py
- test_event_alert_delivery_quality_regressions.py
- openai_costs.py
- news_service.py
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- datetime
- json
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
- collections_abc
- _build_event_alert_payload
- test_event_alert_rich_chart_ux.py
- unknown
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- test_event_alert_historical_diagnostics.py
- AlertFailureStreaks
- test_event_alert_chart_markers.py
- validate_market_heartbeat_output
- Event Alert logic
- README.md
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
- _RecordingProvider
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
- utc_now
- payments.py
- test_openai_costs.py
- test_news_intelligence_schema.py
- Development
- test_market_heartbeat.py
- build_alert_evidence_payloads
- test_heartbeat_postgres.py
- ChatGPT / Bridge / Codex Workflow
- provider_attempts
- collectors/__init__.py
- ops_agent/__init__.py
- test_multicoin_alerts.py
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- test_event_alert_reliability_diagnostics.py
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
- report_context.py
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- test_news_ingestion.py
- CCW-43 — Evidence-based Event Analysis prompt redesign
- calculate_price_change_percent
- 0031_onboarding_customize_event.py
- P
- 0025_llm_operation_correlation.py
- display_symbol
- resolve_alert_recipient_outcomes
- .__init__
- test_exhausted_provider_chain_uses_verified_data_fallback
- User
- CCWBot Operational Report — Unverified (No Production Bundle)
- handlers/reports.py
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
- Provider fallback (redundancy)
- price_service.py
- README_RU.md
- 0026_growth_analytics.py
- fresh200_luna_wait_start.sh
- openai_luna_wait_start.sh
- get_int_env
- build_review.py
- 0027_market_heartbeat_defaults.py
- render_decision_report_context
- 0004_multicoin_delivery_idempotency.py
- _build_market_heartbeat_payload
- 0005_telegram_stars_payments.py
- 0003_premium_watchlist_foundation.py
- 0006_payment_recurring_metadata.py
- 0007_unique_telegram_user_id.py
- CCW20_FINAL_MESSAGE_BASELINE_20261026.md
- convert_human_reviews.py
- 0009_error_file_logging_toggle.py
- 0028_premium_trials.py
- reasoning_effort_for
- test_ai_agent_groq.py
- db/prices.py
- handle_watchlist_callback
- FakeResponse
- test_observability_reconciliation.py
- test_event_alert_24h_now_continuity.py
- AIInvalidJsonError
- clean_news_title
- TransientSessions
- CCW-12 matched Luna significance comparison
- telegram_error
- TransientBot
- test_rich_chart_quality_detector.py
- get_report_market_data_batch
- Event Alert cadence evaluation — CCW-50 (2026-11-06)
- test_growth_analytics_migration.py
- Documentation
- schedule_automatic_btc_check
- _extract_ton_coin_data_from_simple_price
- test_schedule_automatic_price_check_coalesces_overlapping_runs

## God Nodes (most connected - your core abstractions)
1. `select()` - 173 edges
2. `Period` - 117 edges
3. `Base` - 100 edges
4. `LLMRouter` - 99 edges
5. `normalize_symbol()` - 92 edges
6. `EventAnalysisValidationError` - 84 edges
7. `User` - 68 edges
8. `run_detectors()` - 66 edges
9. `utc_now()` - 64 edges
10. `Alert` - 60 edges

## Surprising Connections (you probably didn't know these)
- `Event Alert chart reference markers (2026-10-26)` --references--> `price()`  [INFERRED]
  docs/alert_logic.md → bot/handlers/price.py
- `Which 4xx responses fall back` --references--> `AIInvalidJsonError`  [INFERRED]
  docs/llm_usage.md → bot/services/llm/errors.py
- `Read-only local check` --references--> `load_frozen()`  [INFERRED]
  benchmarks/ccw15-v1/README.md → scripts/event_alert_benchmark.py
- `Evidence rules` --references--> `unknown()`  [INFERRED]
  docs/ops-agent-report-codex-prompt.md → tests/test_event_alert_rich_chart_ux.py
- `Production Read-Only Setup` --references--> `unknown()`  [INFERRED]
  ops_agent/README.md → tests/test_event_alert_rich_chart_ux.py

## Import Cycles
- None detected.

## Communities (257 total, 36 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.10
Nodes (59): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), check(), check(), check() (+51 more)

### Community 1 - "hashlib"
Cohesion: 0.04
Nodes (46): _json_dumps(), Canonical JSON that writes Decimal market values without binary-float loss., copy, hashlib, html_parser, io, Change only the CCW-16 experiment user cron cadence, preserving all other jobs., Read-only provider credential authentication probe on isolated Hetzner… (+38 more)

### Community 2 - "event_alert_benchmark.py"
Cohesion: 0.11
Nodes (41): importlib_util, random, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, CCW-29 fresh private holdout: collect real POST-200 market cases via…, CCW-29 new unseen 20-case holdout: verified sealed inputs, model replies,…, choose(), Freeze fresh 200 real CCWBot market cases, excluding both earlier sets;…, blind_packet() (+33 more)

### Community 3 - "onboarding.py"
Cohesion: 0.10
Nodes (57): ProductEvent, UserCoinSubscription, ensure_default_coin_subscriptions(), Ensure one subscription row per supported symbol for a user., build_premium_paywall_keyboard(), build_trial_offer_keyboard(), _as_aware_utc(), build_instant_brief() (+49 more)

### Community 4 - "test_db_queries_and_detectors.py"
Cohesion: 0.04
Nodes (65): alembic_migration, alembic_operations, ops_agent_collectors, _alert_evidence_windows(), datetime, run_detectors(), Period, sqlite3 (+57 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.08
Nodes (75): _backoff_schedule(), breaker_snapshot(), _BreakerState, _failure_threshold(), is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics. (+67 more)

### Community 6 - "telemetry.py"
Cohesion: 0.09
Nodes (52): _json_response_validator(), _validate(), Provider interface and the shared OpenAI-compatible provider implementation.…, current_llm_operation_id(), active_rate_limit_backoff(), classify_ai_error_reason(), _effective_status_code(), _error_fields() (+44 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.09
Nodes (44): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), format_html_market_report(), format_rich_market_report(), market_report_change_chart() (+36 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.14
Nodes (33): Payment, build_premium_invoice_payload(), sqlalchemy_pool, AsyncNoop, build_session(), build_session_factory_for_concurrency(), create_user(), FakeMessage (+25 more)

### Community 9 - "common.py"
Cohesion: 0.12
Nodes (27): decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, Edit a transient callback screen without exposing Telegram failures., Best-effort deletion of a user's slash command in a private chat. (+19 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.17
Nodes (49): build_admin_llm_diagnostics_text(), build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health., builtins, build_session_factory(), _event_analysis(), _final_failed_alert() (+41 more)

### Community 12 - "test_openai_budget.py"
Cohesion: 0.15
Nodes (29): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., OpenAIBudget, OpenAIBudgetExhausted, RuntimeError, OpenAI was skipped before HTTP because safe authorization was unavailable., pytest_asyncio, budget_db() (+21 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.04
Nodes (74): alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.…, SeverityEvaluation (+66 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.15
Nodes (23): BudgetLease, _Charge, GroqBudget, GroqBudgetExhausted, datetime, Conservative zero-cost Groq admission control, shared across all call types. A…, Test-only reset; production restarts reload persisted usage., asyncio (+15 more)

### Community 15 - "BundleWriter"
Cohesion: 0.12
Nodes (12): BundleWriter, Any, Path, Publish the manifest only after its complete JSON payload is on disk., sha256_file(), sha256_tree(), utc_stamp(), write_json() (+4 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.15
Nodes (35): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), BundleHasher, _content_fingerprints() (+27 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.13
Nodes (40): ask_event_analysis_raw(), _configure(), ContentProvider, _empty_report_news_context(), _grounded_alert(), _grounding_market(), _grounding_schema_check(), _install_report_inputs() (+32 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.19
Nodes (31): _affected_users(), _alert_quality(), _collector_next_action(), _collector_status_table(), _count_pct(), _data_completeness(), _data_sources(), _decision_reasons() (+23 more)

### Community 19 - "domain/premium.py"
Cohesion: 0.17
Nodes (29): _as_aware_utc(), can_deliver_market_heartbeat_now(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active() (+21 more)

### Community 20 - "normalize_symbol"
Cohesion: 0.06
Nodes (56): _automatic_market_check_job_name(), _build_event_analysis_id(), _build_event_instance_key(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _event_instance_bucket(), _stable_float(), _candidate_news_relevance_label() (+48 more)

### Community 21 - "test_event_analysis_cloudflare_schema.py"
Cohesion: 0.09
Nodes (35): Update a usage row when downstream JSON schema validation fails., Save one LLM usage telemetry row., save_llm_usage_log(), update_llm_usage_log_status(), ask_event_significance_raw(), Return JSON mode and provider-specific schemas for verified model attempts., _structured_response_formats(), llm_operation_scope() (+27 more)

### Community 22 - "cli.py"
Cohesion: 0.08
Nodes (58): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+50 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.23
Nodes (13): add_delivery(), delivery_db(), asyncio, test_delayed_success_uses_completion_not_reservation(), test_event_resets_timer_during_generation_market_fetch(), market(), test_fresh_cache_avoids_generation_market_fetch(), test_latest_success_is_ordered_by_delivery_not_reservation() (+5 more)

### Community 24 - "LlmUsageLog"
Cohesion: 0.20
Nodes (25): LlmUsageLog, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider…, Compute 24h terminal outcomes. Raises on DB errors; never returns fake OK., read_logical_llm_health(), _state() (+17 more)

### Community 25 - "event_text.py"
Cohesion: 0.04
Nodes (98): _action_price_levels_supported(), _action_without_negated_technical_levels(), compact_event_alert_possible_action(), compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback() (+90 more)

### Community 26 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 27 - "ai_agent_groq.py"
Cohesion: 0.05
Nodes (43): asyncpg, compact_elapsed_since(), bot_services, ask_market_heartbeat_raw(), build_event_analysis_prompt(), build_market_heartbeat_prompt(), build_market_report_prompt(), _event_alert_render_market_metrics() (+35 more)

### Community 28 - "test_product_analytics.py"
Cohesion: 0.07
Nodes (58): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+50 more)

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "health_response"
Cohesion: 0.07
Nodes (27): health_response(), handle_health(), Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _clean_state(), asyncio, test_a_slow_database_degrades_the_block_instead_of_stalling_health() (+19 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.07
Nodes (72): audit(), positive_age_minutes(), ranking(), main(), _number(), _time(), _aggregate_markdown(), _cli() (+64 more)

### Community 33 - "detectors.py"
Cohesion: 0.11
Nodes (35): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+27 more)

### Community 34 - "user.py"
Cohesion: 0.42
Nodes (8): DEFAULT_TYPE, Update, General user command handlers., Best-effort product measurement that never exposes deep-link data to users., _record_start_analytics(), start(), _start_payload(), user_id()

### Community 35 - "schedule_report_cache_generation"
Cohesion: 0.27
Nodes (7): schedule_report_cache_generation(), Market report use-case entrypoints., generate_daily_report_cache_job(), generate_weekly_report_cache_job(), One recovery attempt after a scheduled failure; no recurring retry storm., _schedule_failed_report_retry(), test_report_cache_scheduler_replaces_weekly_direct_send_and_strong_signal()

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.17
Nodes (33): reports(), _build_report_telegram_message(), get_or_generate_report(), One shared refresh on old content; never fan out LLM/RSS per recipient., send_daily_report_message(), AsyncClock, build_session_factory(), _daily_message() (+25 more)

### Community 37 - "_event_significance_prompt_payload"
Cohesion: 0.10
Nodes (25): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Ground-truth evidence and limitations, Read-only local check, Versioned artifacts, build_event_significance_prompt(), _event_significance_prompt_payload(), Return the small always-on model view used only for significance. (+17 more)

### Community 38 - "logging"
Cohesion: 0.08
Nodes (47): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports(), _collect_secret_values() (+39 more)

### Community 39 - "LLMRouter"
Cohesion: 0.14
Nodes (60): api_key_env(), AIProviderRateLimitError, Raised when a provider refuses a request because the account is rate limited., LLMRouter, Startup configuration log, _call(), _call_validated(), _configure() (+52 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.04
Nodes (76): EventAnalysisDecision, _event_input_hash(), _event_instance_key_for_decision(), _raw_event_key_from_payload(), _semantic_family_from_payload(), _stable_related_news_ids(), _as_news_only_rejected_decision(), _decision_describes_market_event() (+68 more)

### Community 42 - "MarketReportDecision"
Cohesion: 0.19
Nodes (13): MarketReportDecision, _build_daily_report_message(), _build_weekly_report_message(), _format_report_coin_watchpoints(), _format_weekly_breadth(), Bound LLM verbosity without replacing or manufacturing market claims., One price/change table, plus model watchpoints with no repeated quotes., Non-repeated per-coin watchpoints carry useful weekly analysis. (+5 more)

### Community 43 - "Observability Snippets"
Cohesion: 0.10
Nodes (21): consecutive_failures(), CCW-50 Event Alert reliability signals (2026-11), Compact admin LLM overview, Duplicate/Suppressed Analysis, Event Alert Exact Context Reuse, Event Alert LLM Cadence Estimate, Event Alert section diagnostics and on-demand heartbeat cache, Event Alerts With Market Events (+13 more)

### Community 44 - "select"
Cohesion: 0.06
Nodes (95): get_analysed_window_minutes(), _build_event_analysis_input(), _get_or_create_event_alert_market_event(), _get_previous_event_alert_for_input(), attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery() (+87 more)

### Community 45 - "bot/news.py"
Cohesion: 0.09
Nodes (47): _alert_news_rank(), Impact dominates primary tags; direct relevance resolves close rankings., _collapse_whitespace(), make_news_key(), _normalize_news_link(), Normalize repeated spaces so keys stay stable across feed formatting., Return a stable URL string for news identity checks., Build a stable key for a news item. Links are preferred because RSS titles can… (+39 more)

### Community 46 - "ProviderResult"
Cohesion: 0.12
Nodes (23): ABC, BaseProvider, ProviderResult, Normalized successful chat-completion result returned by every provider., Common interface for all LLM providers., True when this provider has all configuration required for an attempt., Run one chat completion and return a :class:`ProviderResult` on success.…, Provider-agnostic LLM error types shared across the provider router. These were… (+15 more)

### Community 47 - "news_intelligence_service.py"
Cohesion: 0.11
Nodes (32): ask_news_intelligence_raw(), _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text(), _dedup_hint_is_specific_to_title() (+24 more)

### Community 48 - "db/news.py"
Cohesion: 0.10
Nodes (33): LlmOperationOutcome, SeenNews, AsyncSession, Persist one sanitized terminal outcome for a logical LLM operation., save_llm_operation_outcome(), cleanup_seen_news(), count_recent_news_intelligence_llm_calls(), get_cached_news_item_analysis() (+25 more)

### Community 50 - "router.py"
Cohesion: 0.08
Nodes (43): bot_services_llm, CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions…, get_provider(), GroqProvider, Groq provider (primary). OpenAI-compatible chat-completions API., get_provider() (+35 more)

### Community 51 - "ccw47_runner.py"
Cohesion: 0.10
Nodes (20): pct(), Path, quality(), sha(), canonical(), compact(), execute(), load() (+12 more)

### Community 52 - "test_event_alert_render_provider_chain.py"
Cohesion: 0.15
Nodes (31): ask_event_alert_render_raw(), OpenAIProvider, call_render(), FakeProvider, good_render(), input_payload(), install(), patch_significance_and_storage() (+23 more)

### Community 53 - "test_event_analysis_health.py"
Cohesion: 0.10
Nodes (27): _log_event_analysis_failure(), Log global Event Analysis degradation without changing its historical contract., bot_observability, evaluate_state(), failure_escalation_threshold(), max_success_age_seconds(), datetime, In-process health signal for Event Analysis. Event Alerts were fully dead for… (+19 more)

### Community 54 - "_create_event_analysis_decision"
Cohesion: 0.07
Nodes (68): _create_event_analysis_decision(), _render_schema_check(), _significance_schema_check(), _event_alert_render_result_for_validation(), _event_alert_render_validation_reason(), _event_market_decision_detail(), _get_previous_event_alert_id(), _normalize_render_section_labels() (+60 more)

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
Nodes (45): AlertRecipient, _automatic_delivery_lock(), _count_suppression(), _deliver_market_event_alert(), _delivery_error_class_name(), _disable_recipient_if_bot_blocked(), EventRecipientFilterResult, _filter_event_recipients_for_cooldown() (+37 more)

### Community 59 - "test_price_service.py"
Cohesion: 0.15
Nodes (20): get_coin_market_data_batch(), get_coin_price(), Get current coin price and 24h change from CoinGecko. Unsupported symbols raise…, Fetch market data for supported symbols with one CoinGecko request. Missing…, _set_cached_price(), clean_price_caches(), clear_price_caches(), isolate_http_client_construction() (+12 more)

### Community 60 - "system_status.py"
Cohesion: 0.09
Nodes (43): _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, _container_started_at(), _delivery_failure_category(), _delivery_health() (+35 more)

### Community 61 - "test_bundle_and_cli.py"
Cohesion: 0.06
Nodes (39): BundleSizeLimitError, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., OpsAgentConfig, OpsAgentLimits, Path, _collect_args(), MonkeyPatch (+31 more)

### Community 62 - "RichDeliveryUncertain"
Cohesion: 0.11
Nodes (12): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert() (+4 more)

### Community 63 - "test_gram_render_prompt_reliability.py"
Cohesion: 0.11
Nodes (18): bot, _log_event_news_trace(), Log one shared prepared payload, never validation attempts or recipient data., Replay published CCW-20 final-copy candidates offline through actual assembly.…, _recorded_candidate_pairs(), test_ccw20_replay_all_20_recorded_candidate_final_pairs_without_llm_calls(), asyncio, parametrize (+10 more)

### Community 64 - "LLMRateLimitBackoffActive"
Cohesion: 0.11
Nodes (24): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., LLMRateLimitBackoffActive, Raised when a provider/model is already in temporary rate-limit backoff., GeminiProvider (+16 more)

### Community 65 - "RedactionReport"
Cohesion: 0.06
Nodes (64): dataclasses, ops_agent, _collect_alert_repetition_rows(), collect_db(), _collector_error(), _jsonable(), Any, Exception (+56 more)

### Community 66 - "button_router"
Cohesion: 0.13
Nodes (21): button_router(), DEFAULT_TYPE, Update, build_admin_alert_settings_keyboard(), build_interval_keyboard(), AsyncFalse, AsyncTrue, _callback_update() (+13 more)

### Community 67 - "validate_event_significance_output"
Cohesion: 0.18
Nodes (15): empirical_absolute_move_percentile(), EventSignificanceDecision, Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., validate_event_significance_output(), _payload(), parametrize, test_empirical_absolute_move_percentile_returns_none_for_insufficient_or_missing_data() (+7 more)

### Community 68 - "_send_alert_to_recipient_once"
Cohesion: 0.14
Nodes (19): _delivery_retry_delay_seconds(), _is_permanent_telegram_delivery_error(), _is_transient_telegram_delivery_error(), Application, BaseException, Exactly one confirmed send per attempt. No fallback after uncertain acceptance., Send with retries; returns (sent, error_message, last_exception). The exception…, _retry_after_seconds() (+11 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "event_analysis.py"
Cohesion: 0.07
Nodes (72): CanonicalEventKey, canonicalize_event_key(), _claim_clause(), _claimed_percent(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal() (+64 more)

### Community 71 - "CCWBot"
Cohesion: 0.11
Nodes (19): CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables, Features (+11 more)

### Community 72 - "llm/config.py"
Cohesion: 0.09
Nodes (29): api_key(), base_url(), event_analysis_operation_budget_seconds(), _format_chain(), is_thinking_model(), _model_from_env(), openai_enabled(), provider_is_configured() (+21 more)

### Community 73 - "replay_event_significance.py"
Cohesion: 0.09
Nodes (31): _groq_json_mode_enabled(), scripts, classify_replay_error(), effort_budget(), groq_significance_response_format(), live_report(), load_cases(), NonObjectSignificanceError (+23 more)

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

### Community 78 - "openai_costs.py"
Cohesion: 0.15
Nodes (28): _amount(), CostsDataError, _fetch(), format_costs_screen(), InternalCosts, _official_trends(), _parse_page(), ProviderCosts (+20 more)

### Community 79 - "news_service.py"
Cohesion: 0.13
Nodes (23): headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Low-cost, word-boundary-aware prefilter; not an alert decision., Bound provider latency/response size; parse only successfully fetched bytes., Return one usable publisher feed; never fetch the mirror on primary success. (+15 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.21
Nodes (38): NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap(), build_session(), FakeNewsLlm, asyncio (+30 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "datetime"
Cohesion: 0.05
Nodes (52): argparse, concurrent_futures, datetime, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., Audit only aggregated benchmark budget and next-call feasibility (no inference). (+44 more)

### Community 83 - "json"
Cohesion: 0.03
Nodes (44): collections, csv, json, math, Model identifiers the shipped bot defaults to, for drift detection. The ops-…, pathlib, re, CCW-25: bounded read-only aggregate collection; never exports prompts or IDs. (+36 more)

### Community 84 - "log"
Cohesion: 0.05
Nodes (73): AbstractEventLoop, aiohttp, AppRunner, asyncio, cleanup_seen_news_job(), DEFAULT_TYPE, schedule_market_heartbeat_generation(), schedule_seen_news_cleanup() (+65 more)

### Community 85 - "CCW-20 paired final messages"
Cohesion: 0.09
Nodes (21): 10. ev_3c7f3da2e73e4b90 — ETH, 11. ev_7804adc277bd3333 — GRAM, 12. ev_345fc49db8255adf — GRAM, 13. ev_7b3325d2f2609480 — GRAM, 14. ev_1b39a518ede3c14f — GRAM, 15. ev_6500c5ad9f5364bc — GRAM, 16. ev_4bba21dd01bc8372 — SOL, 17. ev_1ea4cea05b78ed5c — SOL (+13 more)

### Community 86 - "event_chart.py"
Cohesion: 0.14
Nodes (20): ChartResult, _connectable_now_segment(), _display_marker_label(), _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw (+12 more)

### Community 87 - "test_llm_config_budgets.py"
Cohesion: 0.11
Nodes (34): log_resolved_configuration(), max_tokens_for(), Resolve the completion-token budget for a call type. The current ``LLM_*`` name…, Log the resolved LLM configuration once, at startup. This is the signal that…, parametrize, Per-call-type token budgets, reasoning effort, loud env parsing, and the…, _startup_log_messages(), test_bad_value_warns_once_not_once_per_call() (+26 more)

### Community 88 - "test_watchlist_ux.py"
Cohesion: 0.08
Nodes (34): build_subscribe_message(), build_watchlist_message(), build_watchlist_render(), AsyncFalse, AsyncNoop, AsyncTrue, CallbackQuery, FakeMessage (+26 more)

### Community 89 - "CCW-47 Final Event Significance Prompt Comparison"
Cohesion: 0.08
Nodes (23): CCW-47 Final Event Significance Prompt Comparison, confidence, Coverage and per-coin decisions, Decision differences, Distributions, Eight owner-ambiguous cases (excluded from scoring), Final recommendation, Focused error analysis (+15 more)

### Community 90 - "Context Audit Report"
Cohesion: 0.07
Nodes (18): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+10 more)

### Community 91 - "_fixture"
Cohesion: 0.07
Nodes (35): Clear all breaker state (tests and controlled restarts)., reset_breakers(), _real_socket, socket, _guarded_create_connection(), _guarded_getaddrinfo(), _GuardedSocket, _is_loopback() (+27 more)

### Community 92 - "watchlist.py"
Cohesion: 0.18
Nodes (26): build_my_plan_keyboard(), build_user_settings_message(), build_user_settings_render(), _current_telegram_user_id(), edit_myplan_message(), edit_user_settings_message(), edit_watchlist_message(), _format_date() (+18 more)

### Community 93 - "refresh_report_cache_scheduled"
Cohesion: 0.30
Nodes (14): _is_report_provider_backoff_active(), Scheduled cache refresh: regenerate unless the cache stays fresh past the grace…, refresh_report_cache_scheduled(), _cached_report(), asyncio, Scheduled report cache refresh: cadence, grace window, and explicit skip…, test_daily_cache_fresh_by_seconds_at_fire_time_regenerates(), test_expired_weekly_cache_triggers_regeneration() (+6 more)

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.15
Nodes (12): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Event Alert degradation counters (CCW-50), Log pattern counting (+4 more)

### Community 96 - "collections_abc"
Cohesion: 0.09
Nodes (4): downgrade(), _is_sqlite(), upgrade(), collections_abc

### Community 97 - "_build_event_alert_payload"
Cohesion: 0.07
Nodes (47): classify_news_relevance(), filter_news_for_symbol(), _is_clearly_market_wide_news(), _log_news_selection_summary(), Use article evidence for direct and substantive market-wide relevance., _build_event_alert_html_message(), _build_event_alert_payload(), _event_news_shortlist_limit() (+39 more)

### Community 98 - "test_event_alert_rich_chart_ux.py"
Cohesion: 0.11
Nodes (22): prepare_chart_points(), Never extrapolate over missing time or label a partial day as 24h., Event-specific references are opt-in; Heartbeat is exactly the old chart., render_price_chart(), _observations(), asyncio, Event Alert UX, chart evidence and single-send fallback contracts., test_chart_accepts_normal_30_minute_scheduler_jitter_but_rejects_stale() (+14 more)

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

### Community 105 - "test_event_alert_historical_diagnostics.py"
Cohesion: 0.17
Nodes (23): _build_exact_event_context_fingerprint(), _payload(), parametrize, test_ccw349_invalid_headline_does_not_hide_second_valid_headline(), test_ccw349_news_priority_changes_model_visible_context_and_fingerprint(), test_exact_context_does_not_reuse_the_ambiguous_change_field_contract(), test_exact_context_ignores_previous_title_not_sent_to_model(), test_exact_context_ignores_runtime_metadata_and_normalizes_decimal_representation() (+15 more)

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

### Community 110 - "README.md"
Cohesion: 0.18
Nodes (5): Canonical ownership, Conflict resolution, No standing rules outside the repository, Repository bootstrap, Repository Source of Truth

### Community 111 - "CCW-41 Reviewer C offline audit"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C offline audit, Compare only after sealing, Prepare frozen blind packets, Review and import

### Community 112 - "ccwbot-ops-agent-mark-report-success"
Cohesion: 0.70
Nodes (4): ccwbot-ops-agent-mark-report-success script, reject(), safe_relative_path(), usage()

### Community 113 - "_RecordingProvider"
Cohesion: 0.11
Nodes (18): _CapturingClient, _CapturingCompletions, _mock_openai_admission(), _provider_payload(), asyncio, Captures the kwargs the router passes, without making any provider call., _RecordingProvider, _route() (+10 more)

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
Cohesion: 0.09
Nodes (29): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids() (+21 more)

### Community 129 - "event_identity.py"
Cohesion: 0.12
Nodes (23): AnalysedWindowReference, _calculate_price_change(), _canonical_decimal_string(), _canonical_event_analysis_context(), _event_analysis_datetime(), _event_analysis_news_age_hours(), _event_analysis_news_summary(), datetime (+15 more)

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

### Community 144 - "utc_now"
Cohesion: 0.18
Nodes (38): Record one typed event; a duplicate lifecycle key returns the original., record_product_event(), Return timezone-aware UTC timestamp., UserPremiumSubscription, UserPremiumTrial, utc_now(), activate_premium_from_telegram_stars_payment(), _activate_premium_from_telegram_stars_payment_locked() (+30 more)

### Community 145 - "payments.py"
Cohesion: 0.19
Nodes (21): build_premium_activation_keyboard(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date(), _get_payment_attr(), _is_private_update(), _is_subscribe_rate_limited() (+13 more)

### Community 146 - "test_openai_costs.py"
Cohesion: 0.26
Nodes (22): OpenAICostsMonitor, bucket(), bucket_at(), client_mock(), configured(), page(), asyncio, parametrize (+14 more)

### Community 147 - "test_news_intelligence_schema.py"
Cohesion: 0.19
Nodes (21): model_for(), Resolve the model for a (provider, call_type) pair from env, with defaults., _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), test_model_value_is_stripped(), schema_check() (+13 more)

### Community 148 - "Development"
Cohesion: 0.25
Nodes (8): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.09
Nodes (42): _build_market_heartbeat_id(), _deliver_market_heartbeat(), generate_market_heartbeats(), _is_fresh_heartbeat(), _select_related_news_context(), MarketHeartbeat, test_cache_expiring_before_lock_acquisition_is_not_sent(), test_concurrent_checks_send_one_heartbeat_and_reset_timer() (+34 more)

### Community 150 - "build_alert_evidence_payloads"
Cohesion: 0.29
Nodes (24): build_alert_evidence_payloads(), _numeric_context_json(), _period(), parametrize, _row(), test_alert_evidence_uses_hashes_without_raw_alert_text(), test_alert_quality_clean_delivered_event_alert_stays_clean(), test_alert_quality_detects_old_24h_label_in_delivered_event_alert() (+16 more)

### Community 151 - "test_heartbeat_postgres.py"
Cohesion: 0.22
Nodes (12): automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, postgres_url(), asyncio, Real PostgreSQL locking checks; the SQLite process mutex cannot prove these…, test_postgres_lock_serializes_separate_workers_and_releases_on_cancellation() (+4 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "provider_attempts"
Cohesion: 0.10
Nodes (24): global_provider_priority(), _parse_priority_list(), provider_attempts(), provider_priority(), Parse a comma-separated provider list, warning about names that are not…, Resolve the ordered provider chain for a call type. Per-call-type override env…, Return the ordered concrete provider/model attempts for one logical LLM…, Case schema (+16 more)

### Community 156 - "test_multicoin_alerts.py"
Cohesion: 0.13
Nodes (30): AlertRecipientResolution, _classify_news_context(), Return active market symbols independently of current recipient eligibility., resolve_symbols_to_check(), set_user_coin_subscription(), build_session_factory(), create_user(), asyncio (+22 more)

### Community 157 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 158 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 159 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 160 - "test_event_alert_reliability_diagnostics.py"
Cohesion: 0.13
Nodes (15): DbQuery, Assert every collector SQL statement is a read-only, single, unterminated…, validate_read_only_queries(), test_all_db_queries_are_read_only_and_parameterized(), test_db_collector_failure_is_isolated_and_later_collectors_continue(), _evidence(), _find(), Contract tests for sanitized CCW-50 alert degradation observability. (+7 more)

### Community 162 - "admin.py"
Cohesion: 0.13
Nodes (52): schedule_automatic_market_check(), acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_admin_llm_diagnostics_text(), _build_admin_openai_costs_text(), _build_admin_system_status_text() (+44 more)

### Community 164 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "LLMJsonResult"
Cohesion: 0.29
Nodes (5): LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., test_backward_compatible_public_api(), CorrelatedFallbackNewsLlm, tuple

### Community 169 - "test_rich_403_preserves_safe_blocked_classification_without_raw_errors"
Cohesion: 0.11
Nodes (6): parametrize, test_integrity_conflict_preserves_terminal_delivery_reservation(), test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post(), test_rich_confirmed_telegram_rejections(), post()

### Community 170 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 171 - "automatic_price_check"
Cohesion: 0.18
Nodes (19): automatic_price_check(), DEFAULT_TYPE, Update, User settings command handler., settings(), get_db_alert_settings(), get_db_error_file_logging_enabled(), get_runtime_alert_settings() (+11 more)

### Community 172 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 173 - "bot/reports.py"
Cohesion: 0.07
Nodes (55): MarketReport, get_latest_market_report(), AsyncSession, datetime, Save one cached market report generation attempt., Return the newest cached market report for a cadence., save_market_report(), _build_deterministic_report_decision() (+47 more)

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
Cohesion: 0.05
Nodes (59): alembic_script, AppSettings, Base, datetime, Database infrastructure for optional PostgreSQL runtime storage., Run Alembic migrations without blocking the active event loop., Base class for all SQLAlchemy models., run_async_upgrade() (+51 more)

### Community 178 - "test_price_handlers.py"
Cohesion: 0.32
Nodes (14): CoinGeckoRateLimitError, Exception, Raised when CoinGecko returns HTTP 429., _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users(), test_price_maps_provider_errors_to_safe_user_messages() (+6 more)

### Community 180 - "/graphify"
Cohesion: 0.09
Nodes (18): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+10 more)

### Community 181 - "report_context.py"
Cohesion: 0.25
Nodes (20): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+12 more)

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.33
Nodes (5): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps

### Community 183 - "test_news_ingestion.py"
Cohesion: 0.14
Nodes (10): _entry(), _feed(), asyncio, datetime, Regression tests for the independent, bounded RSS ingestion path., test_report_and_hourly_ingestion_share_serial_llm_budget_gate(), test_rss_merges_sources_by_publication_time_before_limit(), test_rss_source_failure_is_isolated_and_safely_counted() (+2 more)

### Community 184 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 185 - "calculate_price_change_percent"
Cohesion: 0.20
Nodes (12): calculate_price_change_percent(), is_cooldown_active(), datetime, Decimal, Core alert-rule helpers used by automatic market checks., Calculate a percent change without mixing binary floats and ``Decimal`` values., Return True while a previous alert is still inside the cooldown window., _event_alert_for_recipient() (+4 more)

### Community 186 - "0031_onboarding_customize_event.py"
Cohesion: 0.83
Nodes (3): downgrade(), _replace_event_name_check(), upgrade()

### Community 188 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 189 - "display_symbol"
Cohesion: 0.13
Nodes (33): coin_display_name(), display_symbol(), is_supported_symbol(), premium_symbols_display(), Supported coin metadata shared by price checks and Premium watchlists., supported_symbols_display(), log_custom_emoji_ids(), price() (+25 more)

### Community 190 - "resolve_alert_recipient_outcomes"
Cohesion: 0.20
Nodes (13): get_alert_recipients(), Resolve eligible recipients once for one market event., Resolve recipients and preserve queryable reasons for filtered users., RecipientOutcome, resolve_alert_recipient_outcomes(), FakeSession, asyncio, test_event_alert_eligibility_ignores_market_heartbeat_preference() (+5 more)

### Community 192 - "test_exhausted_provider_chain_uses_verified_data_fallback"
Cohesion: 0.50
Nodes (5): asyncio, parametrize, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload()

### Community 193 - "User"
Cohesion: 0.12
Nodes (36): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), User, backfill_blocked_users_from_alerts(), get_active_users_with_alert_preferences(), get_active_users_with_chat_ids(), get_or_create_user() (+28 more)

### Community 194 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 195 - "handlers/reports.py"
Cohesion: 0.39
Nodes (7): daily_report(), DEFAULT_TYPE, Update, Market report command handlers., weekly_report(), send_weekly_report_message(), Models, token budgets, and reasoning effort

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
Nodes (18): Return the fully resolved per-call-type LLM configuration. Model identifiers,…, resolved_configuration(), _cost(), monthly_budget_usd(), OpenAIBudgetLease, _positive_decimal_env(), pricing_usd_per_million(), datetime (+10 more)

### Community 206 - "Repository-backed Graphify"
Cohesion: 0.33
Nodes (5): Clones and local development, Repository-backed Graphify, Retention, Shared state in dev, Updates after migration

### Community 207 - "CCW-25 research evidence"
Cohesion: 0.40
Nodes (4): Billing assumptions, CCW-25 research evidence, Interpretation limits, Reproduce

### Community 208 - "datetime"
Cohesion: 0.13
Nodes (18): _build_market_heartbeat_input(), _compact_event_snapshot(), _compact_event_snapshots(), _load_news_driven_alert_candidates(), _parse_state_alert_at(), _prepare_event_alert_chart(), datetime, Build one shared PNG before fanout. No recipient data enters this image. (+10 more)

### Community 209 - "operator_prompt.md"
Cohesion: 0.40
Nodes (4): CCW-41 Reviewer C operator prompt, CCW-41 Reviewer C significance rubric v1, Frozen output schema, Frozen rubric

### Community 210 - "graphify reference: extra exports and benchmark"
Cohesion: 0.20
Nodes (9): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000) (+1 more)

### Community 213 - "Provider fallback (redundancy)"
Cohesion: 0.17
Nodes (11): Admin OpenAI Platform Costs monitoring (optional, read-only), Current Event Alert Luna-only policy (owner update 2026-10-29), Event Analysis timeout and operation budget, Groq free-tier admission control (Event Analysis), Historical CCW-20 Event Alert provider order (superseded), Historical Gemini 429 quota classification and backoff, LLM Usage Reporting, Ops-Agent LLM Usage Evidence (+3 more)

### Community 214 - "price_service.py"
Cohesion: 0.17
Nodes (20): _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), get_btc_market_data(), get_btc_price(), _get_cached_price(), _get_stale_cached_price(), _get_with_retry() (+12 more)

### Community 217 - "0026_growth_analytics.py"
Cohesion: 0.90
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 222 - "get_int_env"
Cohesion: 0.13
Nodes (18): _get_int_env(), Substrings that mark a model identifier as reasoning-capable (overridable via…, reasoning_model_markers(), get_choice_env(), get_int_env(), _is_secret_name(), _looks_like_secret_value(), Environment parsing helpers for the LLM subsystem that fail loudly. The… (+10 more)

### Community 223 - "build_review.py"
Cohesion: 0.32
Nodes (11): candidate(), canon(), context(), csvwrite(), main(), Private read-only CCWBot market benchmark and independent review CSV exporter., run_psql(), safe() (+3 more)

### Community 224 - "0027_market_heartbeat_defaults.py"
Cohesion: 0.70
Nodes (4): downgrade(), _has_alert_frequency_column(), _set_default(), upgrade()

### Community 225 - "render_decision_report_context"
Cohesion: 0.25
Nodes (18): _display_detector_status(), datetime, render_decision_report_context(), _report_status(), _unknown_section(), DetectorResult, Any, _period() (+10 more)

### Community 226 - "0004_multicoin_delivery_idempotency.py"
Cohesion: 0.83
Nodes (3): downgrade(), _unique_constraint_names(), upgrade()

### Community 227 - "_build_market_heartbeat_payload"
Cohesion: 0.10
Nodes (26): Escape all model/news wording; only safely link explicit HTTP(S) sources., _report_coin_icon_html(), _safe_rich_line(), _build_event_alert_rich_html(), _build_market_heartbeat_html_message(), _build_market_heartbeat_payload(), _build_market_heartbeat_rich_html(), _coin_fallback_emoji() (+18 more)

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

### Community 236 - "reasoning_effort_for"
Cohesion: 0.12
Nodes (19): effective_max_tokens_for(), is_reasoning_model(), Return the completion budget for one concrete provider attempt. The public…, True when this model identifier is known to accept ``reasoning_effort``., Resolve ``reasoning_effort`` for a (model, call_type) pair, or ``None`` when…, reasoning_effort_for(), test_replay_budget_respects_groq_free_tier(), test_builtin_reasoning_markers_survive_legacy_extension_value() (+11 more)

### Community 237 - "test_ai_agent_groq.py"
Cohesion: 0.15
Nodes (12): ask_market_report_raw(), Keep user-visible LLM text concise and remove accidental diagnostic lines., sanitize_alert_message(), _set_groq_client(), test_event_alert_render_schema_only_contains_model_generated_fields(), test_event_analysis_prompt_makes_llm_the_market_significance_decider(), test_event_analysis_raw_uses_strict_groq_schema_and_returns_provider_attribution(), test_event_analysis_unknown_groq_model_keeps_json_object_mode() (+4 more)

### Community 238 - "db/prices.py"
Cohesion: 0.27
Nodes (16): _save_price_state(), PriceSnapshot, PriceState, UserSymbolAlertState, get_price_snapshots_since(), get_price_state(), get_reference_price_snapshot(), get_user_symbol_alert_state() (+8 more)

### Community 239 - "handle_watchlist_callback"
Cohesion: 0.24
Nodes (11): handle_watchlist_callback(), build_session(), create_user(), FakeQuery, asyncio, parametrize, SessionContext, test_legacy_frequency_callback_rerenders_current_settings() (+3 more)

### Community 240 - "FakeResponse"
Cohesion: 0.17
Nodes (8): post(), FakeClient, FakeResponse, test_get_coin_price_429_triggers_retry(), __init__(), test_get_with_retry_can_disable_stale_cache_after_429_retries(), test_get_with_retry_returns_stale_cache_after_429_retries(), test_get_with_retry_sends_demo_api_key()

### Community 241 - "test_observability_reconciliation.py"
Cohesion: 0.26
Nodes (10): _payload(), _period(), Regression contracts for sanitized ops-agent evidence and report denominators., _row(), test_disjoint_recipients_do_not_trigger_global_family_cooldown(), test_docker_health_summary_uses_sanitized_collector_contract(), test_failed_delivery_does_not_create_sent_cooldown_violation(), test_missing_recipient_evidence_is_unknown_not_healthy() (+2 more)

### Community 242 - "test_event_alert_24h_now_continuity.py"
Cohesion: 0.27
Nodes (11): bot_alerting, pil, decision(), history(), market_payload(), Event Alert metric/title and true observed NOW continuity regressions., test_24h_metric_and_unambiguous_header_in_all_delivery_formats(), test_now_connection_draws_real_segment_inside_chart_plot() (+3 more)

### Community 243 - "AIInvalidJsonError"
Cohesion: 0.18
Nodes (7): AIInvalidJsonError, datetime, Exception, RuntimeError, Raised when the provider response is not valid JSON., Circuit breaker, _validate()

### Community 244 - "clean_news_title"
Cohesion: 0.36
Nodes (9): _format_event_related_context(), _format_market_heartbeat_related_context(), _format_related_context(), _safe_telegram_link_url(), clean_news_title(), clean_related_news_text(), test_clean_news_title_preserves_non_matching_titles(), test_clean_news_title_removes_known_source_suffixes() (+1 more)

### Community 246 - "CCW-12 matched Luna significance comparison"
Cohesion: 0.40
Nodes (4): CCW-12 matched Luna significance comparison, Changed binary decisions, Limits, Matched comparison

### Community 247 - "telegram_error"
Cohesion: 0.31
Nodes (8): handle_application_error(), Global python-telegram-bot error handler. Log-only: never sends anything to…, telegram_error, asyncio, parametrize, Global PTB error handler: concise WARNING for transient network errors, ERROR…, test_non_network_error_logs_error_with_traceback(), test_transient_network_error_logs_one_concise_warning()

### Community 248 - "TransientBot"
Cohesion: 0.33
Nodes (6): Intercept only messages sent in the scope of a manual command/callback., _tracking(), TransientBot, with_close_button(), ExtBot, test_close_markup_preserves_other_actions_and_does_not_duplicate()

### Community 249 - "test_rich_chart_quality_detector.py"
Cohesion: 0.36
Nodes (8): _quality_issues(), test_optional_related_news_is_not_telegram_quality_failure(), _issues(), Regressions for rich Telegram charts persisted as plain alternatives., test_exact_chart_fallback_is_not_a_quality_failure_for_rich_alerts(), test_heartbeat_unavailable_is_not_suppressed_by_event_alert_exception(), test_other_placeholders_and_old_labels_remain_detectable(), test_other_unavailable_text_is_still_flagged()

### Community 250 - "get_report_market_data_batch"
Cohesion: 0.29
Nodes (8): _extract_sparkline_prices(), get_report_market_data_batch(), _optional_float(), _optional_int(), _range_position(), Fetch richer market data for cached daily/weekly reports. This intentionally…, test_get_report_market_data_batch_keeps_btc_alert_cache_unchanged(), test_get_report_market_data_batch_uses_markets_endpoint()

### Community 251 - "Event Alert cadence evaluation — CCW-50 (2026-11-06)"
Cohesion: 0.29
Nodes (6): Decision, Event Alert cadence evaluation — CCW-50 (2026-11-06), Follow-up decision gates, Hypothetical comparison — not a historical replay, Reproducible baseline, What this can and cannot establish

### Community 252 - "test_growth_analytics_migration.py"
Cohesion: 0.47
Nodes (5): alembic_config, _alembic_config(), Config, test_growth_analytics_upgrade_backfills_existing_users(), test_premium_trials_upgrade_preserves_existing_premium_and_payment_rows()

### Community 253 - "Documentation"
Cohesion: 0.33
Nodes (5): Core, Development and operations, Documentation, Research, What is intentionally not here

### Community 254 - "schedule_automatic_btc_check"
Cohesion: 0.40
Nodes (3): Compatibility wrapper for older imports; schedules the market-wide check., schedule_automatic_btc_check(), test_legacy_automatic_btc_scheduler_alias_uses_market_job_name()

### Community 255 - "_extract_ton_coin_data_from_simple_price"
Cohesion: 0.50
Nodes (4): _extract_ton_coin_data_from_simple_price(), Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., test_ton_simple_price_extractor_accepts_only_current_gram_id(), test_ton_simple_price_extractor_rejects_arbitrary_symbol_candidates()

## Knowledge Gaps
- **467 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+462 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1788 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `unknown` to `test_event_alert_rich_chart_ux.py`, `Observability Snippets`, `CCWBot Ops-Agent Report Analysis`, `RichDeliveryUncertain`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `test_event_alert_rich_chart_ux.py`, `unknown`, `_send_alert_to_recipient_once`, `test_rich_market_report_delivery.py`, `bot/alerts.py`, `bot/reports.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `select()` connect `select` to `onboarding.py`, `test_telegram_stars_payments.py`, `test_system_status.py`, `test_openai_budget.py`, `test_groq_budget.py`, `utc_now`, `test_news_intelligence_schema.py`, `test_market_heartbeat.py`, `test_event_analysis_cloudflare_schema.py`, `LlmUsageLog`, `test_product_analytics.py`, `test_multicoin_alerts.py`, `test_report_cooldowns.py`, `test_event_alert_pipeline.py`, `bot/reports.py`, `bot/news.py`, `news_intelligence_service.py`, `db/news.py`, `database.py`, `router.py`, `_deliver_market_event_alert`, `system_status.py`, `User`, `openai_budget.py`, `openai_costs.py`, `test_news_intelligence_service.py`, `build_review.py`, `db/prices.py`, `handle_watchlist_callback`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 170 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 170 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _467 weakly-connected nodes found - possible documentation gaps or missing edges._