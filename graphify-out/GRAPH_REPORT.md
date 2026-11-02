# Graph Report - CCWBot  (2026-11-02)

## Corpus Check
- 658 files · ~1,155,697 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 34 file(s) not represented in the graph (top: .toml 12, (none) 8, .csv 7)

## Summary
- 5889 nodes · 17408 edges · 225 communities (190 shown, 35 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1448 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `92864023`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- json
- llm/config.py
- onboarding.py
- test_db_queries_and_detectors.py
- test_llm_breaker.py
- telemetry.py
- test_rich_market_report_delivery.py
- test_telegram_stars_payments.py
- logging
- test_system_status.py
- sqlalchemy
- test_openai_budget.py
- bot/alerts.py
- test_groq_budget.py
- log
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- event_alert_benchmark.py
- test_event_alert_message_quality.py
- test_event_alert_historical_diagnostics.py
- cli.py
- test_heartbeat_silence.py
- LlmUsageLog
- event_text.py
- properties
- test_event_analysis_cloudflare_schema.py
- test_product_analytics.py
- validate_market_report_output
- properties
- openai_costs.py
- ccw41_reviewer_c_audit.py
- detectors.py
- admin.py
- hashlib
- test_report_cooldowns.py
- Provider fallback (redundancy)
- error_file_logging.py
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- canonicalize_event_key
- Observability Snippets
- select
- bot/news.py
- AIProviderRateLimitError
- news_intelligence_service.py
- make_news_key
- bootstrap.py
- router.py
- _CapturingCompletions
- test_event_alert_render_provider_chain.py
- domain/premium.py
- test_event_alert_render_reliability.py
- test_llm_outage_detectors.py
- manifest.json
- CCWBot Growth Strategy: 0 -> 1 Premium
- User
- price_service.py
- system_status.py
- test_bundle_and_cli.py
- RichDeliveryUncertain
- test_event_analysis_health.py
- test_news_intelligence_schema.py
- RedactionReport
- button_router
- test_event_alert_postrelease_regressions.py
- test_openai_costs.py
- 0001_initial_schema.py
- validate_event_significance_output
- CCWBot
- BundleWriter
- replay_event_significance.py
- 0024_gram_symbol.py
- test_event_alert_composition_investigation.py
- test_agent_workflow_contract.py
- test_event_alert_delivery_quality_regressions.py
- test_report_content_rich_and_llm_summary.py
- test_news_ingestion.py
- test_news_intelligence_service.py
- CCWBot Ops-Agent Report Analysis
- datetime
- event_analysis.py
- supported_coins.py
- CCW-20 paired final messages
- event_chart.py
- openai_budget.py
- test_watchlist_ux.py
- test_event_alert_owner_copy_news_regressions.py
- Context Audit Report
- _fixture
- watchlist.py
- refresh_report_cache_scheduled
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- test_event_alert_render_grounded_copy.py
- test_event_alert_24h_now_continuity.py
- test_event_alert_rich_chart_ux.py
- Ops-Agent Service
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- _build_exact_event_context_fingerprint
- settings
- test_event_alert_chart_markers.py
- test_price_service.py
- Event Alert logic
- Documentation
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
- database.py
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
- conftest.py
- TransientSessions
- benchmark.py
- Development
- test_market_heartbeat.py
- ai_agent_groq.py
- test_llm_config_budgets.py
- ChatGPT / Bridge / Codex Workflow
- provider_attempts
- collectors/__init__.py
- ops_agent/__init__.py
- automatic_price_check
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- schemas.py
- graphify reference: GitHub clone and cross-repo merge
- callbacks.py
- pkgutil
- test_heartbeat_does_not_query_previous_event
- reviewer-c-rubric.md
- What You Must Do When Invoked
- extraction-spec.md
- test_alembic_migrations.py
- asyncio
- CCW-41 exploratory Reviewer-C agreement/disagreement
- TransientBot
- 0008_database_comments.py
- bot/reports.py
- _runner_private.py
- _StructuredRecordBuffer
- types
- runtime/state.py
- test_price_handlers.py
- FakeAsyncClient
- /graphify
- normalize_symbol
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- utc_now
- CCW-43 — Evidence-based Event Analysis prompt redesign
- unittest_mock
- test_news_driven_alerts.py
- check_owner_html.py
- 0025_llm_operation_correlation.py
- news_context.py
- _validate_event_alert_render_causality
- .__init__
- LLMRateLimitBackoffActive
- Repository Source of Truth
- CCWBot Operational Report — Unverified (No Production Bundle)
- test_transport_reuses_file_id_and_handles_valid_response
- score_economical_200.py
- CCW-25 — Self-hosted LLM owner decision
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- CCWBot — blind owner disagreement-only replay
- test_exact_context_reuse_recanonicalizes_and_rerenders_market_context
- Repository-backed Graphify
- CCW-25 research evidence
- operator_prompt.md
- graphify reference: extra exports and benchmark
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- handlers/reports.py
- _build_weekly_report_message
- README_RU.md
- CCW-20 — Offline safety correction of retained Cloudflare final texts
- fresh200_luna_wait_start.sh
- openai_luna_wait_start.sh
- build_review.py
- CCW20_FINAL_MESSAGE_BASELINE_20261026.md
- convert_human_reviews.py
- pytest

## God Nodes (most connected - your core abstractions)
1. `select()` - 173 edges
2. `Period` - 115 edges
3. `Base` - 100 edges
4. `LLMRouter` - 98 edges
5. `normalize_symbol()` - 89 edges
6. `EventAnalysisValidationError` - 69 edges
7. `User` - 68 edges
8. `utc_now()` - 64 edges
9. `run_detectors()` - 64 edges
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

## Communities (225 total, 35 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.13
Nodes (50): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), alert_analysis_result(), event_analysis_result(), factual_market_input() (+42 more)

