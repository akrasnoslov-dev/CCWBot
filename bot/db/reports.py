"""Market report cache persistence.

Belongs here: daily/weekly market report cache reads and writes.
Does not belong here: report LLM calls, Telegram command handling, alert delivery,
or schema/model declarations.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.database import MarketReport


async def save_market_report(
    session: AsyncSession,
    *,
    report_type: str,
    llm_operation_id: str | None = None,
    generated_at: datetime,
    expires_at: datetime,
    status: str,
    raw_input_json: str | None,
    raw_output_json: str | None,
    telegram_message: str | None = None,
    error_message: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> MarketReport:
    """Save one cached market report generation attempt."""
    report = MarketReport(
        report_type=report_type.lower(),
        llm_operation_id=llm_operation_id,
        generated_at=generated_at,
        expires_at=expires_at,
        status=status,
        raw_input_json=raw_input_json,
        raw_output_json=raw_output_json,
        telegram_message=telegram_message,
        error_message=error_message,
        provider=provider,
        model=model,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report



async def get_latest_market_report(
    session: AsyncSession,
    *,
    report_type: str,
    statuses: set[str] | None = None,
) -> MarketReport | None:
    """Return the newest cached market report for a cadence."""
    statement = (
        select(MarketReport)
        .where(MarketReport.report_type == report_type.lower())
        .order_by(MarketReport.generated_at.desc(), MarketReport.id.desc())
        .limit(1)
    )
    if statuses is not None:
        statement = statement.where(MarketReport.status.in_(sorted(statuses)))
    return await session.scalar(statement)
