import uuid
from datetime import datetime

from pydantic import BaseModel


class OrgCreate(BaseModel):
    name: str
    description: str | None = None


class OrgResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    slug: str
    owner_id: uuid.UUID
    billing_group_id: uuid.UUID
    credits_per_usd: int
    is_active: bool
    description: str | None
    created_at: datetime
