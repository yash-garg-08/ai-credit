import uuid
from datetime import datetime

from pydantic import BaseModel

from app.credentials.models import CredentialMode


class CredentialCreate(BaseModel):
    provider: str
    api_key: str  # plaintext — encrypted before storage
    label: str | None = None
    mode: CredentialMode = CredentialMode.BYOK


class CredentialResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    org_id: uuid.UUID
    provider: str
    mode: CredentialMode
    label: str | None
    is_active: bool
    created_at: datetime
    # Never expose encrypted_api_key
