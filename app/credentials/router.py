import uuid

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.credentials import service as cred_service
from app.credentials.schemas import CredentialCreate, CredentialResponse

router = APIRouter(prefix="/orgs/{org_id}/credentials", tags=["credentials"])


@router.post("", response_model=CredentialResponse, status_code=201)
async def add_credential(org_id: uuid.UUID, body: CredentialCreate, user: CurrentUser, db: DbSession):
    async with db.begin():
        cred = await cred_service.add_credential(
            db,
            org_id=org_id,
            provider=body.provider,
            plaintext_api_key=body.api_key,
            label=body.label,
            mode=body.mode,
        )
    return cred
