import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_groups.models import AgentGroup
from app.agents.models import Agent
from app.core.exceptions import ForbiddenError, NotFoundError
from app.orgs.models import Organization
from app.workspaces.models import Workspace


def _assert_owner(org: Organization, user_id: uuid.UUID) -> None:
    if org.owner_id != user_id:
        raise ForbiddenError("You do not have access to this organization")


async def require_owned_org(
    db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise NotFoundError("Organization", str(org_id))
    _assert_owner(org, user_id)
    return org


async def require_owned_workspace(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Workspace, Organization]:
    result = await db.execute(
        select(Workspace, Organization)
        .join(Organization, Organization.id == Workspace.org_id)
        .where(Workspace.id == workspace_id)
    )
    row = result.one_or_none()
    if row is None:
        raise NotFoundError("Workspace", str(workspace_id))
    workspace, org = row
    _assert_owner(org, user_id)
    return workspace, org


async def require_owned_agent_group(
    db: AsyncSession, agent_group_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[AgentGroup, Workspace, Organization]:
    result = await db.execute(
        select(AgentGroup, Workspace, Organization)
        .join(Workspace, Workspace.id == AgentGroup.workspace_id)
        .join(Organization, Organization.id == Workspace.org_id)
        .where(AgentGroup.id == agent_group_id)
    )
    row = result.one_or_none()
    if row is None:
        raise NotFoundError("AgentGroup", str(agent_group_id))
    agent_group, workspace, org = row
    _assert_owner(org, user_id)
    return agent_group, workspace, org


async def require_owned_agent(
    db: AsyncSession, agent_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Agent, AgentGroup, Workspace, Organization]:
    result = await db.execute(
        select(Agent, AgentGroup, Workspace, Organization)
        .join(AgentGroup, AgentGroup.id == Agent.agent_group_id)
        .join(Workspace, Workspace.id == AgentGroup.workspace_id)
        .join(Organization, Organization.id == Workspace.org_id)
        .where(Agent.id == agent_id)
    )
    row = result.one_or_none()
    if row is None:
        raise NotFoundError("Agent", str(agent_id))
    agent, agent_group, workspace, org = row
    _assert_owner(org, user_id)
    return agent, agent_group, workspace, org
