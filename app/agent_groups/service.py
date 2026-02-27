"""AgentGroup management service."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_groups.models import AgentGroup


async def create_agent_group(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    name: str,
    description: str | None = None,
) -> AgentGroup:
    group = AgentGroup(workspace_id=workspace_id, name=name, description=description)
    db.add(group)
    await db.flush()
    return group


async def list_agent_groups(db: AsyncSession, workspace_id: uuid.UUID) -> list[AgentGroup]:
    result = await db.execute(
        select(AgentGroup).where(AgentGroup.workspace_id == workspace_id).order_by(AgentGroup.created_at)
    )
    return list(result.scalars().all())


async def get_agent_group(db: AsyncSession, agent_group_id: uuid.UUID) -> AgentGroup | None:
    result = await db.execute(select(AgentGroup).where(AgentGroup.id == agent_group_id))
    return result.scalar_one_or_none()
