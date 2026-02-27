import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.ledger.models import TransactionType


class PurchaseCreditsRequest(BaseModel):
    group_id: uuid.UUID
    amount: int = Field(gt=0)  # credits to add (positive integer)
    idempotency_key: str | None = None


class LedgerEntryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    group_id: uuid.UUID
    amount: int
    type: TransactionType
    metadata_: dict | None = None
    created_at: datetime
