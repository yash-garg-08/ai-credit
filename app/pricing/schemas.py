import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PricingRuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    provider: str
    model: str
    input_cost_per_1k: Decimal
    output_cost_per_1k: Decimal
    created_at: datetime


class CostCalculation(BaseModel):
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    credits: int
