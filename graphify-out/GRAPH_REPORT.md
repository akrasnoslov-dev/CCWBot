# Graph Report - CCWBot  (2026-11-01)

## Corpus Check
- 657 files · ~1,155,343 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 34 file(s) not represented in the graph (top: .toml 12, (none) 8, .csv 7)

## Summary
- 5885 nodes · 17399 edges · 230 communities (196 shown, 34 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1447 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a5afeb72`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EventAnalysisValidationError
- json
- hashlib
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
- Base
- test_acquisition_link_workflow.py
- alert_similarity.py
- test_llm_invalid_output_fallback.py
- report_markdown.py
- event_alert_benchmark.py
- _build_event_alert_payload
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
- domain/premium.py
- ccw41_reviewer_c_audit.py
- detectors.py
- admin.py
- schedule_automatic_btc_check
- utc_now
- Provider fallback (redundancy)
- error_file_logging.py
- LLMRouter
- collect_docker
- test_event_alert_pipeline.py
- User
- Observability Snippets
- Alert
- bot/news.py
- AIProviderRateLimitError
- news_intelligence_service.py
- make_news_key
- log
- test_llm_rate_limit_backoff.py
- market_report_rich.py
- AISchemaValidationError
- onboarding.py
- EventAnalysisDecision
- test_llm_outage_detectors.py
- manifest.json
- CCWBot Growth Strategy: 0 -> 1 Premium
- _deliver_market_event_alert
- price_service.py
- system_status.py
- test_bundle_and_cli.py
- test_seen_news_dedup.py
- test_event_analysis_health.py
- test_news_intelligence_schema.py
- RedactionReport
- button_router
- _filter_event_recipients_for_cooldown
- canonicalize_event_key
- 0001_initial_schema.py
- validate_event_significance_output
- CCWBot
- BundleWriter
- replay_event_significance.py
- 0024_gram_symbol.py
- test_event_alert_composition_investigation.py
- test_agent_workflow_contract.py
- test_event_alert_delivery_quality_regressions.py
- test_heartbeat_postgres.py
- test_news_ingestion.py
- select
- CCWBot Ops-Agent Report Analysis
- datetime
- event_analysis.py
- build_alert_evidence_payloads
- CCW-20 paired final messages
- event_chart.py
- report_context.py
- FakeMessage
- FakeResponse
- Context Audit Report
- _fixture
- test_watchlist_ux.py
- refresh_report_cache_scheduled
- ccwbot-deploy-safe.sh
- CCWBot Ops-Agent
- test_event_alert_render_grounded_copy.py
- test_alert_recipients.py
- test_event_alert_rich_chart_ux.py
- Ops-Agent Service
- _test_A_C_survey.js
- ccwbot-ops-agent-collect
- SimulatedDeployTests
- Dev Ops Guide
- Event Alert benchmark and historical diagnostics (PR 1)
- render_decision_report_context
- telegram_error
- test_event_alert_chart_markers.py
- test_price_service.py
- Event Alert logic
- Documentation
- CCW-41 Reviewer C offline audit
- ccwbot-ops-agent-mark-report-success
- normalize_symbol
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
- LLMJsonResult
- Development
- test_market_heartbeat.py
- os
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
- test_database_comments.py
- reviewer-c-rubric.md
- What You Must Do When Invoked
- extraction-spec.md
- test_alembic_migrations.py
- test_rich_403_preserves_safe_blocked_classification_without_raw_errors
- CCW-41 exploratory Reviewer-C agreement/disagreement
- test_heartbeat_does_not_query_previous_event
- test_observability_reconciliation.py
- bot/reports.py
- _runner_private.py
- _StructuredRecordBuffer
- types
- SessionFactoryRef
- test_price_handlers.py
- FakeAsyncClient
- /graphify
- ai_agent_groq.py
- Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)
- 0008_database_comments.py
- CCW-43 — Evidence-based Event Analysis prompt redesign
- test_exhausted_provider_chain_uses_verified_data_fallback
- test_news_driven_alerts.py
- P
- 0025_llm_operation_correlation.py
- news_context.py
- Repository Source of Truth
- .__init__
- pytest
- validate_event_analysis_output
- CCWBot Operational Report — Unverified (No Production Bundle)
- collections_abc
- 0026_growth_analytics.py
- CCW-25 — Self-hosted LLM owner decision
- CCW-41 owner-reviewed significance reference v1
- _working_code_backup.py
- CCW-29 Handoff — New CCW-43 Event Analysis Prompts
- CCW-25 — Owner decision
- CCWBot — итоги оценки alerts (16 октября 2026)
- CCWBot — blind owner disagreement-only replay
- clean_news_title
- Repository-backed Graphify
- CCW-25 research evidence
- .__init__
- operator_prompt.md
- graphify reference: extra exports and benchmark
- ccw41_private/reviewer-c-rubric.md
- README_HUMAN_REVIEW.md
- RichDeliveryUncertain
- _build_weekly_report_message
- README_RU.md
- test_rich_chart_quality_detector.py
- fresh200_luna_wait_start.sh
- openai_luna_wait_start.sh
- 0027_market_heartbeat_defaults.py
- build_review.py
- 0004_multicoin_delivery_idempotency.py
- 0007_unique_telegram_user_id.py
- CCW20_FINAL_MESSAGE_BASELINE_20261026.md
- convert_human_reviews.py
- database.py
- asyncio

## God Nodes (most connected - your core abstractions)
1. `select()` - 173 edges
2. `Period` - 115 edges
3. `Base` - 100 edges
4. `LLMRouter` - 98 edges
5. `normalize_symbol()` - 89 edges
6. `EventAnalysisValidationError` - 68 edges
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

## Communities (230 total, 34 thin omitted)

### Community 0 - "EventAnalysisValidationError"
Cohesion: 0.18
Nodes (36): EventAnalysisValidationError, ValueError, Raised when LLM event-analysis JSON cannot be trusted., alert_analysis_result(), factual_market_input(), test_alert_accepts_gram_display_symbol_for_backend_gram(), test_alert_possible_action_advice_like_wording_no_longer_blocks_schema(), test_alert_rejects_invalid_urgency() (+28 more)

### Community 1 - "json"
Cohesion: 0.03
Nodes (53): collections, csv, html_parser, json, math, pathlib, re, main() (+45 more)

### Community 2 - "hashlib"
Cohesion: 0.08
Nodes (28): copy, hashlib, io, Stage verified model-visible pilot calls into isolated CCW-16 workspace. No…, Stage and execute a finite, blind, genuine new-event holdout replay. No…, Finish immutable fresh200 Luna staging manifest preflight, without reading…, CCW-29 full 200-case improved-prompt replay; builds audited jobs and starts…, CCW-29 new full-200 read-only collector, per-provider owner-label scoring; no… (+20 more)

### Community 3 - "test_onboarding.py"
Cohesion: 0.19
Nodes (32): ProductEvent, UserCoinSubscription, build_instant_brief(), Render a brief from persisted PriceState only; never call LLMs or providers., Send a first-run BTC brief or a concise returning-user dashboard., send_start_experience(), inspect, build_session() (+24 more)

### Community 4 - "test_db_queries_and_detectors.py"
Cohesion: 0.04
Nodes (65): alembic_migration, alembic_operations, ops_agent_collectors, _alert_evidence_windows(), datetime, run_detectors(), Period, sqlite3 (+57 more)

### Community 5 - "test_llm_breaker.py"
Cohesion: 0.08
Nodes (70): _backoff_schedule(), breaker_snapshot(), _BreakerState, _failure_threshold(), is_enabled(), datetime, Circuit breaker for (call_type, provider, model) triples that keep failing…, Read-only view of current breaker state, for diagnostics. (+62 more)

### Community 6 - "telemetry.py"
Cohesion: 0.03
Nodes (128): asyncio, _create_market_heartbeat(), AsyncSession, Update a usage row when downstream JSON schema validation fails., Save one LLM usage telemetry row., save_llm_usage_log(), update_llm_usage_log_status(), _get_int_env() (+120 more)

### Community 7 - "test_rich_market_report_delivery.py"
Cohesion: 0.09
Nodes (41): MarketReportDecision, compact_report_for_display(), format_html_market_report(), format_rich_market_report(), market_report_change_chart(), Rich headings and sections, using exactly the persisted plain report content., Valid ordinary Telegram HTML when native Rich is definitively rejected., Create compact Telegram infographics solely from persisted market evidence. (+33 more)

### Community 8 - "test_telegram_stars_payments.py"
Cohesion: 0.09
Nodes (56): Payment, activate_premium_from_telegram_stars_payment(), Record one Stars payment and extend Premium once for that payment id., build_premium_activation_keyboard(), build_premium_invoice_payload(), build_premium_prices(), build_subscribe_message(), _coerce_datetime() (+48 more)

### Community 9 - "common.py"
Cohesion: 0.08
Nodes (39): _callback_command_update(), decorator(), wrapper(), _pop_denied(), DEFAULT_TYPE, Update, Shared Telegram handler helpers. Belongs here: cross-command logging,…, Edit a transient callback screen without exposing Telegram failures. (+31 more)

### Community 10 - "test_system_status.py"
Cohesion: 0.17
Nodes (49): PriceState, build_admin_llm_diagnostics_text(), build_admin_system_status_text(), Return concise admin-safe status text without live provider probes., Return admin-safe provider-attempt diagnostics separate from feature health., builtins, build_session_factory(), _event_analysis() (+41 more)

### Community 11 - "sqlalchemy"
Cohesion: 0.04
Nodes (22): alembic, downgrade(), _table_names(), upgrade(), _column_names(), downgrade(), upgrade(), _column_names() (+14 more)

### Community 12 - "test_openai_costs.py"
Cohesion: 0.05
Nodes (96): OpenAIBudgetReservation, Durable pre-request reservation for the single global OpenAI monthly cap., Return the fully resolved per-call-type LLM configuration. Model identifiers,…, resolved_configuration(), _cost(), monthly_budget_usd(), OpenAIBudget, OpenAIBudgetExhausted (+88 more)

### Community 13 - "bot/alerts.py"
Cohesion: 0.04
Nodes (79): alert_title_action(), AlertDecision, AlertSeverity, AlertType, Enum, str, Presentation-only severity labels retained for non-Event-Alert compatibility.…, SeverityEvaluation (+71 more)

### Community 14 - "Base"
Cohesion: 0.14
Nodes (24): Base, Base class for all SQLAlchemy models., _Charge, GroqBudget, GroqBudgetExhausted, datetime, Test-only reset; production restarts reload persisted usage., DeclarativeBase (+16 more)

### Community 15 - "test_acquisition_link_workflow.py"
Cohesion: 0.14
Nodes (21): create_acquisition_link(), _is_acquisition_link_code_collision(), Create one collision-safe, validated operator acquisition link., AcquisitionLink, AcquisitionLinkMetadata, Allowlisted, bounded metadata stored behind an opaque acquisition link., Return safe operator metadata or reject values outside the attribution…, validate_acquisition_link_metadata() (+13 more)

### Community 16 - "alert_similarity.py"
Cohesion: 0.15
Nodes (35): hmac, _add_group_row(), _alert_quality(), _analysis_ref(), _analysis_text(), _base_payload(), BundleHasher, _content_fingerprints() (+27 more)

### Community 17 - "test_llm_invalid_output_fallback.py"
Cohesion: 0.13
Nodes (41): ask_event_analysis_raw(), _configure(), ContentProvider, _empty_report_news_context(), _grounded_alert(), _grounding_market(), _grounding_schema_check(), _install_report_inputs() (+33 more)

### Community 18 - "report_markdown.py"
Cohesion: 0.19
Nodes (31): _affected_users(), _alert_quality(), _collector_next_action(), _collector_status_table(), _count_pct(), _data_completeness(), _data_sources(), _decision_reasons() (+23 more)

### Community 19 - "event_alert_benchmark.py"
Cohesion: 0.08
Nodes (47): CCW-15 — Reviewer A Event Analysis prompt pack (2026-10-21), CCW-16 matched-input replay contract (NOT authorized by this task), Read-only local check, importlib_util, random, Owner-approved PR2 reviewer A reference, kept outside Git in ignored reports/.…, CCW-29 fresh private holdout: collect real POST-200 market cases via…, choose() (+39 more)

### Community 20 - "_build_event_alert_payload"
Cohesion: 0.10
Nodes (31): _build_event_alert_html_message(), _build_event_alert_payload(), _event_news_shortlist_limit(), _preserve_render_prose(), Minimal whitespace normalization; retain the model's paragraph structure., Validate every displayed USD quote against actually supplied observations.…, _validate_event_alert_render_prices(), CCW-20 — Offline safety correction of retained Cloudflare final texts (+23 more)

### Community 21 - "test_event_alert_historical_diagnostics.py"
Cohesion: 0.15
Nodes (26): _build_exact_event_context_fingerprint(), _payload(), parametrize, test_ccw349_invalid_headline_does_not_hide_second_valid_headline(), test_ccw349_news_priority_changes_model_visible_context_and_fingerprint(), test_decimal_json_is_full_precision_json_number_not_float_or_string(), test_exact_context_does_not_reuse_the_ambiguous_change_field_contract(), test_exact_context_ignores_previous_title_not_sent_to_model() (+18 more)

### Community 22 - "cli.py"
Cohesion: 0.14
Nodes (30): _add_failure(), build_parser(), _collect(), _collection_result(), _collection_status(), _event_analysis_signal(), _failed_evidence(), _inspect_state() (+22 more)

### Community 23 - "test_heartbeat_silence.py"
Cohesion: 0.11
Nodes (26): pytest_asyncio, add_delivery(), asyncio, parametrize, test_cache_expiring_before_lock_acquisition_is_not_sent(), test_concurrent_checks_send_one_heartbeat_and_reset_timer(), test_delayed_success_uses_completion_not_reservation(), test_event_resets_timer_during_generation_market_fetch() (+18 more)

### Community 24 - "LlmUsageLog"
Cohesion: 0.12
Nodes (32): LlmUsageLog, Clear all state (tests and controlled restarts)., reset(), LogicalHealth, _outcome_kind(), AsyncSession, datetime, Read-only rolling health of *terminal logical operations*, never provider… (+24 more)

### Community 25 - "event_text.py"
Cohesion: 0.04
Nodes (87): _action_price_levels_supported(), _action_without_negated_technical_levels(), compact_event_alert_possible_action(), compact_event_alert_situation(), _concise_explanation_clause(), _decimal_market_value(), ensure_useful_situation(), event_alert_presentation_fallback() (+79 more)

### Community 26 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 27 - "test_event_analysis_cloudflare_schema.py"
Cohesion: 0.08
Nodes (35): ask_event_alert_render_raw(), ask_event_significance_raw(), ask_market_heartbeat_raw(), ask_market_report_raw(), ask_news_intelligence_raw(), _json_response_validator(), Return JSON mode and provider-specific schemas for verified model attempts., _structured_response_formats() (+27 more)

### Community 28 - "test_product_analytics.py"
Cohesion: 0.09
Nodes (42): AcquisitionAttribution, capture_first_touch_attribution(), list_active_acquisition_links(), AsyncSession, datetime, Durable, allowlisted product analytics persistence., List a bounded set of links which may currently attribute a start., Resolve an active opaque deep-link token into configured attribution. (+34 more)

### Community 29 - "validate_market_report_output"
Cohesion: 0.17
Nodes (36): _first_text_field(), _format_report_text_dict(), MarketReportValidationError, _normalize_report_text_list_item(), _optional_text(), Any, ValueError, Raised when LLM market-report JSON cannot be trusted. (+28 more)

### Community 30 - "properties"
Cohesion: 0.05
Nodes (41): additionalProperties, pattern, type, pattern, type, enum, items, minItems (+33 more)

### Community 31 - "domain/premium.py"
Cohesion: 0.26
Nodes (20): _as_aware_utc(), can_deliver_market_heartbeat_now(), get_user_plan(), get_user_trial(), has_premium_entitlement(), heartbeat_activation_baseline(), is_coin_unlocked_for_user(), is_user_premium_active() (+12 more)

### Community 32 - "ccw41_reviewer_c_audit.py"
Cohesion: 0.07
Nodes (72): audit(), positive_age_minutes(), ranking(), main(), _number(), _time(), _aggregate_markdown(), _cli() (+64 more)

### Community 33 - "detectors.py"
Cohesion: 0.11
Nodes (34): consecutive_zero_success_runs(), detector_payload(), event_analysis_call_totals(), _event_analysis_dead_detector(), _event_analysis_model_drift_detector(), _event_ref(), _file_payload(), _has_query() (+26 more)

### Community 34 - "admin.py"
Cohesion: 0.16
Nodes (43): build_acquisition_telegram_url(), Build a Telegram deep link only from a valid configured bot username and opaque…, acquisition_link(), _acquisition_link_usage_text(), acquisition_links(), admin(), _build_admin_llm_diagnostics_text(), _build_admin_system_status_text() (+35 more)

### Community 35 - "schedule_automatic_btc_check"
Cohesion: 0.40
Nodes (3): Compatibility wrapper for older imports; schedules the market-wide check., schedule_automatic_btc_check(), test_legacy_automatic_btc_scheduler_alias_uses_market_job_name()

### Community 36 - "utc_now"
Cohesion: 0.14
Nodes (38): Return timezone-aware UTC timestamp., utc_now(), reports(), _build_report_telegram_message(), get_or_generate_report(), One shared refresh on old content; never fan out LLM/RSS per recipient., send_daily_report_message(), asyncio (+30 more)

### Community 37 - "Provider fallback (redundancy)"
Cohesion: 0.17
Nodes (11): Admin OpenAI Platform Costs monitoring (optional, read-only), Current Event Alert Luna-only policy (owner update 2026-10-29), Event Analysis timeout and operation budget, Groq free-tier admission control (Event Analysis), Historical CCW-20 Event Alert provider order (superseded), Historical Gemini 429 quota classification and backoff, LLM Usage Reporting, Ops-Agent LLM Usage Evidence (+3 more)

### Community 38 - "error_file_logging.py"
Cohesion: 0.08
Nodes (48): _log_event_alert_candidate_crossing(), Record that a symbol reached the point of being analysed, before the LLM is…, Compatibility wrapper for observability logging helpers., bot_observability, _active_error_log_path(), apply_persisted_error_file_logging_state(), AttributableFormatter, build_sanitized_log_exports() (+40 more)

### Community 39 - "LLMRouter"
Cohesion: 0.15
Nodes (57): AllProvidersFailedError, Raised when every provider in the fallback chain has been exhausted.…, LLMRouter, _call(), _call_validated(), _configure(), _content_result(), FakeProvider (+49 more)

### Community 40 - "collect_docker"
Cohesion: 0.23
Nodes (23): _clean_text(), collect_docker(), _container_name(), _error_category(), _is_running(), _load_restart_counts(), _load_status_payload(), Any (+15 more)

### Community 41 - "test_event_alert_pipeline.py"
Cohesion: 0.05
Nodes (52): _event_alert_presentation_title(), _event_context_fingerprint(), _get_recent_event_analysis_decision_by_exact_context(), _has_non_flat_analysed_market_context(), _llm_no_alert_decision_reason(), _merge_existing_event_analysis_payload(), Render the headline from the primary deterministic metric, not LLM prose., Keep the current deterministic rendering when an event already has an analysis. (+44 more)

### Community 42 - "User"
Cohesion: 0.14
Nodes (32): User, backfill_blocked_users_from_alerts(), get_active_users_with_alert_preferences(), get_active_users_with_chat_ids(), get_or_create_user(), get_user_by_telegram_chat_id(), get_user_role(), is_telegram_chat_delivery_enabled() (+24 more)

### Community 43 - "Observability Snippets"
Cohesion: 0.08
Nodes (29): consecutive_failures(), Output, Rules you enforce, What you review, Admin System Status, Compact admin LLM overview, Delivery Outcome Tracking, Duplicate/Suppressed Analysis (+21 more)

### Community 44 - "Alert"
Cohesion: 0.06
Nodes (70): _get_or_create_event_alert_market_event(), count_market_events(), count_recent_market_events_for_symbol(), get_alert_delivery(), get_event_ai_analysis(), get_last_sent_alert(), get_last_sent_alert_at(), get_last_sent_event_alert_at_for_event_key() (+62 more)

### Community 45 - "bot/news.py"
Cohesion: 0.15
Nodes (31): _dedupe_report_news(), fetch_report_news_context(), within_window(), _has_report_news_identity(), _incident_phase(), _item_link(), _item_published_at(), _item_related_symbols() (+23 more)

### Community 46 - "AIProviderRateLimitError"
Cohesion: 0.13
Nodes (23): ABC, BaseProvider, ProviderResult, Normalized successful chat-completion result returned by every provider., Common interface for all LLM providers., True when this provider has all configuration required for an attempt., Run one chat completion and return a :class:`ProviderResult` on success.…, AIProviderRateLimitError (+15 more)

### Community 47 - "news_intelligence_service.py"
Cohesion: 0.09
Nodes (36): Persist one sanitized terminal outcome for a logical LLM operation., save_llm_operation_outcome(), get_cached_news_item_analysis(), Return a reusable structured news analysis for the exact model-aware input hash., _budget_priority_score(), build_llm_payload(), build_post_llm_dedup_group_id(), build_pre_llm_dedup_group_id() (+28 more)

### Community 48 - "make_news_key"
Cohesion: 0.13
Nodes (28): make_news_key(), Build a stable key for a news item. Links are preferred because RSS titles can…, SeenNews, cleanup_seen_news(), count_recent_news_intelligence_llm_calls(), get_cooling_failed_news_keys(), get_news_item_by_key(), get_recent_seen_news() (+20 more)

### Community 49 - "log"
Cohesion: 0.05
Nodes (65): AbstractEventLoop, AppRunner, _build_market_heartbeat_id(), cleanup_seen_news_job(), generate_market_heartbeats(), DEFAULT_TYPE, schedule_market_heartbeat_generation(), schedule_seen_news_cleanup() (+57 more)

### Community 50 - "test_llm_rate_limit_backoff.py"
Cohesion: 0.06
Nodes (45): AsyncOpenAI, OpenAICompatibleProvider, Create the provider client lazily, only when a call is actually needed., Sampling parameters supported by this provider/model pair., Shared implementation for OpenAI-compatible chat-completions providers., CloudflareProvider, get_provider(), Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions… (+37 more)

### Community 51 - "market_report_rich.py"
Cohesion: 0.12
Nodes (27): _chart_source_rows(), _draw_daily_chart(), _draw_weekly_chart(), _font(), _percent_label(), ImageDraw, _range_label(), Presentation-only Rich Telegram reports from persisted, validated report data.… (+19 more)

### Community 52 - "AISchemaValidationError"
Cohesion: 0.11
Nodes (31): _schema_check(), AIInvalidJsonError, AISchemaValidationError, datetime, Exception, RuntimeError, Raised when the provider response is not valid JSON., Raised when validated JSON does not match the expected schema. ``raw_content``… (+23 more)

### Community 53 - "onboarding.py"
Cohesion: 0.08
Nodes (40): ensure_default_coin_subscriptions(), Ensure one subscription row per supported symbol for a user., is_symbol_free(), build_onboarding_customize_keyboard(), build_onboarding_keyboard(), build_premium_paywall_keyboard(), build_trial_offer_keyboard(), Premium-only onboarding selector. BTC stays as the free default during… (+32 more)

### Community 54 - "EventAnalysisDecision"
Cohesion: 0.07
Nodes (55): EventAnalysisDecision, _build_event_instance_key(), _event_instance_bucket(), _event_instance_key_for_decision(), _raw_event_key_from_payload(), _semantic_family_from_payload(), _stable_related_news_ids(), _as_news_only_rejected_decision() (+47 more)

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
Cohesion: 0.08
Nodes (46): AlertRecipient, _automatic_delivery_lock(), _deliver_market_event_alert(), _delivery_error_class_name(), _delivery_retry_delay_seconds(), _disable_recipient_if_bot_blocked(), _is_permanent_telegram_delivery_error(), _is_transient_telegram_delivery_error() (+38 more)

### Community 59 - "price_service.py"
Cohesion: 0.12
Nodes (31): _build_stale_price_payload(), _coingecko_bool(), _coingecko_headers(), _extract_sparkline_prices(), get_btc_market_data(), get_btc_price(), _get_cached_price(), get_coin_price() (+23 more)

### Community 60 - "system_status.py"
Cohesion: 0.10
Nodes (42): AppSettings, _age_label(), _ai_health(), _as_utc(), build_admin_llm_summary_html(), ComponentHealth, ComponentStatus, _container_started_at() (+34 more)

### Community 61 - "test_bundle_and_cli.py"
Cohesion: 0.05
Nodes (64): ops_agent, _mark_report_success(), _validate_bundle(), OpsAgentLimits, load_state(), parse_timestamp(), Any, datetime (+56 more)

### Community 62 - "test_seen_news_dedup.py"
Cohesion: 0.14
Nodes (30): main(), One-time backfill for users who previously blocked the Telegram bot., run_backfill(), attach_analysis_to_market_event(), get_latest_success_event_ai_analysis(), Return any successful saved analysis for a market event., Save one raw LLM event-analysis attempt., Attach one successful event analysis, reusing the canonical row when present. (+22 more)

### Community 63 - "test_event_analysis_health.py"
Cohesion: 0.05
Nodes (49): aiohttp, _log_event_analysis_failure(), Log a failed event analysis, escalating to ERROR once failures stop being…, _event_analysis_block(), health_response(), _isoformat_timestamp(), Any, datetime (+41 more)

### Community 64 - "test_news_intelligence_schema.py"
Cohesion: 0.25
Nodes (17): _default_llm_client(), _schema_check(), Reject parseable provider output that does not satisfy the requested news…, validate_news_intelligence_schema(), schema_check(), asyncio, parametrize, Offline News Intelligence symbol-contract regression tests; no provider calls. (+9 more)

### Community 65 - "RedactionReport"
Cohesion: 0.07
Nodes (62): httpx, _collect_alert_repetition_rows(), collect_db(), _collector_error(), _jsonable(), Any, Exception, _successful_alert_repetition_buckets() (+54 more)

### Community 66 - "button_router"
Cohesion: 0.14
Nodes (19): bot_handlers, button_router(), DEFAULT_TYPE, Update, AsyncFalse, AsyncTrue, _callback_update(), _callback_values() (+11 more)

### Community 67 - "_filter_event_recipients_for_cooldown"
Cohesion: 0.15
Nodes (18): _numeric_context_payload(), _count_suppression(), EventRecipientFilterResult, _filter_event_recipients_for_cooldown(), RecipientOutcome, asyncio, The production 2026-10-12/13 numeric-key path omitted both stored families., test_legacy_numeric_price_key_cannot_bypass_four_hour_semantic_cooldown() (+10 more)

### Community 68 - "canonicalize_event_key"
Cohesion: 0.11
Nodes (27): canonicalize_event_key(), _collapse_event_key(), _contains_any_phrase(), _contains_price_downtrend_signal(), _contains_price_uptrend_signal(), _fallback_event_key(), _is_random_event_key(), _normalize_event_key_text() (+19 more)

### Community 69 - "0001_initial_schema.py"
Cohesion: 0.25
Nodes (15): _add_missing_alert_delivery_columns(), _column_names(), _create_alerts(), _create_app_settings(), _create_event_ai_analyses(), _create_market_events(), _create_price_state(), _create_seen_news() (+7 more)

### Community 70 - "validate_event_significance_output"
Cohesion: 0.16
Nodes (17): empirical_absolute_move_percentile(), EventSignificanceDecision, Return the empirical percentile of an absolute move without deciding…, Validate the compact significance-only Event Analysis result., _required_choice(), validate_event_significance_output(), _significance_schema_check(), _payload() (+9 more)

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
Cohesion: 0.18
Nodes (28): market_direction_claims_supported(), Check explicit period directions and the direction implied by relationships., Reject fabricated context, independent of editorial preferences. Valid text…, _validate_event_alert_render_causality(), market(), parametrize, Synthetic regressions for the October alert-composition investigation., test_alignment_fallback_names_direction_and_verified_size_relationship() (+20 more)

### Community 76 - "test_agent_workflow_contract.py"
Cohesion: 0.19
Nodes (10): _adapter_path(), _agent_names(), _agent_paths(), _load_toml(), Path, test_agent_definitions_have_matching_claude_adapters(), test_agent_definitions_have_required_schema(), test_agent_routing_references_existing_agents() (+2 more)

### Community 77 - "test_event_alert_delivery_quality_regressions.py"
Cohesion: 0.20
Nodes (19): final_event_alert_quality_flags(), Inspect the actual Telegram-ready message, never only the Render decision. Used…, test_specific_next_observation_is_not_generic(), _decision(), _market(), parametrize, Regressions from 2026-10-13 delivered Event Alerts. These assertions inspect…, _render() (+11 more)

### Community 78 - "test_heartbeat_postgres.py"
Cohesion: 0.22
Nodes (12): automatic_delivery_lock(), _lock_connection_slot(), Reserve capacity for persistence while an advisory-lock connection is held.…, Serialize automatic sends across event/heartbeat identities for one coin. A…, postgres_url(), asyncio, Real PostgreSQL locking checks; the SQLite process mutex cannot prove these…, test_postgres_lock_serializes_separate_workers_and_releases_on_cancellation() (+4 more)

### Community 79 - "test_news_ingestion.py"
Cohesion: 0.07
Nodes (35): fetch_crypto_news(), headline_is_relevant(), _keyword_matches(), _published_at(), datetime, Bounded, observable RSS fetching for the existing free news sources., Merge available feeds by publication age *before* applying the batch limit. A…, Low-cost, word-boundary-aware prefilter; not an alert decision. (+27 more)

### Community 80 - "select"
Cohesion: 0.22
Nodes (41): LlmOperationOutcome, NewsItem, NewsIntelligenceService, Analyze RSS news with cache and strict LLM budgets., select(), variations(), test_cached_high_priority_headline_does_not_consume_next_batch_slot(), test_fresh_article_outranks_older_high_priority_in_new_work_cap() (+33 more)

### Community 81 - "CCWBot Ops-Agent Report Analysis"
Cohesion: 0.20
Nodes (9): CCWBot Ops-Agent Report Analysis, Event Alert invariants, Evidence rules, Final report format, Goal, Investigation questions, Preflight, Report completion (+1 more)

### Community 82 - "datetime"
Cohesion: 0.05
Nodes (51): argparse, concurrent_futures, datetime, email_utils, http_server, Owner-approved, local-only pinned benchmark dependencies., Continue the already-started screen without overlapping inference models., Audit only aggregated benchmark budget and next-call feasibility (no inference). (+43 more)

### Community 83 - "event_analysis.py"
Cohesion: 0.14
Nodes (35): CanonicalEventKey, _claim_clause(), _claimed_percent(), _decimal_market_value(), _direction_for_claim(), directional_market_family(), _duration_minutes(), _duration_minutes_from_claim() (+27 more)

### Community 84 - "build_alert_evidence_payloads"
Cohesion: 0.29
Nodes (24): build_alert_evidence_payloads(), _numeric_context_json(), _period(), parametrize, _row(), test_alert_evidence_uses_hashes_without_raw_alert_text(), test_alert_quality_clean_delivered_event_alert_stays_clean(), test_alert_quality_detects_old_24h_label_in_delivered_event_alert() (+16 more)

### Community 85 - "CCW-20 paired final messages"
Cohesion: 0.09
Nodes (21): 10. ev_3c7f3da2e73e4b90 — ETH, 11. ev_7804adc277bd3333 — GRAM, 12. ev_345fc49db8255adf — GRAM, 13. ev_7b3325d2f2609480 — GRAM, 14. ev_1b39a518ede3c14f — GRAM, 15. ev_6500c5ad9f5364bc — GRAM, 16. ev_4bba21dd01bc8372 — SOL, 17. ev_1ea4cea05b78ed5c — SOL (+13 more)

### Community 86 - "event_chart.py"
Cohesion: 0.16
Nodes (18): ChartResult, _connectable_now_segment(), _draw_reference_shape(), _font(), _observed(), datetime, ImageDraw, Deterministic PNG chart from persisted, timestamped price observations only. (+10 more)

### Community 87 - "report_context.py"
Cohesion: 0.25
Nodes (20): _alert_quality_summary(), _attention_findings(), _collection_gaps(), _current_status(), _detector_sort_key(), _event_regression_summary(), _int(), _key_metrics() (+12 more)

### Community 88 - "FakeMessage"
Cohesion: 0.10
Nodes (12): AsyncFalse, AsyncNoop, AsyncTrue, CallbackQuery, FakeMessage, test_grant_premium_me_uses_current_admin_telegram_user_id(), test_plan_command_opens_inline_keyboard(), test_plan_my_plan_callback_edits_existing_message() (+4 more)

### Community 89 - "FakeResponse"
Cohesion: 0.19
Nodes (6): FakeClient, FakeResponse, test_get_coin_price_429_triggers_retry(), __init__(), test_get_with_retry_can_disable_stale_cache_after_429_retries(), test_get_with_retry_returns_stale_cache_after_429_retries()

### Community 90 - "Context Audit Report"
Cohesion: 0.07
Nodes (18): 1) Environment, 2) Measurement, 3) Plan by gradation, 4) Startup load, 5) Skill inventory, 6) MCP inventory, 7) Tools, 8) What was not done (+10 more)

### Community 91 - "_fixture"
Cohesion: 0.10
Nodes (27): Clear all breaker state (tests and controlled restarts)., reset_breakers(), _isolate_llm_breaker_state(), _test_verified_groq_routing(), _reset_state(), _estimate_tokens(), _fixture(), _measurement() (+19 more)

### Community 92 - "test_watchlist_ux.py"
Cohesion: 0.10
Nodes (51): build_my_plan_keyboard(), build_watchlist_keyboard(), is_admin_update(), Update, build_subscribe_message(), build_user_settings_message(), build_user_settings_render(), build_watchlist_message() (+43 more)

### Community 93 - "refresh_report_cache_scheduled"
Cohesion: 0.14
Nodes (21): schedule_report_cache_generation(), Market report use-case entrypoints., generate_daily_report_cache_job(), generate_weekly_report_cache_job(), _is_report_provider_backoff_active(), Scheduled cache refresh: regenerate unless the cache stays fresh past the grace…, One recovery attempt after a scheduled failure; no recurring retry storm., refresh_report_cache_scheduled() (+13 more)

### Community 94 - "ccwbot-deploy-safe.sh"
Cohesion: 0.21
Nodes (20): acquire_lock(), backup(), check_state_file(), clean_main(), COMPOSE_FILE, COMPOSE_PROFILES, COMPOSE_PROJECT_NAME, ensure_state_dir() (+12 more)

### Community 95 - "CCWBot Ops-Agent"
Cohesion: 0.17
Nodes (11): CCWBot Ops-Agent, Cleanup, Collection state, Container restart counts, Credential Rotation, Emergency Disable, Log pattern counting, News-candidate signal (+3 more)

### Community 96 - "test_event_alert_render_grounded_copy.py"
Cohesion: 0.20
Nodes (17): _contains_contradictory_direction(), _contradictory_observed_claim_in_level_action(), _guard_event_text_against_market_data(), _primary_market_direction_value(), Validate factual direction without rejecting future up/down scenarios. A…, test_release_conditional_levels_cannot_mask_false_observed_direction(), decision_for(), final_action() (+9 more)

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

### Community 105 - "render_decision_report_context"
Cohesion: 0.25
Nodes (18): _display_detector_status(), datetime, render_decision_report_context(), _report_status(), _unknown_section(), DetectorResult, Any, _period() (+10 more)

### Community 106 - "telegram_error"
Cohesion: 0.31
Nodes (8): handle_application_error(), Global python-telegram-bot error handler. Log-only: never sends anything to…, telegram_error, asyncio, parametrize, Global PTB error handler: concise WARNING for transient network errors, ERROR…, test_non_network_error_logs_error_with_traceback(), test_transient_network_error_logs_one_concise_warning()

### Community 107 - "test_event_alert_chart_markers.py"
Cohesion: 0.33
Nodes (17): event_chart(), marker(), Event Alert PNG reference-point and shared-delivery regressions., samples(), test_current_event_newer_and_different_from_latest_persisted_snapshot(), test_current_missing_cannot_fall_back_to_history(), test_discontinuous_history_remains_gap_free_and_partial(), test_four_reliable_markers_and_exact_observation_values() (+9 more)

### Community 108 - "test_price_service.py"
Cohesion: 0.13
Nodes (22): _extract_ton_coin_data_from_simple_price(), get_coin_market_data_batch(), Fetch market data for supported symbols with one CoinGecko request. Missing…, Accept only the current exact CoinGecko id for GRAM/legacy TON payloads., clean_price_caches(), clear_price_caches(), isolate_http_client_construction(), NoopAsyncClient (+14 more)

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

### Community 113 - "normalize_symbol"
Cohesion: 0.06
Nodes (64): _automatic_market_check_job_name(), _build_news_driven_event_instance_key(), _build_news_driven_event_key(), _calculate_price_change(), get_analysed_window_minutes(), _stable_float(), _coin_name(), _news_driven_identity() (+56 more)

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
Cohesion: 0.12
Nodes (21): Intercept only messages sent in the scope of a manual command/callback., _tracking(), TransientBot, with_close_button(), CoinGeckoRateLimitError, Exception, Raised when CoinGecko returns HTTP 429., ExtBot (+13 more)

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
Cohesion: 0.20
Nodes (33): UserPremiumSubscription, UserPremiumTrial, _activate_premium_from_telegram_stars_payment_locked(), expire_due_premium_trials(), get_payment_by_provider_id(), get_user_premium_subscription(), get_user_premium_trial(), grant_user_premium() (+25 more)

### Community 145 - "conftest.py"
Cohesion: 0.15
Nodes (11): _real_socket, socket, _guarded_create_connection(), _guarded_getaddrinfo(), _GuardedSocket, _is_loopback(), _is_loopback_address(), _raise_external_network_block() (+3 more)

### Community 147 - "LLMJsonResult"
Cohesion: 0.29
Nodes (4): LLMJsonResult, A compatible ``(raw_content, parsed)`` result with provider attribution., CorrelatedFallbackNewsLlm, tuple

### Community 148 - "Development"
Cohesion: 0.15
Nodes (8): Canonical Windows workspace, Development, Heartbeat delivery timestamp migration, Local Checks, Local Migration Recovery, Ops-Agent Development, Runtime Notes, Scope boundaries

### Community 149 - "test_market_heartbeat.py"
Cohesion: 0.07
Nodes (63): MarketHeartbeatDecision, MarketHeartbeatValidationError, Any, ValueError, Raised when LLM heartbeat JSON cannot be trusted., _required_text(), sanitize_heartbeat_message_body(), sanitize_heartbeat_possible_action() (+55 more)

### Community 150 - "os"
Cohesion: 0.07
Nodes (25): asyncpg, bot_services, build_llm_messages(), graphify reference: transcribe video and audio, Step 2.5 - Transcribe video / audio files (only if video files detected), ctypes, dotenv, openai (+17 more)

### Community 151 - "test_llm_config_budgets.py"
Cohesion: 0.04
Nodes (82): api_key_env(), base_url(), effective_max_tokens_for(), is_reasoning_model(), log_resolved_configuration(), max_tokens_for(), model_for(), Resolve the model for a (provider, call_type) pair from env, with defaults. (+74 more)

### Community 152 - "ChatGPT / Bridge / Codex Workflow"
Cohesion: 0.20
Nodes (10): 1. Execution hierarchy, 2. Evidence-first gate, 3. Planning without task-spec clutter, 4. Test-first and verification, 5. Repository workflow, 6. Agents and model routing, 7. PR readiness, 8. Tooling safety (+2 more)

### Community 153 - "provider_attempts"
Cohesion: 0.12
Nodes (19): provider_attempts(), provider_priority(), Resolve the ordered provider chain for a call type. Per-call-type override env…, Return the ordered concrete provider/model attempts for one logical LLM…, Case schema, Commands (offline by default), Frozen evidence contract, Independent blinded evaluation (+11 more)

### Community 156 - "automatic_price_check"
Cohesion: 0.11
Nodes (32): _build_event_analysis_id(), AlertRecipientResolution, automatic_price_check(), get_alert_recipients(), Return active market symbols independently of current recipient eligibility., Resolve eligible recipients once for one market event., Resolve recipients and preserve queryable reasons for filtered users., resolve_alert_recipient_outcomes() (+24 more)

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
Cohesion: 0.09
Nodes (48): schedule_automatic_market_check(), _build_admin_openai_costs_text(), _format_admin_alert_settings(), send_admin_callback_response(), _standalone_settings_origin(), Central callback-query router for Telegram inline keyboards., log_custom_emoji_ids(), price() (+40 more)

### Community 164 - "test_database_comments.py"
Cohesion: 0.16
Nodes (15): alembic_config, alembic_script, importlib, _alembic_head(), _load_comments_migration(), _load_event_alert_policy_migration(), _load_market_heartbeat_migration(), asyncio (+7 more)

### Community 166 - "What You Must Do When Invoked"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Locate the provisioned Graphify installation, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 168 - "test_alembic_migrations.py"
Cohesion: 0.15
Nodes (20): ast, Module, sqlalchemy_dialects, _clean_heartbeat_delivery_history(), _default_contract(), _down_revisions(), _literal_assignment(), _migration_config() (+12 more)

### Community 169 - "test_rich_403_preserves_safe_blocked_classification_without_raw_errors"
Cohesion: 0.08
Nodes (8): parametrize, test_integrity_conflict_preserves_terminal_delivery_reservation(), test_rich_403_preserves_safe_blocked_classification_without_raw_errors(), post(), test_rich_confirmed_telegram_rejections(), post(), test_rich_success_without_valid_receipt_is_uncertain(), post()

### Community 170 - "CCW-41 exploratory Reviewer-C agreement/disagreement"
Cohesion: 0.17
Nodes (11): CCW-41 exploratory Reviewer-C agreement/disagreement, Confirmed observations, Differences by symbol (A vs C), High-impact disagreement counts, Hypotheses requiring owner judgment, Limitations and decisions, Observed scenario and tag splits (A vs C), Original A/B disagreement subset (+3 more)

### Community 171 - "test_heartbeat_does_not_query_previous_event"
Cohesion: 0.20
Nodes (5): asyncio, test_heartbeat_does_not_query_previous_event(), get_snapshots(), test_shared_market_chart_reuses_one_session_and_global_event_not_recipient(), get_snapshots()

### Community 172 - "test_observability_reconciliation.py"
Cohesion: 0.26
Nodes (10): _payload(), _period(), Regression contracts for sanitized ops-agent evidence and report denominators., _row(), test_disjoint_recipients_do_not_trigger_global_family_cooldown(), test_docker_health_summary_uses_sanitized_collector_contract(), test_failed_delivery_does_not_create_sent_cooldown_violation(), test_missing_recipient_evidence_is_unknown_not_healthy() (+2 more)

### Community 173 - "bot/reports.py"
Cohesion: 0.07
Nodes (56): MarketReport, get_latest_market_report(), AsyncSession, datetime, Save one cached market report generation attempt., Return the newest cached market report for a cadence., save_market_report(), Mark news items as seen in PostgreSQL after they were used by the bot. (+48 more)

### Community 174 - "_runner_private.py"
Cohesion: 0.28
Nodes (15): call_once(), classify(), fail(), main(), persist(), datetime, quota_allows(), Finite direct-provider CCW-16 canary runner; Python stdlib only. This script… (+7 more)

### Community 175 - "_StructuredRecordBuffer"
Cohesion: 0.21
Nodes (4): Any, Keep newest safe records by byte budget and retain uncapped aggregate counts., _StructuredRecord, _StructuredRecordBuffer

### Community 176 - "types"
Cohesion: 0.23
Nodes (12): bot, bot_alerting, pil, decision(), history(), market_payload(), Event Alert metric/title and true observed NOW continuity regressions., test_24h_metric_and_unambiguous_header_in_all_delivery_formats() (+4 more)

### Community 178 - "test_price_handlers.py"
Cohesion: 0.45
Nodes (11): _context(), asyncio, test_manual_rate_limit_message_is_suppressed_per_chat(), test_price_hides_value_error_details_from_users(), test_price_maps_provider_errors_to_safe_user_messages(), test_price_normalizes_legacy_ton_alias_before_lookup(), test_price_rejects_unsupported_symbol_without_provider_call(), test_price_repeated_calls_are_not_ui_throttled() (+3 more)

### Community 180 - "/graphify"
Cohesion: 0.09
Nodes (18): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal, CCWBot safety overrides, For /graphify add and --watch, For /graphify query (+10 more)

### Community 181 - "ai_agent_groq.py"
Cohesion: 0.04
Nodes (72): Ground-truth evidence and limitations, Versioned artifacts, AnalysedWindowReference, _canonical_decimal_string(), _canonical_event_analysis_context(), _event_analysis_datetime(), _event_analysis_news_age_hours(), _event_analysis_news_summary() (+64 more)

### Community 182 - "Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26)"
Cohesion: 0.33
Nodes (5): Dataset and evaluation scope, Event Alert significance — owner blind review of six frozen Luna prompts (2026-10-26), Findings, Owner-label confusion on 58 decisive disagreement cases, Restrictions and next steps

### Community 183 - "0008_database_comments.py"
Cohesion: 0.48
Nodes (6): _apply_comments(), _column_names(), downgrade(), _is_postgresql(), database comments Revision ID: 0008_database_comments Revises:…, upgrade()

### Community 184 - "CCW-43 — Evidence-based Event Analysis prompt redesign"
Cohesion: 0.18
Nodes (10): CCW-43 — Evidence-based Event Analysis prompt redesign, Complete CCW-16 20-case stratified diagnostic, New complete prompt proposals (not evaluated), Priority 1: missed new meaningful extensions — false negatives, Priority 2: near-duplicate/noise alerts — false positives, Priority 3: reference and provider calibration drift, Reproducibility and handling, Result (+2 more)

### Community 185 - "test_exhausted_provider_chain_uses_verified_data_fallback"
Cohesion: 0.50
Nodes (5): asyncio, parametrize, test_exhausted_provider_chain_uses_verified_data_fallback(), test_unexpected_report_programming_error_does_not_become_fake_success(), _verified_payload()

### Community 186 - "test_news_driven_alerts.py"
Cohesion: 0.47
Nodes (5): _load_news_driven_alert_candidates(), asyncio, Regression coverage for the disabled standalone-news Event Alert path., test_news_driven_alerts_warning_logs_once_not_per_cycle(), test_news_driven_flag_cannot_bypass_product_policy()

### Community 188 - "0025_llm_operation_correlation.py"
Cohesion: 0.80
Nodes (5): downgrade(), _has_column(), _has_index(), _has_table(), upgrade()

### Community 189 - "news_context.py"
Cohesion: 0.07
Nodes (50): _alert_news_rank(), _candidate_news_relevance_label(), classify_news_relevance(), filter_news_for_symbol(), _format_candidate_news(), _has_gram_crypto_context(), _is_clearly_market_wide_news(), is_generic_news_item() (+42 more)

### Community 190 - "Repository Source of Truth"
Cohesion: 0.33
Nodes (5): Canonical ownership, Conflict resolution, No standing rules outside the repository, Repository bootstrap, Repository Source of Truth

### Community 192 - "pytest"
Cohesion: 0.15
Nodes (22): LLMRateLimitBackoffActive, Raised when a provider/model is already in temporary rate-limit backoff., GeminiProvider, get_provider(), Gemini provider (second fallback). Reached through Google's OpenAI-compatible…, Gemini 3.x deprecates explicit sampling parameters in generation config., pytest, _failed_provider() (+14 more)

### Community 193 - "validate_event_analysis_output"
Cohesion: 0.26
Nodes (13): Validate the single event-analysis schema accepted from the LLM., validate_event_analysis_output(), event_analysis_result(), parametrize, test_missing_required_field_is_still_rejected(), test_no_alert_accepts_confidence_value(), test_no_alert_accepts_empty_related_news_ids(), test_no_alert_accepts_null_urgency_confidence_and_null_related_news_ids() (+5 more)

### Community 194 - "CCWBot Operational Report — Unverified (No Production Bundle)"
Cohesion: 0.22
Nodes (8): CCWBot Operational Report — Unverified (No Production Bundle), Coverage, Evidence References, Executive Summary, Findings, Limitations / Evidence Gaps, Operational Metrics, Required Completion Gate

### Community 195 - "collections_abc"
Cohesion: 0.09
Nodes (8): _column_names(), downgrade(), _table_names(), upgrade(), downgrade(), _is_sqlite(), upgrade(), collections_abc

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

### Community 205 - "clean_news_title"
Cohesion: 0.36
Nodes (9): _format_event_related_context(), _format_market_heartbeat_related_context(), _format_related_context(), _safe_telegram_link_url(), clean_news_title(), clean_related_news_text(), test_clean_news_title_preserves_non_matching_titles(), test_clean_news_title_removes_known_source_suffixes() (+1 more)

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
Cohesion: 0.20
Nodes (9): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000) (+1 more)

### Community 213 - "RichDeliveryUncertain"
Cohesion: 0.28
Nodes (8): Exception, Single-request Telegram Bot API 10.2+ rich-message transport. PTB 22.8 does not…, The Telegram request might have been accepted: never send a duplicate., Send one rich message; reuse Telegram photo file_id when the API returns one.…, _returned_photo_file_id(), walk(), RichDeliveryUncertain, send_rich_event_alert()

### Community 214 - "_build_weekly_report_message"
Cohesion: 0.28
Nodes (9): _build_daily_report_message(), _build_weekly_report_message(), _format_report_coin_watchpoints(), _format_weekly_breadth(), Bound LLM verbosity without replacing or manufacturing market claims., One price/change table, plus model watchpoints with no repeated quotes., Non-repeated per-coin watchpoints carry useful weekly analysis., Scenario/level watchpoints only; do not echo summaries/price changes. (+1 more)

### Community 217 - "test_rich_chart_quality_detector.py"
Cohesion: 0.36
Nodes (8): _quality_issues(), test_optional_related_news_is_not_telegram_quality_failure(), _issues(), Regressions for rich Telegram charts persisted as plain alternatives., test_exact_chart_fallback_is_not_a_quality_failure_for_rich_alerts(), test_heartbeat_unavailable_is_not_suppressed_by_event_alert_exception(), test_other_placeholders_and_old_labels_remain_detectable(), test_other_unavailable_text_is_still_flagged()

### Community 222 - "0027_market_heartbeat_defaults.py"
Cohesion: 0.70
Nodes (4): downgrade(), _has_alert_frequency_column(), _set_default(), upgrade()

### Community 223 - "build_review.py"
Cohesion: 0.36
Nodes (10): candidate(), canon(), context(), csvwrite(), main(), Private read-only CCWBot market benchmark and independent review CSV exporter., run_psql(), safe() (+2 more)

### Community 224 - "0004_multicoin_delivery_idempotency.py"
Cohesion: 0.83
Nodes (3): downgrade(), _unique_constraint_names(), upgrade()

### Community 225 - "0007_unique_telegram_user_id.py"
Cohesion: 0.83
Nodes (3): _constraint_names(), downgrade(), upgrade()

### Community 233 - "convert_human_reviews.py"
Cohesion: 0.42
Nodes (8): finalize_reconciled(), labels_for(), main(), normalize_yes_no(), Convert two completed independent reviewer CSV sets to PR1 benchmark labels.…, rows(), score_disagreements(), validate_phase()

### Community 234 - "database.py"
Cohesion: 0.10
Nodes (27): do_run_migrations(), get_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), _collapse_whitespace(), _normalize_news_link(), datetime (+19 more)

### Community 235 - "asyncio"
Cohesion: 0.11
Nodes (8): asyncio, test_event_chart_file_id_reused_across_recipients_in_one_dispatch(), test_heartbeat_falls_back_to_styled_html_if_rich_adapter_has_no_token(), test_rich_ambiguous_error_never_falls_back_or_retries(), test_rich_confirmed_bad_request_falls_back_once(), test_rich_httpx_transport_uncertainty_prevents_fallback(), test_transport_reuses_file_id_and_handles_valid_response(), post()

## Knowledge Gaps
- **440 isolated node(s):** `$schema`, `title`, `type`, `additionalProperties`, `required` (+435 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1717 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `unknown()` connect `Observability Snippets` to `Ops-Agent Service`, `asyncio`, `CCWBot Ops-Agent Report Analysis`, `RichDeliveryUncertain`, `CCWBot Ops-Agent`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `RichDeliveryUncertain` connect `RichDeliveryUncertain` to `test_event_alert_rich_chart_ux.py`, `test_rich_market_report_delivery.py`, `test_rich_403_preserves_safe_blocked_classification_without_raw_errors`, `asyncio`, `Observability Snippets`, `bot/alerts.py`, `bot/reports.py`, `_deliver_market_event_alert`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `query()` connect `/graphify` to `test_event_alert_rich_chart_ux.py`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 170 inferred relationships involving `select()` (e.g. with `attach_analysis_to_market_event()` and `count_market_events()`) actually correct?**
  _`select()` has 170 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `Period` (e.g. with `_alert_quality()` and `_base_payload()`) actually correct?**
  _`Period` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Base` (e.g. with `build_session()` and `build_session_factory()`) actually correct?**
  _`Base` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `title`, `type` to the rest of the system?**
  _440 weakly-connected nodes found - possible documentation gaps or missing edges._