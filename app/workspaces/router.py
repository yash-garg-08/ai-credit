import uuid

from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUser, DbSession
from app.workspaces import service as ws_service
from app.workspaces.schemas import WorkspaceCreate, WorkspaceResponse

router = APIRouter(prefix="/orgs/{org_id}/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(org_id: uuid.UUID, body: WorkspaceCreate, user: CurrentUser, db: DbSession):
    async with db.begin():
        ws = await ws_service.create_workspace(db, org_id=org_id, name=body.name, description=body.description)
    return ws


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(org_id: uuid.UUID, user: CurrentUser, db: DbSession):
    return await ws_service.list_workspaces(db, org_id)
