import uuid

from fastapi import APIRouter

from app.budgets import service as budget_service
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


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    user: CurrentUser,
    db: DbSession,
    org_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    agent_group_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
):
    target_count = sum(
        1
        for value in (org_id, workspace_id, agent_group_id, agent_id)
        if value is not None
    )
    if target_count != 1:
        raise AppError(
            "Provide exactly one target query parameter: org_id, workspace_id, "
            "agent_group_id, or agent_id",
            status_code=400,
        )

    if org_id is not None:
        await require_owned_org(db, org_id=org_id, user_id=user.id)
    elif workspace_id is not None:
        await require_owned_workspace(db, workspace_id=workspace_id, user_id=user.id)
    elif agent_group_id is not None:
        await require_owned_agent_group(
            db, agent_group_id=agent_group_id, user_id=user.id
        )
    elif agent_id is not None:
        await require_owned_agent(db, agent_id=agent_id, user_id=user.id)

    budgets = await budget_service.list_budgets_for_target(
        db,
        org_id=org_id,
        workspace_id=workspace_id,
        agent_group_id=agent_group_id,
        agent_id=agent_id,
    )
    return [BudgetResponse.model_validate(b) for b in budgets]
