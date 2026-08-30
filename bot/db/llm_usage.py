"""LLM usage telemetry persistence.

Belongs here: saving and updating provider/model token and rate-limit telemetry.
Does not belong here: LLM provider calls, prompt construction, alert delivery,
or schema/model declarations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import LlmUsageLog


async def save_llm_usage_log(
    session: AsyncSession,
    *,
    provider: str,
    model: str,
    call_type: str,
    llm_operation_id: str | None = None,
    status: str,
    symbol: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    input_chars: int | None = None,
    output_chars: int | None = None,
    max_tokens: int | None = None,
    rate_limit_limit_requests: str | None = None,
    rate_limit_remaining_requests: str | None = None,
    rate_limit_reset_requests: str | None = None,
    rate_limit_limit_tokens: str | None = None,
    rate_limit_remaining_tokens: str | None = None,
    rate_limit_reset_tokens: str | None = None,
    retry_after: str | None = None,
    provider_request_id: str | None = None,
    error_reason: str | None = None,
    error_message: str | None = None,
) -> LlmUsageLog:
    """Save one LLM usage telemetry row."""
    row = LlmUsageLog(
        provider=provider,
        model=model,
        call_type=call_type,
        llm_operation_id=llm_operation_id,
        symbol=symbol.upper() if symbol else None,
        status=status,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        input_chars=input_chars,
        output_chars=output_chars,
        max_tokens=max_tokens,
        rate_limit_limit_requests=rate_limit_limit_requests,
        rate_limit_remaining_requests=rate_limit_remaining_requests,
        rate_limit_reset_requests=rate_limit_reset_requests,
        rate_limit_limit_tokens=rate_limit_limit_tokens,
        rate_limit_remaining_tokens=rate_limit_remaining_tokens,
        rate_limit_reset_tokens=rate_limit_reset_tokens,
        retry_after=retry_after,
        provider_request_id=provider_request_id,
        error_reason=error_reason,
        error_message=error_message,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row



async def update_llm_usage_log_status(
    session: AsyncSession,
    *,
    usage_log_id: int,
    status: str,
    error_reason: str | None = None,
    error_message: str | None = None,
) -> LlmUsageLog | None:
    """Update a usage row when downstream JSON schema validation fails."""
    row = await session.get(LlmUsageLog, usage_log_id)
    if row is None:
        return None
    row.status = status
    row.error_reason = error_reason
    row.error_message = error_message
    await session.commit()
    await session.refresh(row)
    return row
