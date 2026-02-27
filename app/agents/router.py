import uuid

from fastapi import APIRouter

from app.agents import service as agent_service
from app.agents.schemas import (
    AgentCreate,
    AgentResponse,
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyResponse,
)
from app.core.dependencies import CurrentUser, DbSession
from app.core.tenancy import require_owned_agent, require_owned_agent_group

router = APIRouter(prefix="/agent-groups/{agent_group_id}/agents", tags=["agents"])
key_router = APIRouter(prefix="/agents/{agent_id}/keys", tags=["api-keys"])


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(agent_group_id: uuid.UUID, body: AgentCreate, user: CurrentUser, db: DbSession):
    await require_owned_agent_group(db, agent_group_id=agent_group_id, user_id=user.id)
    async with db.begin():
        agent = await agent_service.create_agent(db, agent_group_id=agent_group_id, name=body.name, description=body.description)
    return agent


@router.get("", response_model=list[AgentResponse])
async def list_agents(agent_group_id: uuid.UUID, user: CurrentUser, db: DbSession):
    await require_owned_agent_group(db, agent_group_id=agent_group_id, user_id=user.id)
    return await agent_service.list_agents_for_group(db, agent_group_id)


@key_router.post("", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(agent_id: uuid.UUID, body: ApiKeyCreate, user: CurrentUser, db: DbSession):
    await require_owned_agent(db, agent_id=agent_id, user_id=user.id)
    async with db.begin():
        api_key_obj, plaintext = await agent_service.create_api_key(db, agent_id=agent_id, name=body.name)
    return ApiKeyCreated(
        id=api_key_obj.id,
        agent_id=api_key_obj.agent_id,
        name=api_key_obj.name,
        key_suffix=api_key_obj.key_suffix,
        is_active=api_key_obj.is_active,
        created_at=api_key_obj.created_at,
        plaintext_key=plaintext,
    )


@key_router.delete("/{key_id}", status_code=204)
async def revoke_api_key(agent_id: uuid.UUID, key_id: uuid.UUID, user: CurrentUser, db: DbSession):
    await require_owned_agent(db, agent_id=agent_id, user_id=user.id)
    async with db.begin():
        await agent_service.revoke_api_key(
            db,
            key_id,
            reason="revoked by user",
            agent_id=agent_id,
        )
