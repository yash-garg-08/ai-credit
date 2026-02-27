import uuid
from datetime import datetime

from pydantic import BaseModel


class PolicyCreate(BaseModel):
    name: str
    # Target level — provide exactly one of:
    org_id: uuid.UUID | None = None
    workspace_id: uuid.UUID | None = None
    agent_group_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    # Rules:
    allowed_models: list[str] | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    rpm_limit: int | None = None


class PolicyResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    org_id: uuid.UUID | None
    workspace_id: uuid.UUID | None
    agent_group_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    allowed_models: list[str] | None
    max_input_tokens: int | None
    max_output_tokens: int | None
    rpm_limit: int | None
    is_active: bool
    created_at: datetime
