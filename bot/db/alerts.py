"""Alert delivery, market-event, event-analysis, and heartbeat persistence.

Belongs here: alert delivery reservations/status, market event identity rows,
event-analysis attempts, and cached market heartbeats.
Does not belong here: LLM provider calls, Telegram send/retry IO, recipient
eligibility policy, or schema/model declarations.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import (
    Alert,
    AlertDeliveryOutcome,
    EventAiAnalysis,
    MarketEvent,
    MarketHeartbeat,
    normalize_stored_severity,
    utc_now,
)


async def save_alert(
    session: AsyncSession,
    *,
    symbol: str,
    alert_type: str,
    message: str,
    sent_to_chat_id: int,
    market_event_id: int | None = None,
    market_heartbeat_id: int | None = None,
    event_ai_analysis_id: int | None = None,
    user_id: int | None = None,
    status: str | None = None,
    error_message: str | None = None,
    trigger_reason: str | None = None,
    trigger_source: str | None = None,
    numeric_context: str | None = None,
    thresholds_used: str | None = None,
    llm_severity: str | None = None,
    llm_reasoning_summary: str | None = None,
    fallback_mode: bool = False,
):
    alert = Alert(
        symbol=symbol.upper(),
        alert_type=alert_type,
        message=message,
        sent_to_chat_id=sent_to_chat_id,
        market_event_id=market_event_id,
        market_heartbeat_id=market_heartbeat_id,
        event_ai_analysis_id=event_ai_analysis_id,
        user_id=user_id,
        status=status,
        error_message=error_message,
        trigger_reason=trigger_reason,
        trigger_source=trigger_source,
        numeric_context=numeric_context,
        thresholds_used=thresholds_used,
        llm_severity=normalize_stored_severity(llm_severity),
        llm_reasoning_summary=llm_reasoning_summary,
        fallback_mode=fallback_mode,
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert



async def get_last_sent_alert_at(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    alert_type: str | None = None,
) -> datetime | None:
    """Return latest sent delivery time for a user+symbol frequency window."""
    statement = (
        select(func.max(Alert.created_at))
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.status == "sent")
    )
    if alert_type is not None:
        statement = statement.where(Alert.alert_type == alert_type)
    return await session.scalar(statement)



async def get_last_sent_event_alert_at_for_event_key(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    canonical_event_key: str,
    alert_type: str,
) -> datetime | None:
    """Return latest sent delivery for a user+symbol+canonical event key."""
    statement = (
        select(func.max(Alert.created_at))
        .select_from(Alert)
        .join(MarketEvent, Alert.market_event_id == MarketEvent.id)
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.alert_type == alert_type)
        .where(Alert.status == "sent")
        .where(MarketEvent.event_key == canonical_event_key)
    )
    return await session.scalar(statement)



async def get_latest_sent_event_alert_for_event_key(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    canonical_event_key: str,
    alert_type: str,
) -> Alert | None:
    """Return latest sent delivery row for a user+symbol+canonical event key."""
    statement = (
        select(Alert)
        .join(MarketEvent, Alert.market_event_id == MarketEvent.id)
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.alert_type == alert_type)
        .where(Alert.status == "sent")
        .where(MarketEvent.event_key == canonical_event_key)
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(1)
    )
    return await session.scalar(statement)



async def get_last_sent_alert(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    alert_type: str | None = None,
) -> Alert | None:
    """Return latest sent delivery row for a user and symbol."""
    statement = (
        select(Alert)
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.status == "sent")
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(1)
    )
    if alert_type is not None:
        statement = statement.where(Alert.alert_type == alert_type)
    return await session.scalar(statement)



async def get_latest_sent_alert_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    alert_type: str | None = None,
) -> Alert | None:
    """Return the latest sent delivery row for a symbol across all users."""
    statement = (
        select(Alert)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.status == "sent")
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(1)
    )
    if alert_type is not None:
        statement = statement.where(Alert.alert_type == alert_type)
    return await session.scalar(statement)



async def get_alert_delivery(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    market_event_id: int,
) -> Alert | None:
    return await session.scalar(
        select(Alert)
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.market_event_id == market_event_id)
        .limit(1)
    )



async def get_market_heartbeat_delivery(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    alert_type: str,
    market_heartbeat_id: int,
) -> Alert | None:
    return await session.scalar(
        select(Alert)
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.alert_type == alert_type)
        .where(Alert.market_heartbeat_id == market_heartbeat_id)
        .limit(1)
    )



async def reserve_alert_delivery(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    alert_type: str,
    sent_to_chat_id: int,
    market_event_id: int,
    event_ai_analysis_id: int | None,
    message: str,
    trigger_reason: str | None = None,
    trigger_source: str | None = None,
    numeric_context: str | None = None,
    thresholds_used: str | None = None,
    llm_severity: str | None = None,
    llm_reasoning_summary: str | None = None,
    fallback_mode: bool = False,
) -> tuple[Alert, bool]:
    """Reserve one delivery identity before sending.

    Returns (alert, created_or_retryable). Existing sent/pending rows are not
    retryable; failed rows are moved back to pending for another attempt.
    """
    existing = await get_alert_delivery(
        session,
        user_id=user_id,
        symbol=symbol,
        market_event_id=market_event_id,
    )
    if existing:
        if existing.status in {"sent", "pending", "retry_pending"}:
            return existing, False
        if existing.final_failed_at is not None:
            return existing, False
        existing.status = "pending"
        existing.error_message = None
        existing.retry_count = 0
        existing.last_error = None
        existing.next_retry_at = None
        existing.final_failed_at = None
        existing.message = message
        existing.sent_to_chat_id = sent_to_chat_id
        existing.event_ai_analysis_id = event_ai_analysis_id
        existing.trigger_reason = trigger_reason
        existing.trigger_source = trigger_source
        existing.numeric_context = numeric_context
        existing.thresholds_used = thresholds_used
        existing.llm_severity = normalize_stored_severity(llm_severity)
        existing.llm_reasoning_summary = llm_reasoning_summary
        existing.fallback_mode = fallback_mode
        await session.commit()
        await session.refresh(existing)
        return existing, True

    alert = Alert(
        symbol=symbol.upper(),
        alert_type=alert_type,
        message=message,
        sent_to_chat_id=sent_to_chat_id,
        market_event_id=market_event_id,
        event_ai_analysis_id=event_ai_analysis_id,
        user_id=user_id,
        status="pending",
        trigger_reason=trigger_reason,
        trigger_source=trigger_source,
        numeric_context=numeric_context,
        thresholds_used=thresholds_used,
        llm_severity=normalize_stored_severity(llm_severity),
        llm_reasoning_summary=llm_reasoning_summary,
        fallback_mode=fallback_mode,
    )
    session.add(alert)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_alert_delivery(
            session,
            user_id=user_id,
            symbol=symbol,
            market_event_id=market_event_id,
        )
        if existing is None:
            raise
        return existing, existing.status == "failed"
    await session.refresh(alert)
    return alert, True



async def reserve_market_heartbeat_delivery(
    session: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    alert_type: str,
    sent_to_chat_id: int,
    market_heartbeat_id: int,
    message: str,
    trigger_reason: str | None = None,
    trigger_source: str | None = None,
    numeric_context: str | None = None,
    llm_severity: str | None = None,
    llm_reasoning_summary: str | None = None,
) -> tuple[Alert, bool]:
    """Reserve one market-heartbeat delivery before sending."""
    existing = await session.scalar(
        select(Alert)
        .where(Alert.user_id == user_id)
        .where(Alert.symbol == symbol.upper())
        .where(Alert.alert_type == alert_type)
        .where(Alert.market_heartbeat_id == market_heartbeat_id)
        .with_for_update()
        .limit(1)
    )
    if existing:
        if existing.status in {"sent", "pending", "retry_pending"}:
            return existing, False
        if existing.final_failed_at is not None:
            return existing, False
        existing.status = "pending"
        existing.error_message = None
        existing.retry_count = 0
        existing.last_error = None
        existing.next_retry_at = None
        existing.final_failed_at = None
        existing.message = message
        existing.sent_to_chat_id = sent_to_chat_id
        existing.trigger_reason = trigger_reason
        existing.trigger_source = trigger_source
        existing.numeric_context = numeric_context
        existing.llm_severity = normalize_stored_severity(llm_severity)
        existing.llm_reasoning_summary = llm_reasoning_summary
        await session.commit()
        await session.refresh(existing)
        return existing, True

    alert = Alert(
        symbol=symbol.upper(),
        alert_type=alert_type,
        message=message,
        sent_to_chat_id=sent_to_chat_id,
        market_event_id=None,
        market_heartbeat_id=market_heartbeat_id,
        event_ai_analysis_id=None,
        user_id=user_id,
        status="pending",
        trigger_reason=trigger_reason,
        trigger_source=trigger_source,
        numeric_context=numeric_context,
        llm_severity=normalize_stored_severity(llm_severity),
        llm_reasoning_summary=llm_reasoning_summary,
    )
    session.add(alert)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_market_heartbeat_delivery(
            session,
            user_id=user_id,
            symbol=symbol,
            alert_type=alert_type,
            market_heartbeat_id=market_heartbeat_id,
        )
        if existing is None:
            raise
        return existing, existing.status == "failed" and existing.final_failed_at is None
    await session.refresh(alert)
    return alert, True



async def update_alert_delivery_status(
    session: AsyncSession,
    *,
    alert_id: int,
    status: str,
    error_message: str | None = None,
    retry_count: int | None = None,
    last_error: str | None = None,
    next_retry_at: datetime | None = None,
    final_failed_at: datetime | None = None,
) -> Alert | None:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        return None
    alert.status = status
    alert.error_message = error_message
    if retry_count is not None:
        alert.retry_count = retry_count
    if last_error is not None:
        alert.last_error = last_error
    if status == "sent":
        alert.error_message = None
        alert.next_retry_at = None
        alert.final_failed_at = None
    else:
        alert.next_retry_at = next_retry_at
        if final_failed_at is not None:
            alert.final_failed_at = final_failed_at
    await session.commit()
    await session.refresh(alert)
    return alert



async def save_alert_delivery_outcome(
    session: AsyncSession,
    *,
    symbol: str,
    alert_type: str,
    status: str,
    reason_code: str,
    market_event_id: int | None = None,
    event_ai_analysis_id: int | None = None,
    alert_id: int | None = None,
    user_id: int | None = None,
    sent_to_chat_id: int | None = None,
    recipient_considered: bool = False,
    recipient_eligible: bool | None = None,
    trigger_source: str | None = None,
    event_instance_key: str | None = None,
    semantic_family: str | None = None,
    detail: str | None = None,
) -> AlertDeliveryOutcome:
    outcome = AlertDeliveryOutcome(
        symbol=symbol.upper(),
        alert_type=alert_type,
        market_event_id=market_event_id,
        event_ai_analysis_id=event_ai_analysis_id,
        alert_id=alert_id,
        user_id=user_id,
        sent_to_chat_id=sent_to_chat_id,
        status=status,
        reason_code=reason_code,
        recipient_considered=recipient_considered,
        recipient_eligible=recipient_eligible,
        trigger_source=trigger_source,
        event_instance_key=event_instance_key,
        semantic_family=semantic_family,
        detail=detail,
    )
    session.add(outcome)
    await session.commit()
    await session.refresh(outcome)
    return outcome



async def get_or_create_market_event(
    session: AsyncSession,
    *,
    symbol: str,
    event_type: str,
    event_key: str,
    event_instance_key: str | None = None,
    price: float,
    price_change_percent: float,
    previous_price: float | None = None,
    last_24h_change: float | None = None,
    last_7d_change: float | None = None,
    detected_at: datetime | None = None,
) -> MarketEvent:
    """Return the market event for event_instance_key, creating it when needed."""
    instance_key = event_instance_key or event_key
    existing = await session.scalar(
        select(MarketEvent).where(MarketEvent.event_instance_key == instance_key).limit(1)
    )
    if existing:
        return existing

    market_event = MarketEvent(
        symbol=symbol.upper(),
        event_type=event_type,
        event_key=event_key,
        event_instance_key=instance_key,
        price=price,
        previous_price=previous_price,
        price_change_percent=price_change_percent,
        last_24h_change=last_24h_change,
        last_7d_change=last_7d_change,
        detected_at=detected_at or utc_now(),
    )
    session.add(market_event)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await session.scalar(
            select(MarketEvent).where(MarketEvent.event_instance_key == instance_key).limit(1)
        )
    await session.refresh(market_event)
    return market_event



async def get_market_event_by_instance_key(
    session: AsyncSession,
    *,
    event_instance_key: str,
) -> MarketEvent | None:
    """Return an existing market event by stable event instance key."""
    return await session.scalar(
        select(MarketEvent).where(MarketEvent.event_instance_key == event_instance_key).limit(1)
    )



async def get_event_ai_analysis(
    session: AsyncSession, *, market_event_id: int, input_hash: str
) -> EventAiAnalysis | None:
    """Return an existing AI analysis for the event/input pair if present."""
    return await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.market_event_id == market_event_id)
        .where(EventAiAnalysis.input_hash == input_hash)
        .limit(1)
    )



async def get_latest_success_event_ai_analysis(
    session: AsyncSession,
    *,
    market_event_id: int,
) -> EventAiAnalysis | None:
    """Return any successful saved analysis for a market event."""
    return await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.market_event_id == market_event_id)
        .where(EventAiAnalysis.status.in_(["success", "completed"]))
        .where(EventAiAnalysis.plain_text.isnot(None))
        .order_by(EventAiAnalysis.id.asc())
        .limit(1)
    )



async def save_event_ai_analysis(
    session: AsyncSession,
    *,
    market_event_id: int,
    provider: str,
    model: str,
    input_hash: str,
    analysis_text: str | None = None,
    plain_text: str | None = None,
    html_text: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    estimated_cost: float | None = None,
    status: str = "completed",
    error_message: str | None = None,
) -> EventAiAnalysis:
    """Save one AI analysis row for a market event."""
    existing = await get_event_ai_analysis(
        session, market_event_id=market_event_id, input_hash=input_hash
    )
    if existing:
        return existing

    analysis = EventAiAnalysis(
        market_event_id=market_event_id,
        provider=provider,
        model=model,
        input_hash=input_hash,
        analysis_text=analysis_text,
        plain_text=plain_text,
        html_text=html_text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        status=status,
        error_message=error_message,
    )
    session.add(analysis)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await get_event_ai_analysis(
            session, market_event_id=market_event_id, input_hash=input_hash
        )
    await session.refresh(analysis)
    return analysis



async def save_event_llm_analysis(
    session: AsyncSession,
    *,
    analysis_id: str,
    symbol: str,
    input_hash: str,
    raw_input_json: str,
    raw_output_json: str | None,
    status: str,
    provider: str = "groq",
    model: str = "",
    analysis_type: str = "event_analysis",
    market_event_id: int | None = None,
    parsed_result_json: str | None = None,
    should_alert: bool | None = None,
    event_key: str | None = None,
    title: str | None = None,
    message_body: str | None = None,
    related_news_ids: str | None = None,
    possible_action: str | None = None,
    urgency: str | None = None,
    confidence: str | None = None,
    reason_for_no_alert: str | None = None,
    error_message: str | None = None,
    error_reason: str | None = None,
    plain_text: str | None = None,
    html_text: str | None = None,
) -> EventAiAnalysis:
    """Save one raw LLM event-analysis attempt."""
    existing = await session.scalar(
        select(EventAiAnalysis).where(EventAiAnalysis.analysis_id == analysis_id).limit(1)
    )
    if existing:
        return existing

    analysis = EventAiAnalysis(
        market_event_id=market_event_id,
        analysis_id=analysis_id,
        symbol=symbol.upper(),
        analysis_type=analysis_type,
        provider=provider,
        model=model,
        input_hash=input_hash,
        raw_input_json=raw_input_json,
        raw_output_json=raw_output_json,
        parsed_result_json=parsed_result_json,
        should_alert=should_alert,
        event_key=event_key,
        title=title,
        message_body=message_body,
        related_news_ids=related_news_ids,
        possible_action=possible_action,
        urgency=urgency,
        confidence=confidence,
        reason_for_no_alert=reason_for_no_alert,
        analysis_text=raw_output_json,
        plain_text=plain_text,
        html_text=html_text,
        status=status,
        error_message=error_message,
        error_reason=error_reason,
    )
    session.add(analysis)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await session.scalar(
            select(EventAiAnalysis).where(EventAiAnalysis.analysis_id == analysis_id).limit(1)
        )
    await session.refresh(analysis)
    return analysis



async def attach_analysis_to_market_event(
    session: AsyncSession,
    *,
    analysis_id: str,
    market_event_id: int,
    plain_text: str | None = None,
    html_text: str | None = None,
) -> EventAiAnalysis | None:
    """Attach a previously saved event analysis to the event created from its decision."""
    analysis = await session.scalar(
        select(EventAiAnalysis).where(EventAiAnalysis.analysis_id == analysis_id).limit(1)
    )
    if analysis is None:
        return None
    analysis.market_event_id = market_event_id
    if plain_text is not None:
        analysis.plain_text = plain_text
    if html_text is not None:
        analysis.html_text = html_text
    await session.commit()
    await session.refresh(analysis)
    return analysis



async def save_market_heartbeat(
    session: AsyncSession,
    *,
    symbol: str,
    generated_at: datetime,
    raw_input_json: str | None,
    raw_output_json: str | None,
    title: str | None = None,
    message_body: str | None = None,
    related_news_ids: str | None = None,
    possible_action: str | None = None,
    confidence: str | None = None,
    status: str = "completed",
    error_message: str | None = None,
) -> MarketHeartbeat:
    heartbeat = MarketHeartbeat(
        symbol=symbol.upper(),
        generated_at=generated_at,
        raw_input_json=raw_input_json,
        raw_output_json=raw_output_json,
        title=title,
        message_body=message_body,
        related_news_ids=related_news_ids,
        possible_action=possible_action,
        confidence=confidence,
        status=status,
        error_message=error_message,
    )
    session.add(heartbeat)
    await session.commit()
    await session.refresh(heartbeat)
    return heartbeat



async def get_latest_market_heartbeat(
    session: AsyncSession,
    *,
    symbol: str,
    statuses: set[str] | None = None,
) -> MarketHeartbeat | None:
    statement = (
        select(MarketHeartbeat)
        .where(MarketHeartbeat.symbol == symbol.upper())
        .order_by(MarketHeartbeat.generated_at.desc(), MarketHeartbeat.id.desc())
        .limit(1)
    )
    if statuses is not None:
        statement = statement.where(MarketHeartbeat.status.in_(sorted(statuses)))
    return await session.scalar(statement)



async def get_latest_event_analysis_attempt(
    session: AsyncSession,
) -> EventAiAnalysis | None:
    """Return the most recent LLM event-analysis attempt."""
    return await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.analysis_type == "event_analysis")
        .order_by(EventAiAnalysis.created_at.desc(), EventAiAnalysis.id.desc())
        .limit(1)
    )



async def get_latest_event_analysis_by_statuses(
    session: AsyncSession,
    statuses: set[str],
) -> EventAiAnalysis | None:
    """Return the latest event-analysis row whose status is in statuses."""
    return await session.scalar(
        select(EventAiAnalysis)
        .where(EventAiAnalysis.analysis_type == "event_analysis")
        .where(EventAiAnalysis.status.in_(sorted(statuses)))
        .order_by(EventAiAnalysis.created_at.desc(), EventAiAnalysis.id.desc())
        .limit(1)
    )



async def count_market_events(session: AsyncSession, symbol: str | None = None) -> int:
    """Return the number of stored market events, optionally for one symbol."""
    statement = select(func.count()).select_from(MarketEvent)
    if symbol:
        statement = statement.where(MarketEvent.symbol == symbol.upper())
    return int(await session.scalar(statement) or 0)



async def get_recent_market_events(
    session: AsyncSession, *, symbol: str | None = None, limit: int = 20
) -> list[MarketEvent]:
    """Return recent market events, newest first."""
    statement = select(MarketEvent)
    if symbol:
        statement = statement.where(MarketEvent.symbol == symbol.upper())
    result = await session.scalars(
        statement.order_by(MarketEvent.detected_at.desc(), MarketEvent.id.desc()).limit(limit)
    )
    return list(result.all())
