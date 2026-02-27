from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.policies.models import Policy
from app.policies.schemas import PolicyCreate, PolicyResponse

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(body: PolicyCreate, user: CurrentUser, db: DbSession):
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
