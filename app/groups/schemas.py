import uuid
from datetime import datetime

from pydantic import BaseModel

from app.groups.models import MemberRole


class CreateGroupRequest(BaseModel):
    name: str


class InviteRequest(BaseModel):
    email: str
    role: MemberRole = MemberRole.MEMBER


class GroupResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime


class BalanceResponse(BaseModel):
    group_id: uuid.UUID
    balance: int  # credits (integer)


class MembershipResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    group_id: uuid.UUID
    role: MemberRole
