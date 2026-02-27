from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.ledger import service as ledger_service
from app.orgs import service as org_service
from app.orgs.schemas import OrgCreate, OrgResponse

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.post("", response_model=OrgResponse, status_code=201)
async def create_org(body: OrgCreate, user: CurrentUser, db: DbSession):
    async with db.begin():
        org = await org_service.create_organization(
            db, owner_id=user.id, name=body.name, description=body.description
        )
    return org


@router.get("", response_model=list[OrgResponse])
async def list_orgs(user: CurrentUser, db: DbSession):
    return await org_service.list_orgs_for_user(db, user.id)


@router.get("/{org_id}/balance")
async def get_org_balance(org_id: str, user: CurrentUser, db: DbSession):
    import uuid
    org = await org_service.get_org(db, uuid.UUID(org_id))
    if org is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Organization not found")
    balance = await ledger_service.get_group_balance(db, org.billing_group_id)
    return {"org_id": str(org.id), "balance": balance}
