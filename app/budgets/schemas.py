import uuid
from datetime import datetime

from pydantic import BaseModel, model_validator

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

    @model_validator(mode="after")
    def validate_single_target(self) -> "BudgetCreate":
        target_count = sum(
            1
            for value in (
                self.org_id,
                self.workspace_id,
                self.agent_group_id,
                self.agent_id,
            )
            if value is not None
        )
        if target_count != 1:
            raise ValueError(
                "Exactly one target must be provided: org_id, workspace_id, "
                "agent_group_id, or agent_id"
            )
        return self


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
