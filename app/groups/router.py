import uuid

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.groups import service
from app.groups.schemas import (
    BalanceResponse,
    CreateGroupRequest,
    GroupResponse,
    InviteRequest,
    MembershipResponse,
)
from app.ledger.service import get_group_balance

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("/me", response_model=list[GroupResponse])
async def my_groups(db: DbSession, user: CurrentUser) -> list[GroupResponse]:
    groups = await service.get_user_groups(db, user.id)
    return [GroupResponse.model_validate(g) for g in groups]


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    body: CreateGroupRequest, db: DbSession, user: CurrentUser
) -> GroupResponse:
    group = await service.create_group(db, body.name, user)
    return GroupResponse.model_validate(group)


@router.post("/{group_id}/invite", response_model=MembershipResponse, status_code=201)
async def invite_user(
    group_id: uuid.UUID,
    body: InviteRequest,
    db: DbSession,
    user: CurrentUser,
) -> MembershipResponse:
    membership = await service.invite_user(db, group_id, user, body.email, body.role)
    return MembershipResponse.model_validate(membership)


@router.get("/{group_id}/balance", response_model=BalanceResponse)
async def balance(
    group_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> BalanceResponse:
    # Verify membership
    await service.get_user_membership(db, user.id, group_id)
    bal = await get_group_balance(db, group_id)
    return BalanceResponse(group_id=group_id, balance=bal)
