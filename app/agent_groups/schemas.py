import uuid
from datetime import datetime

from pydantic import BaseModel


class AgentGroupCreate(BaseModel):
    name: str
    description: str | None = None


class AgentGroupResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
