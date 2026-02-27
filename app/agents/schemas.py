import uuid
from datetime import datetime

from pydantic import BaseModel

from app.agents.models import AgentStatus


class AgentCreate(BaseModel):
    name: str
    description: str | None = None


class AgentResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    agent_group_id: uuid.UUID
    name: str
    description: str | None
    status: AgentStatus
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    agent_id: uuid.UUID
    name: str
    key_suffix: str
    is_active: bool
    created_at: datetime


class ApiKeyCreated(ApiKeyResponse):
    """Returned once at creation — includes the plaintext key."""
    plaintext_key: str
