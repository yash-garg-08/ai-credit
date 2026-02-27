"""Budget enforcement — multi-level credit cap checking.

Hierarchy: Org → Workspace → AgentGroup → Agent.
All levels are checked; any exceeded level blocks the request.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.budgets.models import Budget, BudgetPeriod
from app.core.exceptions import AppError
from app.db.session import async_session_factory
from app.usage.models import UsageEvent, UsageStatus


def _period_start(period: BudgetPeriod) -> datetime | None:
    """Return the start of the current period, or None for TOTAL (all time)."""
    now = datetime.now(timezone.utc)
    if period == BudgetPeriod.DAILY:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == BudgetPeriod.MONTHLY:
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # TOTAL
        return None


async def _sum_usage_for_period(
    db: AsyncSession,
    *,
    org_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    agent_group_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
    since: datetime | None,
) -> int:
    """Sum credits_charged for successful events scoped to a hierarchy level."""
    # We need to join through the hierarchy to filter by level
    # For simplicity, filter usage_events by agent_id when available,
    # then join up the tree otherwise via subqueries.

    from app.agents.models import Agent
    from app.agent_groups.models import AgentGroup
    from app.workspaces.models import Workspace

    q = select(func.coalesce(func.sum(UsageEvent.credits_charged), 0)).where(
        UsageEvent.status == UsageStatus.SUCCESS
    )

    if since is not None:
        q = q.where(UsageEvent.created_at >= since)

    if agent_id is not None:
        q = q.where(UsageEvent.agent_id == agent_id)
    elif agent_group_id is not None:
        # All agents in this agent_group
        agent_ids_sq = select(Agent.id).where(Agent.agent_group_id == agent_group_id).scalar_subquery()
        q = q.where(UsageEvent.agent_id.in_(agent_ids_sq))
    elif workspace_id is not None:
        # All agents in all agent_groups in this workspace
        group_ids_sq = select(AgentGroup.id).where(AgentGroup.workspace_id == workspace_id).scalar_subquery()
        agent_ids_sq = select(Agent.id).where(Agent.agent_group_id.in_(group_ids_sq)).scalar_subquery()
        q = q.where(UsageEvent.agent_id.in_(agent_ids_sq))
    elif org_id is not None:
        # All agents in org (via workspace → agent_group → agent)
        ws_ids_sq = select(Workspace.id).where(Workspace.org_id == org_id).scalar_subquery()
        group_ids_sq = select(AgentGroup.id).where(AgentGroup.workspace_id.in_(ws_ids_sq)).scalar_subquery()
        agent_ids_sq = select(Agent.id).where(Agent.agent_group_id.in_(group_ids_sq)).scalar_subquery()
        q = q.where(UsageEvent.agent_id.in_(agent_ids_sq))

    result = await db.execute(q)
    return int(result.scalar() or 0)


async def _auto_disable_target(
    *,
    budget: Budget,
    fallback_agent_id: uuid.UUID,
) -> None:
    """Persist budget-based disable in its own transaction."""
    from app.agent_groups.models import AgentGroup
    from app.agents.models import Agent, AgentStatus
    from app.orgs.models import Organization
    from app.workspaces.models import Workspace

    async with async_session_factory() as write_db:
        async with write_db.begin():
            if budget.agent_id is not None:
                agent = await write_db.get(Agent, budget.agent_id)
                if agent is not None:
                    agent.status = AgentStatus.BUDGET_EXHAUSTED
                return

            if budget.agent_group_id is not None:
                agent_group = await write_db.get(AgentGroup, budget.agent_group_id)
                if agent_group is not None:
                    agent_group.is_active = False
                return

            if budget.workspace_id is not None:
                workspace = await write_db.get(Workspace, budget.workspace_id)
                if workspace is not None:
                    workspace.is_active = False
                return

            if budget.org_id is not None:
                org = await write_db.get(Organization, budget.org_id)
                if org is not None:
                    org.is_active = False
                return

            # Defensive fallback; target should always be set due schema/DB constraints.
            agent = await write_db.get(Agent, fallback_agent_id)
            if agent is not None:
                agent.status = AgentStatus.BUDGET_EXHAUSTED


async def check_budgets(
    db: AsyncSession,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    agent_group_id: uuid.UUID,
    agent_id: uuid.UUID,
    required_credits: int,
) -> None:
    """
    Check all active budgets at every hierarchy level.
    Raises AppError(402) if any budget would be exceeded.
    """
    budgets_result = await db.execute(
        select(Budget).where(
            Budget.is_active == True,  # noqa: E712
            (
                (Budget.org_id == org_id)
                | (Budget.workspace_id == workspace_id)
                | (Budget.agent_group_id == agent_group_id)
                | (Budget.agent_id == agent_id)
            ),
        )
    )
    budgets = list(budgets_result.scalars().all())

    for budget in budgets:
        since = _period_start(budget.period)
        current_spend = await _sum_usage_for_period(
            db,
            org_id=budget.org_id,
            workspace_id=budget.workspace_id,
            agent_group_id=budget.agent_group_id,
            agent_id=budget.agent_id,
            since=since,
        )
        if current_spend + required_credits > budget.limit_credits:
            level = (
                "organization" if budget.org_id
                else "workspace" if budget.workspace_id
                else "agent_group" if budget.agent_group_id
                else "agent"
            )
            detail = ""
            if budget.auto_disable:
                await _auto_disable_target(
                    budget=budget,
                    fallback_agent_id=agent_id,
                )
                detail = " Target has been auto-disabled."
            raise AppError(
                f"Budget exceeded at {level} level ({budget.period.value}): "
                f"current={current_spend}, limit={budget.limit_credits}, "
                f"required={required_credits}.{detail}",
                status_code=402,
            )


async def list_budgets_for_target(
    db: AsyncSession,
    *,
    org_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    agent_group_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
) -> list[Budget]:
    q = select(Budget)
    if org_id is not None:
        q = q.where(Budget.org_id == org_id)
    elif workspace_id is not None:
        q = q.where(Budget.workspace_id == workspace_id)
    elif agent_group_id is not None:
        q = q.where(Budget.agent_group_id == agent_group_id)
    elif agent_id is not None:
        q = q.where(Budget.agent_id == agent_id)
    else:
        return []

    q = q.order_by(Budget.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())