### Community 1 - "json"
Cohesion: 0.03
Nodes (38): collections, csv, json, math, pathlib, re, CCW-25: bounded read-only aggregate collection; never exports prompts or IDs., Package an explicit, privacy-reviewed research whitelist; no binaries or… (+30 more)

### Community 2 - "llm/config.py"
Cohesion: 0.05
Nodes (56): _get_int_env(), base_url(), event_analysis_operation_budget_seconds(), _format_chain(), is_thinking_model(), log_resolved_configuration(), _model_from_env(), openai_enabled() (+48 more)

### Community 3 - "onboarding.py"
Cohesion: 0.10
Nodes (57): ProductEvent, UserCoinSubscription, build_onboarding_customize_keyboard(), build_onboarding_keyboard(), build_premium_paywall_keyboard(), build_trial_offer_keyboard(), Premium-only onboarding selector. BTC stays as the free default during…, _as_aware_utc() (+49 more)

### Community 4 - "test_db_queries_and_detectors.py"
Cohesion: 0.04
Nodes (65): alembic_migration, alembic_operations, ops_agent_collectors, _alert_evidence_windows(), datetime, run_detectors(), Period, sqlite3 (+57 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.08
Nodes (75): _backoff_schedule(), breaker_snapshot(), _BreakerState, _failure_threshold(), is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics. (+67 more)

### Community 6 - "telemetry.py"
Cohesion: 0.07
Nodes (61): _validate(), Provider interface and the shared OpenAI-compatible provider implementation.…, LLM provider fallback package. Groq stays the primary provider; disabled-by-…, current_llm_operation_id(), new_llm_operation_id(), Async-safe correlation for one logical LLM operation. The value is an opaque…, Return an opaque identifier for exactly one logical LLM operation., Run one logical LLM call over the provider chain. ``validate_response`` is an… (+53 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.09
Nodes (42): _chart_source_rows(), compact_report_for_display(), _draw_daily_chart(), _draw_weekly_chart(), _font(), market_report_change_chart(), _percent_label(), ImageDraw (+34 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.10
Nodes (54): Payment, build_premium_activation_keyboard(), build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime(), _format_date(), _get_payment_attr() (+46 more)

### Community 9 - "logging"
Cohesion: 0.10
Nodes (27): _callback_command_update(), decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, _role_label() (+19 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.17
Nodes (49): PriceState, build_admin_llm_diagnostics_text(), build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health., builtins, build_session_factory(), _event_analysis() (+41 more)

### Community 11 - "sqlalchemy"
Cohesion: 0.03
Nodes (37): alembic, _column_names(), downgrade(), _table_names(), upgrade(), downgrade(), _unique_constraint_names(), upgrade() (+29 more)

### Community 12 - "test_openai_budget.py"
Cohesion: 0.16
Nodes (28): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., OpenAIBudget, OpenAIBudgetExhausted, RuntimeError, OpenAI was skipped before HTTP because safe authorization was unavailable., budget_db(), asyncio (+20 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.04
Nodes (93): alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.…, SeverityEvaluation (+85 more)

### Community 14 - "test_groq_budget.py"
Cohesion: 0.13
Nodes (24): BudgetLease, _Charge, GroqBudget, GroqBudgetExhausted, datetime, Conservative zero-cost Groq admission control, shared across all call types. A…, Test-only reset; production restarts reload persisted usage., GroqProvider (+16 more)

### Community 15 - "log"
Cohesion: 0.09
Nodes (31): cleanup_seen_news_job(), schedule_automatic_market_check(), schedule_market_heartbeat_generation(), schedule_report_cache_generation(), schedule_seen_news_cleanup(), Alert and heartbeat use-case entrypoints., Market report use-case entrypoints., expire_due_premium_trials() (+23 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.09
Nodes (67): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), build_alert_evidence_payloads(), BundleHasher (+59 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.12
Nodes (46): ask_event_analysis_raw(), AISchemaValidationError, Raised when validated JSON does not match the expected schema. ``raw_content``…, _configure(), ContentProvider, _empty_report_news_context(), _grounded_alert(), _grounding_market() (+38 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.07
Nodes (79): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+71 more)

### Community 19 - "event_alert_benchmark.py"
Cohesion: 0.10
Nodes (42): random, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, CCW-29 fresh private holdout: collect real POST-200 market cases via…, choose(), Freeze fresh 200 real CCWBot market cases, excluding both earlier sets;…, Local error diagnosis on frozen benchmark, no API or repo modifications., Private local compact feature comparison of benchmark model errors., blind_packet() (+34 more)

### Community 20 - "test_event_alert_message_quality.py"
Cohesion: 0.13
Nodes (26): compact_event_alert_situation(), event_alert_presentation_fallback(), Keep Event Alert explanations useful instead of repeating the metric block., Return display-only context from supplied evidence, never alert eligibility.…, parametrize, Grounded Event Alert copy: test scenarios without recipient or LLM calls., test_actual_snapshot_duration_prevents_false_pace_claim(), test_ccw20_counterstep_fallback_names_direction_and_next_observation() (+18 more)

### Community 21 - "test_event_alert_historical_diagnostics.py"
Cohesion: 0.08
Nodes (35): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Ground-truth evidence and limitations, Read-only local check, Versioned artifacts, build_event_significance_prompt(), _event_significance_prompt_payload(), Return the small always-on model view used only for significance. (+27 more)

### Community 22 - "cli.py"
Cohesion: 0.14
Nodes (30): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+22 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.15
Nodes (23): can_deliver_market_heartbeat_now(), pytest_asyncio, add_delivery(), delivery_db(), asyncio, parametrize, test_delayed_success_uses_completion_not_reservation(), test_event_resets_timer_during_generation_market_fetch() (+15 more)

### Community 24 - "LlmUsageLog"
Cohesion: 0.12
Nodes (32): LlmUsageLog, Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider… (+24 more)

### Community 25 - "event_text.py"
Cohesion: 0.08
Nodes (35): _action_without_negated_technical_levels(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), _has_final_reference_disclaimer(), _has_persistent_snapshot_direction(), _has_unsupported_action_market_claim(), is_news_centered_event_action() (+27 more)

### Community 26 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 27 - "test_event_analysis_cloudflare_schema.py"
Cohesion: 0.07
Nodes (42): ask_event_alert_render_raw(), ask_event_significance_raw(), ask_market_heartbeat_raw(), ask_market_report_raw(), ask_news_intelligence_raw(), build_event_analysis_prompt(), _json_response_validator(), _parse_json() (+34 more)

### Community 28 - "test_product_analytics.py"
Cohesion: 0.06
Nodes (62): AcquisitionAttribution, capture_first_touch_attribution(), create_acquisition_link(), _is_acquisition_link_code_collision(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence. (+54 more)

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "openai_costs.py"
Cohesion: 0.15
Nodes (28): _amount(), CostsDataError, _fetch(), format_costs_screen(), InternalCosts, _official_trends(), _parse_page(), ProviderCosts (+20 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.07
Nodes (72): audit(), positive_age_minutes(), ranking(), main(), _number(), _time(), _aggregate_markdown(), _cli() (+64 more)

### Community 33 - "detectors.py"
Cohesion: 0.11
Nodes (34): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+26 more)

### Community 34 - "admin.py"
Cohesion: 0.15
Nodes (44): build_acquisition_telegram_url(), Build a Telegram deep link only from a valid configured bot username and opaque…, acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_admin_llm_diagnostics_text(), _build_admin_system_status_text() (+36 more)

### Community 35 - "hashlib"
Cohesion: 0.06
Nodes (35): copy, hashlib, importlib_util, io, main(), Verify completed research, reconcile metrics and fill the decision reports., sha(), Stage and execute a finite, blind, genuine new-event holdout replay. No… (+27 more)

### Community 36 - "test_report_cooldowns.py"
Cohesion: 0.16
Nodes (36): MarketReport, reports(), _build_report_telegram_message(), get_or_generate_report(), Only full persisted report inputs qualify; preserve test/minimal caches., One shared refresh on old content; never fan out LLM/RSS per recipient., _report_requires_content_upgrade(), send_daily_report_message() (+28 more)

### Community 37 - "Provider fallback (redundancy)"
Cohesion: 0.17
Nodes (11): Admin OpenAI Platform Costs monitoring (optional, read-only), Current Event Alert Luna-only policy (owner update 2026-10-29), Event Analysis timeout and operation budget, Groq free-tier admission control (Event Analysis), Historical CCW-20 Event Alert provider order (superseded), Historical Gemini 429 quota classification and backoff, LLM Usage Reporting, Ops-Agent LLM Usage Evidence (+3 more)

### Community 38 - "error_file_logging.py"
Cohesion: 0.08
Nodes (48): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., bot_observability, _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports() (+40 more)

### Community 39 - "LLMRouter"
Cohesion: 0.15
Nodes (57): api_key_env(), LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider, _http_error() (+49 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.04
Nodes (104): EventAnalysisDecision, with_canonical_event_key(), _event_input_hash(), _as_news_only_rejected_decision(), _build_event_alert_html_message(), _build_event_alert_payload(), _create_event_analysis_decision(), _render_schema_check() (+96 more)

### Community 42 - "canonicalize_event_key"
Cohesion: 0.14
Nodes (24): CanonicalEventKey, canonicalize_event_key(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal(), _fallback_event_key(), _is_random_event_key() (+16 more)

### Community 43 - "Observability Snippets"
Cohesion: 0.08
Nodes (29): consecutive_failures(), Output, Rules you enforce, What you review, Admin System Status, Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis (+21 more)

### Community 44 - "select"
Cohesion: 0.05
Nodes (102): _get_or_create_event_alert_market_event(), attach_analysis_to_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery(), get_event_ai_analysis(), get_last_sent_alert(), get_last_sent_alert_at() (+94 more)

### Community 45 - "bot/news.py"
Cohesion: 0.14
Nodes (29): _dedupe_report_news(), fetch_report_news_context(), within_window(), _has_report_news_identity(), _incident_phase(), _item_link(), _item_published_at(), _item_related_symbols() (+21 more)

### Community 46 - "AIProviderRateLimitError"
Cohesion: 0.10
Nodes (34): ABC, BaseProvider, Common interface for all LLM providers., True when this provider has all configuration required for an attempt., Run one chat completion and return a :class:`ProviderResult` on success.…, api_key(), global_provider_priority(), _parse_priority_list() (+26 more)

### Community 47 - "news_intelligence_service.py"
Cohesion: 0.10
Nodes (32): Persist one sanitized terminal outcome for a logical LLM operation., save_llm_operation_outcome(), _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id(), _clamp_score(), _clean_text() (+24 more)

### Community 48 - "make_news_key"
Cohesion: 0.09
Nodes (37): _collapse_whitespace(), make_news_key(), _normalize_news_link(), Normalize repeated spaces so keys stay stable across feed formatting., Return a stable URL string for news identity checks., Build a stable key for a news item. Links are preferred because RSS titles can…, SeenNews, cleanup_seen_news() (+29 more)

### Community 49 - "bootstrap.py"
Cohesion: 0.09
Nodes (32): AbstractEventLoop, AppRunner, asyncio, bot_handlers, Application, register_bot_handlers(), start_health_server(), handle_health() (+24 more)

### Community 50 - "router.py"
Cohesion: 0.08
Nodes (41): CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions…, get_provider(), get_provider(), OpenAIProvider, OpenAI paid fallback, guarded by an explicit kill switch and durable budget., _default_registry() (+33 more)

### Community 52 - "test_event_alert_render_provider_chain.py"
Cohesion: 0.18
Nodes (21): ProviderResult, Normalized successful chat-completion result returned by every provider., call_render(), FakeProvider, good_render(), input_payload(), install(), patch_significance_and_storage() (+13 more)

### Community 53 - "domain/premium.py"
Cohesion: 0.26
Nodes (21): _as_aware_utc(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active(), is_user_trial_active() (+13 more)

### Community 54 - "test_event_alert_render_reliability.py"
Cohesion: 0.22
Nodes (18): build_event_alert_render_prompt(), _payload(), asyncio, parametrize, Regression contracts for production Event Alert Render rejection categories.…, test_ccw20_render_copy_asks_for_meaningful_price_scenarios(), test_ccw20_render_prompt_missing_context_fails_closed(), test_flat_news_led_input_cannot_be_recovered_as_market_alert() (+10 more)

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
Cohesion: 0.06
Nodes (63): AlertRecipient, _automatic_delivery_lock(), _deliver_market_event_alert(), _delivery_error_class_name(), _delivery_retry_delay_seconds(), _disable_recipient_if_bot_blocked(), _is_permanent_telegram_delivery_error(), _is_transient_telegram_delivery_error() (+55 more)

### Community 59 - "price_service.py"
Cohesion: 0.13
Nodes (29): supported_symbols_display(), _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), _extract_sparkline_prices(), get_btc_market_data(), get_btc_price(), _get_cached_price() (+21 more)

### Community 60 - "system_status.py"
Cohesion: 0.10
Nodes (40): AppSettings, _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, ComponentStatus, _container_started_at() (+32 more)

### Community 61 - "test_bundle_and_cli.py"
Cohesion: 0.05
Nodes (64): ops_agent, _mark_report_success(), _validate_bundle(), OpsAgentLimits, load_state(), parse_timestamp(), Any, datetime (+56 more)

### Community 62 - "RichDeliveryUncertain"
Cohesion: 0.11
Nodes (17): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert() (+9 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.05
Nodes (50): aiohttp, _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any, datetime (+42 more)

### Community 64 - "test_news_intelligence_schema.py"
Cohesion: 0.22
Nodes (17): _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), asyncio, parametrize, Offline News Intelligence symbol-contract regression tests; no provider calls., RecordedProvider (+9 more)

### Community 65 - "RedactionReport"
Cohesion: 0.07
Nodes (62): httpx, _collect_alert_repetition_rows(), collect_db(), _collector_error(), _jsonable(), Any, Exception, _successful_alert_repetition_buckets() (+54 more)

### Community 66 - "button_router"
Cohesion: 0.10
Nodes (34): _build_admin_openai_costs_text(), send_admin_callback_response(), _standalone_settings_origin(), button_router(), DEFAULT_TYPE, Update, build_admin_alert_settings_keyboard(), build_admin_back_keyboard() (+26 more)

### Community 67 - "test_event_alert_postrelease_regressions.py"
Cohesion: 0.11
Nodes (25): _count_suppression(), EventRecipientFilterResult, _filter_event_recipients_for_cooldown(), RecipientOutcome, asyncio, test_numeric_family_drift_never_bypasses_four_hour_cooldown(), asyncio, parametrize (+17 more)

### Community 68 - "test_openai_costs.py"
Cohesion: 0.26
Nodes (22): OpenAICostsMonitor, bucket(), bucket_at(), client_mock(), configured(), page(), asyncio, parametrize (+14 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "validate_event_significance_output"
Cohesion: 0.17
Nodes (16): empirical_absolute_move_percentile(), Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., _required_choice(), validate_event_significance_output(), _significance_schema_check(), _payload(), parametrize (+8 more)

### Community 71 - "CCWBot"
Cohesion: 0.10
Nodes (20): Admin System Status, CCWBot, Current Limitations, Database Migrations, Development And Production Environments, Docker Compose, Documentation, Environment Variables (+12 more)

### Community 72 - "BundleWriter"
Cohesion: 0.12
Nodes (15): BundleSizeLimitError, BundleWriter, Any, Path, RuntimeError, Raised when mandatory evidence alone cannot fit the configured hard cap., Publish the manifest only after its complete JSON payload is on disk., sha256_file() (+7 more)

### Community 73 - "replay_event_significance.py"
Cohesion: 0.09
Nodes (31): _groq_json_mode_enabled(), scripts, classify_replay_error(), effort_budget(), groq_significance_response_format(), live_report(), load_cases(), NonObjectSignificanceError (+23 more)

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
Cohesion: 0.16
Nodes (23): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, _event_alert_render_prompt_payload(), Return only a supported sign; no rounded or raw market numbers reach Render., _render_market_direction(), test_specific_next_observation_is_not_generic(), _decision(), _market() (+15 more)

### Community 78 - "test_report_content_rich_and_llm_summary.py"
Cohesion: 0.14
Nodes (19): MarketReportDecision, format_html_market_report(), format_rich_market_report(), Escape all model/news wording; only safely link explicit HTTP(S) sources., Rich headings and sections, using exactly the persisted plain report content., Valid ordinary Telegram HTML when native Rich is definitively rejected., _safe_rich_line(), _llm_diagnostics_menu() (+11 more)

### Community 79 - "test_news_ingestion.py"
Cohesion: 0.07
Nodes (35): fetch_crypto_news(), headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Merge available feeds by publication age *before* applying the batch limit. A…, Low-cost, word-boundary-aware prefilter; not an alert decision. (+27 more)

### Community 80 - "test_news_intelligence_service.py"
Cohesion: 0.14
Nodes (49): LlmOperationOutcome, NewsItem, AsyncSession, Return stored, intelligence-ranked news candidates for a symbol. This selector…, select_intelligence_news_for_symbol(), LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., NewsIntelligenceService (+41 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "datetime"
Cohesion: 0.05
Nodes (52): argparse, concurrent_futures, datetime, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., Audit only aggregated benchmark budget and next-call feasibility (no inference). (+44 more)

### Community 83 - "event_analysis.py"
Cohesion: 0.14
Nodes (35): _claim_clause(), _claimed_percent(), _decimal_market_value(), _direction_for_claim(), directional_market_family(), _duration_minutes(), _duration_minutes_from_claim(), _elapsed_minutes() (+27 more)

### Community 84 - "supported_coins.py"
Cohesion: 0.39
Nodes (7): coin_display_name(), is_supported_symbol(), premium_symbols_display(), Supported coin metadata shared by price checks and Premium watchlists., test_deprecated_ghost_symbols_are_fully_removed(), test_gram_rebrand_uses_primary_gram_symbol_with_legacy_ton_alias(), test_premium_and_supported_symbol_display_use_gram()

### Community 85 - "CCW-20 paired final messages"
Cohesion: 0.09
Nodes (21): 10. ev_3c7f3da2e73e4b90 — ETH, 11. ev_7804adc277bd3333 — GRAM, 12. ev_345fc49db8255adf — GRAM, 13. ev_7b3325d2f2609480 — GRAM, 14. ev_1b39a518ede3c14f — GRAM, 15. ev_6500c5ad9f5364bc — GRAM, 16. ev_4bba21dd01bc8372 — SOL, 17. ev_1ea4cea05b78ed5c — SOL (+13 more)

### Community 86 - "event_chart.py"
Cohesion: 0.16
Nodes (18): ChartResult, _connectable_now_segment(), _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw, Deterministic PNG chart from persisted, timestamped price observations only. (+10 more)

### Community 87 - "openai_budget.py"
Cohesion: 0.16
Nodes (19): _openai_budget_status_line(), Return an admin-safe current UTC-month paid-provider budget summary., _cost(), monthly_budget_usd(), OpenAIBudgetLease, _positive_decimal_env(), pricing_usd_per_million(), datetime (+11 more)

### Community 88 - "test_watchlist_ux.py"
Cohesion: 0.06
Nodes (47): build_watchlist_keyboard(), build_subscribe_message(), build_watchlist_message(), build_watchlist_render(), _subscription_by_symbol(), AsyncFalse, AsyncNoop, AsyncTrue (+39 more)

### Community 89 - "test_event_alert_owner_copy_news_regressions.py"
Cohesion: 0.21
Nodes (16): _action_price_levels_supported(), compact_event_alert_possible_action(), _has_unsupported_situation_causality(), Keep Event Alert actions short, conditional, and non-prescriptive., test_ccw20_action_rejects_unsupported_future_divergence_or_convergence(), _decision(), _market(), Owner-approved Event Alert final-copy regressions (no provider/network calls). (+8 more)

### Community 90 - "Context Audit Report"
Cohesion: 0.07
Nodes (18): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+10 more)

### Community 91 - "_fixture"
Cohesion: 0.11
Nodes (26): _event_analysis_prompt_payload(), Return the compact semantic model view without runtime or repeated static…, Clear all breaker state (tests and controlled restarts)., reset_breakers(), _isolate_llm_breaker_state(), _test_verified_groq_routing(), _reset_state(), _estimate_tokens() (+18 more)

### Community 92 - "watchlist.py"
Cohesion: 0.18
Nodes (27): build_my_plan_keyboard(), is_admin_update(), Update, build_plan_message(), build_user_settings_render(), _current_telegram_user_id(), edit_myplan_message(), edit_user_settings_message() (+19 more)

### Community 93 - "refresh_report_cache_scheduled"
Cohesion: 0.30
Nodes (14): _is_report_provider_backoff_active(), Scheduled cache refresh: regenerate unless the cache stays fresh past the grace…, refresh_report_cache_scheduled(), _cached_report(), asyncio, Scheduled report cache refresh: cadence, grace window, and explicit skip…, test_daily_cache_fresh_by_seconds_at_fire_time_regenerates(), test_expired_weekly_cache_triggers_regeneration() (+6 more)

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.17
Nodes (11): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Log pattern counting, News-candidate signal (+3 more)

### Community 96 - "test_event_alert_render_grounded_copy.py"
Cohesion: 0.29
Nodes (13): Small, backed relationship codes for LLM prose; no raw prices or thresholds., verified_event_alert_render_context(), decision_for(), final_action(), market_down(), Evidence-backed Stage-2 Render guards and final-copy regression tests. All…, test_conditionals_do_not_hide_false_observed_direction(), test_render_does_not_invent_a_path_from_missing_or_gapped_snapshots() (+5 more)

### Community 97 - "test_event_alert_24h_now_continuity.py"
Cohesion: 0.18
Nodes (14): bot, bot_alerting, pil, Replay published CCW-20 final-copy candidates offline through actual assembly.…, _recorded_candidate_pairs(), test_ccw20_replay_all_20_recorded_candidate_final_pairs_without_llm_calls(), decision(), history() (+6 more)

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

### Community 105 - "_build_exact_event_context_fingerprint"
Cohesion: 0.29
Nodes (15): _build_exact_event_context_fingerprint(), _payload(), parametrize, test_ccw349_invalid_headline_does_not_hide_second_valid_headline(), test_ccw349_news_priority_changes_model_visible_context_and_fingerprint(), test_decimal_json_is_full_precision_json_number_not_float_or_string(), test_exact_context_does_not_reuse_the_ambiguous_change_field_contract(), test_exact_context_ignores_previous_title_not_sent_to_model() (+7 more)

### Community 106 - "settings"
Cohesion: 0.22
Nodes (15): _format_admin_alert_settings(), Edit a transient callback screen without exposing Telegram failures., Best-effort deletion of a user's slash command in a private chat., safe_delete_command_invocation(), safe_edit_callback_message(), DEFAULT_TYPE, Update, settings() (+7 more)

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.33
Nodes (17): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+9 more)

### Community 108 - "test_price_service.py"
Cohesion: 0.09
Nodes (29): _extract_ton_coin_data_from_simple_price(), get_coin_market_data_batch(), Fetch market data for supported symbols with one CoinGecko request. Missing…, Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., clean_price_caches(), clear_price_caches(), FakeClient, FakeResponse (+21 more)

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

### Community 113 - "database.py"
Cohesion: 0.13
Nodes (25): _resolve_window_market_context(), _save_price_state(), main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), PriceSnapshot, Database infrastructure for optional PostgreSQL runtime storage., Run Alembic migrations without blocking the active event loop. (+17 more)

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
Cohesion: 0.08
Nodes (39): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), combine_telegram_admin_user_ids(), parse_telegram_user_id(), parse_telegram_user_ids() (+31 more)

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
Cohesion: 0.16
Nodes (17): CoinGeckoRateLimitError, get_coin_price(), Exception, Raised when CoinGecko returns HTTP 429., Get current coin price and 24h change from CoinGecko. Unsupported symbols raise…, fetch(), asyncio, parametrize (+9 more)

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

### Community 145 - "conftest.py"
Cohesion: 0.15
Nodes (11): _real_socket, socket, _guarded_create_connection(), _guarded_getaddrinfo(), _GuardedSocket, _is_loopback(), _is_loopback_address(), _raise_external_network_block() (+3 more)

### Community 147 - "benchmark.py"
Cohesion: 0.20
Nodes (13): build_llm_messages(), graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), ctypes, base(), call(), memory(), prepare() (+5 more)

### Community 148 - "Development"
Cohesion: 0.15
Nodes (8): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.05
Nodes (77): MarketHeartbeatDecision, MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body(), sanitize_heartbeat_possible_action() (+69 more)

### Community 150 - "ai_agent_groq.py"
Cohesion: 0.06
Nodes (32): asyncpg, _json_dumps(), Canonical JSON that writes Decimal market values without binary-float loss., compact_elapsed_since(), bot_services, build_market_heartbeat_prompt(), build_market_report_prompt(), _event_alert_render_market_metrics() (+24 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.06
Nodes (66): effective_max_tokens_for(), is_reasoning_model(), max_tokens_for(), model_for(), Resolve the model for a (provider, call_type) pair from env, with defaults., Resolve the completion-token budget for a call type. The current ``LLM_*`` name…, Return the completion budget for one concrete provider attempt. The public…, True when this model identifier is known to accept ``reasoning_effort``. (+58 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "provider_attempts"
Cohesion: 0.18
Nodes (12): provider_attempts(), Return the ordered concrete provider/model attempts for one logical LLM…, Case schema, Commands (offline by default), Frozen evidence contract, Independent blinded evaluation, test_explicit_event_provider_overrides_select_only_openai_luna(), render_chain() (+4 more)

### Community 156 - "automatic_price_check"
Cohesion: 0.07
Nodes (52): _raw_event_key_from_payload(), _semantic_family_from_payload(), AlertRecipientResolution, automatic_price_check(), _build_news_candidates(), _classify_news_context(), _coin_is_secondary_context(), _event_numeric_context() (+44 more)

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

### Community 162 - "callbacks.py"
Cohesion: 0.14
Nodes (27): Central callback-query router for Telegram inline keyboards., log_custom_emoji_ids(), price(), DEFAULT_TYPE, Update, Manual price lookup and text-message utility handlers., User settings command handler., build_price_keyboard() (+19 more)

### Community 164 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.06
Nodes (47): alembic_config, alembic_script, ast, automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, importlib (+39 more)

### Community 169 - "asyncio"
Cohesion: 0.07
Nodes (12): asyncio, parametrize, test_event_chart_file_id_reused_across_recipients_in_one_dispatch(), test_heartbeat_falls_back_to_styled_html_if_rich_adapter_has_no_token(), test_integrity_conflict_preserves_terminal_delivery_reservation(), test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post(), test_rich_ambiguous_error_never_falls_back_or_retries() (+4 more)

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
Cohesion: 0.08
Nodes (47): Mark news items as seen in PostgreSQL after they were used by the bot., remember_news_context(), _build_deterministic_report_decision(), _build_market_report_input(), _build_report_coin_payload(), _build_weekly_breadth(), _build_weekly_coin_context(), _build_weekly_context() (+39 more)

### Community 174 - "_runner_private.py"
Cohesion: 0.28
Nodes (15): call_once(), classify(), fail(), main(), persist(), datetime, quota_allows(), Finite direct-provider CCW-16 canary runner; Python stdlib only. This script… (+7 more)

### Community 175 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 176 - "types"
Cohesion: 0.29
Nodes (3): test_report_scheduler_check_interval_fits_refresh_grace(), test_significance_prompt_defaults_to_no_alert_and_requires_new_significance(), types

### Community 177 - "runtime/state.py"
Cohesion: 0.15
Nodes (12): Runtime state and startup helpers., close_database(), initialize_database(), Any, Dispose database resources created during startup., SessionFactoryRef, _sync_package_database_engine(), asyncio (+4 more)

### Community 178 - "test_price_handlers.py"
Cohesion: 0.45
Nodes (11): _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users(), test_price_maps_provider_errors_to_safe_user_messages(), test_price_normalizes_legacy_ton_alias_before_lookup(), test_price_rejects_unsupported_symbol_without_provider_call(), test_price_repeated_calls_are_not_ui_throttled() (+3 more)

### Community 180 - "/graphify"
Cohesion: 0.09
Nodes (18): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+10 more)

### Community 181 - "normalize_symbol"
Cohesion: 0.06
Nodes (66): AnalysedWindowReference, _automatic_market_check_job_name(), _build_event_analysis_id(), _build_event_instance_key(), _build_market_heartbeat_id(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _calculate_price_change() (+58 more)

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.33
Nodes (5): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps

### Community 183 - "utc_now"
Cohesion: 0.35
Nodes (11): datetime, Return timezone-aware UTC timestamp., UserSettings, utc_now(), _get_app_settings_row(), get_or_create_app_settings(), get_or_create_user_settings(), AsyncSession (+3 more)

### Community 184 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 185 - "unittest_mock"
Cohesion: 0.19
Nodes (10): asyncio, parametrize, Report availability must survive exhausted LLM providers, but not unrelated…, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload(), asyncio, SessionContext (+2 more)

### Community 186 - "test_news_driven_alerts.py"
Cohesion: 0.47
Nodes (5): _load_news_driven_alert_candidates(), asyncio, Regression coverage for the disabled standalone-news Event Alert path., test_news_driven_alerts_warning_logs_once_not_per_cycle(), test_news_driven_flag_cannot_bypass_product_policy()

### Community 187 - "check_owner_html.py"
Cohesion: 0.22
Nodes (4): html_parser, HTMLParser, P, Quick syntax and blind-payload integrity check for standalone owner form.

### Community 188 - "0025_llm_operation_correlation.py"
Cohesion: 0.38
Nodes (8): downgrade(), _has_column(), _has_index(), _has_table(), upgrade(), downgrade(), _replace_event_name_check(), upgrade()

### Community 189 - "news_context.py"
Cohesion: 0.10
Nodes (37): _alert_news_rank(), _candidate_news_relevance_label(), classify_news_relevance(), filter_news_for_symbol(), _format_candidate_news(), _has_gram_crypto_context(), _is_clearly_market_wide_news(), is_generic_news_item() (+29 more)

### Community 190 - "_validate_event_alert_render_causality"
Cohesion: 0.29
Nodes (7): _has_unsupported_event_claim(), Permit a verified pace comparison, but not an unsupported event claim., Compare actual snapshot step rates; do not assume nominal 30m/1h timing., _short_window_pace_context(), Reject fabricated context, independent of editorial preferences. Valid text…, _validate_event_alert_render_causality(), test_ccw20_frozen_eth_and_sol_errors_are_removed_at_final_assembly()

### Community 192 - "LLMRateLimitBackoffActive"
Cohesion: 0.07
Nodes (32): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., AIInvalidJsonError, LLMRateLimitBackoffActive, datetime (+24 more)

### Community 193 - "Repository Source of Truth"
Cohesion: 0.33
Nodes (5): Canonical ownership, Conflict resolution, No standing rules outside the repository, Repository bootstrap, Repository Source of Truth

### Community 194 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

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

### Community 210 - "graphify reference: extra exports and benchmark"
Cohesion: 0.25
Nodes (7): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 213 - "handlers/reports.py"
Cohesion: 0.39
Nodes (7): daily_report(), DEFAULT_TYPE, Update, Market report command handlers., weekly_report(), send_weekly_report_message(), Models, token budgets, and reasoning effort

### Community 214 - "_build_weekly_report_message"
Cohesion: 0.28
Nodes (9): _build_daily_report_message(), _build_weekly_report_message(), _format_report_coin_watchpoints(), _format_weekly_breadth(), Bound LLM verbosity without replacing or manufacturing market claims., One price/change table, plus model watchpoints with no repeated quotes., Non-repeated per-coin watchpoints carry useful weekly analysis., Scenario/level watchpoints only; do not echo summaries/price changes. (+1 more)

### Community 217 - "CCW-20 — Offline safety correction of retained Cloudflare final texts"
Cohesion: 0.33
Nodes (5): CCW-20 — Offline safety correction of retained Cloudflare final texts, Concrete verified example — ETH (`ev_0ab71234c9080ecc`), Finding / fix, Reproducible offline check, What this test does not prove

### Community 223 - "build_review.py"
Cohesion: 0.32
Nodes (11): candidate(), canon(), context(), csvwrite(), main(), Private read-only CCWBot market benchmark and independent review CSV exporter., run_psql(), safe() (+3 more)

### Community 233 - "convert_human_reviews.py"
Cohesion: 0.42
Nodes (8): finalize_reconciled(), labels_for(), main(), normalize_yes_no(), Convert two completed independent reviewer CSV sets to PR1 benchmark labels.…, rows(), score_disagreements(), validate_phase()

### Community 234 - "pytest"
Cohesion: 0.10
Nodes (25): AsyncSession, LLM usage telemetry persistence. Belongs here: saving and updating…, Update a usage row when downstream JSON schema validation fails., Save one LLM usage telemetry row., save_llm_usage_log(), update_llm_usage_log_status(), get_latest_market_report(), AsyncSession (+17 more)

## Knowledge Gaps
- **440 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+435 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1719 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `select()` connect `select` to `bot/config.py`, `onboarding.py`, `test_telegram_stars_payments.py`, `test_system_status.py`, `test_openai_budget.py`, `test_groq_budget.py`, `db/premium.py`, `test_market_heartbeat.py`, `LlmUsageLog`, `test_product_analytics.py`, `automatic_price_check`, `openai_costs.py`, `test_report_cooldowns.py`, `test_event_alert_pipeline.py`, `bot/news.py`, `news_intelligence_service.py`, `make_news_key`, `router.py`, `utc_now`, `User`, `system_status.py`, `test_news_intelligence_schema.py`, `test_news_intelligence_service.py`, `openai_budget.py`, `test_watchlist_ux.py`, `build_review.py`, `pytest`, `database.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `unknown()` connect `Observability Snippets` to `Ops-Agent Service`, `asyncio`, `CCWBot Ops-Agent Report Analysis`, `RichDeliveryUncertain`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `SimulatedDeployTests` connect `SimulatedDeployTests` to `datetime`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 170 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 170 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _440 weakly-connected nodes found - possible documentation gaps or missing edges._