import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.usage.models import UsageEvent


async def record_usage_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: Decimal,
    credits_charged: int,
    agent_id: uuid.UUID | None = None,
    latency_ms: int | None = None,
    status: str = "SUCCESS",
    error_message: str | None = None,
) -> UsageEvent:
    from app.usage.models import UsageStatus
    event = UsageEvent(
        user_id=user_id,
        group_id=group_id,
        agent_id=agent_id,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=cost_usd,
        credits_charged=credits_charged,
        latency_ms=latency_ms,
        status=UsageStatus(status),
        error_message=error_message,
    )
    db.add(event)
    await db.flush()
    return event


async def get_usage_history(
    db: AsyncSession, group_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[UsageEvent]:
    result = await db.execute(
        select(UsageEvent)
        .where(UsageEvent.group_id == group_id)
        .order_by(UsageEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_burn_rate(
    db: AsyncSession, group_id: uuid.UUID
) -> tuple[int, int]:
    """Returns (credits_last_24h, credits_last_7d)."""
    now = datetime.now(timezone.utc)

    async def _sum_since(since: datetime) -> int:
        result = await db.execute(
            select(func.coalesce(func.sum(UsageEvent.credits_charged), 0)).where(
                UsageEvent.group_id == group_id,
                UsageEvent.created_at >= since,
            )
        )
        return int(result.scalar_one())

    last_24h = await _sum_since(now - timedelta(hours=24))
    last_7d = await _sum_since(now - timedelta(days=7))
    return last_24h, last_7d


async def get_top_users(
    db: AsyncSession, group_id: uuid.UUID, limit: int = 10
) -> list[tuple[uuid.UUID, int]]:
    """Returns list of (user_id, total_credits) sorted desc."""
    result = await db.execute(
        select(
            UsageEvent.user_id,
            func.sum(UsageEvent.credits_charged).label("total"),
        )
        .where(UsageEvent.group_id == group_id)
        .group_by(UsageEvent.user_id)
        .order_by(func.sum(UsageEvent.credits_charged).desc())
        .limit(limit)
    )
    return [(row.user_id, int(row.total)) for row in result.all()]
