import uuid

from fastapi import APIRouter

from app.agent_groups import service as ag_service
from app.agent_groups.schemas import AgentGroupCreate, AgentGroupResponse
from app.core.dependencies import CurrentUser, DbSession
from app.core.tenancy import require_owned_workspace

router = APIRouter(prefix="/workspaces/{workspace_id}/agent-groups", tags=["agent-groups"])


@router.post("", response_model=AgentGroupResponse, status_code=201)
async def create_agent_group(workspace_id: uuid.UUID, body: AgentGroupCreate, user: CurrentUser, db: DbSession):
    await require_owned_workspace(db, workspace_id=workspace_id, user_id=user.id)
    async with db.begin():
        ag = await ag_service.create_agent_group(db, workspace_id=workspace_id, name=body.name, description=body.description)
    return ag


@router.get("", response_model=list[AgentGroupResponse])
async def list_agent_groups(workspace_id: uuid.UUID, user: CurrentUser, db: DbSession):
    await require_owned_workspace(db, workspace_id=workspace_id, user_id=user.id)
    return await ag_service.list_agent_groups(db, workspace_id)
