from fastapi import APIRouter

from app.budgets.models import Budget
from app.budgets.schemas import BudgetCreate, BudgetResponse
from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import AppError
from app.core.tenancy import (
    require_owned_agent,
    require_owned_agent_group,
    require_owned_org,
    require_owned_workspace,
)

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetResponse, status_code=201)
async def create_budget(body: BudgetCreate, user: CurrentUser, db: DbSession):
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
        raise AppError("Budget target is required", status_code=400)

    async with db.begin():
        budget = Budget(
            period=body.period,
            limit_credits=body.limit_credits,
            auto_disable=body.auto_disable,
            org_id=body.org_id,
            workspace_id=body.workspace_id,
            agent_group_id=body.agent_group_id,
            agent_id=body.agent_id,
        )
        db.add(budget)
        await db.flush()
    return budget
