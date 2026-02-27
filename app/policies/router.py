from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import AppError
from app.core.tenancy import (
    require_owned_agent,
    require_owned_agent_group,
    require_owned_org,
    require_owned_workspace,
)
from app.policies.models import Policy
from app.policies.schemas import PolicyCreate, PolicyResponse

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(body: PolicyCreate, user: CurrentUser, db: DbSession):
    if body.org_id is not None:
        await require_owned_org(db, org_id=body.org_id, user_id=user.id)
    elif body.workspace_id is not None:
        await require_owned_workspace(db, workspace_id=body.workspace_id, user_id=user.id)
    elif body.agent_group_id is not None:
        await require_owned_agent_group(
            db, agent_group_id=body.agent_group_id, user_id=user.id
        )
    elif body.agent_id is not None:
        await require_owned_agent(db, agent_id=body.agent_id, user_id=user.id)
    else:
        raise AppError("Policy target is required", status_code=400)

    async with db.begin():
        policy = Policy(
            name=body.name,
            org_id=body.org_id,
            workspace_id=body.workspace_id,
            agent_group_id=body.agent_group_id,
            agent_id=body.agent_id,
            allowed_models=body.allowed_models,
            max_input_tokens=body.max_input_tokens,
            max_output_tokens=body.max_output_tokens,
            rpm_limit=body.rpm_limit,
        )
        db.add(policy)
        await db.flush()
    return policy
