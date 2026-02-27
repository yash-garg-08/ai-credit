from fastapi import APIRouter

from app.budgets.models import Budget
from app.budgets.schemas import BudgetCreate, BudgetResponse
from app.core.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetResponse, status_code=201)
async def create_budget(body: BudgetCreate, user: CurrentUser, db: DbSession):
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
