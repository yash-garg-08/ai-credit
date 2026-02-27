from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import AppError
from app.groups.service import get_user_membership
from app.ledger import service
from app.ledger.models import TransactionType
from app.ledger.schemas import LedgerEntryResponse, PurchaseCreditsRequest

router = APIRouter(prefix="/credits", tags=["credits"])


@router.post("/purchase", response_model=LedgerEntryResponse, status_code=201)
async def purchase_credits(
    body: PurchaseCreditsRequest, db: DbSession, user: CurrentUser
) -> LedgerEntryResponse:
    # Verify user is member of the group
    await get_user_membership(db, user.id, body.group_id)
    if body.amount <= 0:
        raise AppError("Purchase amount must be greater than 0", status_code=400)

    entry = await service.append_entry(
        db,
        group_id=body.group_id,
        amount=body.amount,
        type=TransactionType.CREDIT_PURCHASE,
        idempotency_key=body.idempotency_key,
        metadata={"purchased_by": str(user.id)},
    )
    await db.commit()
    await db.refresh(entry)
    return LedgerEntryResponse.model_validate(entry)
