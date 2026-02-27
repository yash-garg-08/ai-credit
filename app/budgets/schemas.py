import uuid
from datetime import datetime

from pydantic import BaseModel

from app.budgets.models import BudgetPeriod


class BudgetCreate(BaseModel):
    period: BudgetPeriod
    limit_credits: int
    auto_disable: bool = True
    # Target level — provide exactly one:
    org_id: uuid.UUID | None = None
    workspace_id: uuid.UUID | None = None
    agent_group_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None


class BudgetResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    period: BudgetPeriod
    limit_credits: int
    auto_disable: bool
    org_id: uuid.UUID | None
    workspace_id: uuid.UUID | None
    agent_group_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
