import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class UsageRequest(BaseModel):
    group_id: uuid.UUID
    provider: str
    model: str
    messages: list[dict]  # [{"role": "user", "content": "..."}]
    request_id: str  # client-provided idempotency key


class UsageResponse(BaseModel):
    request_id: str
    response: str
    input_tokens: int
    output_tokens: int
    credits_charged: int


class UsageEventResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    group_id: uuid.UUID
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: Decimal
    credits_charged: int
    created_at: datetime


class UsageHistoryParams(BaseModel):
    group_id: uuid.UUID
    limit: int = 50
    offset: int = 0


class BurnRateResponse(BaseModel):
    group_id: uuid.UUID
    credits_last_24h: int
    credits_last_7d: int


class TopUserResponse(BaseModel):
    user_id: uuid.UUID
    total_credits: int
