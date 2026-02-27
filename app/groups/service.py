import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.exceptions import ForbiddenError, NotFoundError
from app.groups.models import Group, Membership, MemberRole


async def create_group(db: AsyncSession, name: str, owner: User) -> Group:
    group = Group(name=name, owner_id=owner.id)
    db.add(group)
    await db.flush()

    membership = Membership(user_id=owner.id, group_id=group.id, role=MemberRole.ADMIN)
    db.add(membership)
    await db.commit()
    await db.refresh(group)
    return group


async def invite_user(
    db: AsyncSession,
    group_id: uuid.UUID,
    inviter: User,
    invitee_email: str,
    role: MemberRole,
) -> Membership:
    # Verify group exists
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if group is None:
        raise NotFoundError("Group", str(group_id))

    # Verify inviter is admin
    result = await db.execute(
        select(Membership).where(
            Membership.group_id == group_id,
            Membership.user_id == inviter.id,
            Membership.role == MemberRole.ADMIN,
        )
    )
    if result.scalar_one_or_none() is None:
        raise ForbiddenError("Only admins can invite users")

    # Find invitee
    result = await db.execute(select(User).where(User.email == invitee_email))
    invitee = result.scalar_one_or_none()
    if invitee is None:
        raise NotFoundError("User", invitee_email)

    # Check existing membership
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == invitee.id, Membership.group_id == group_id
        )
    )
    if result.scalar_one_or_none() is not None:
        raise ForbiddenError("User is already a member")

    membership = Membership(user_id=invitee.id, group_id=group_id, role=role)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


async def get_user_groups(db: AsyncSession, user_id: uuid.UUID) -> list[Group]:
    result = await db.execute(
        select(Group)
        .join(Membership, Membership.group_id == Group.id)
        .where(Membership.user_id == user_id)
        .order_by(Group.created_at.desc())
    )
    return list(result.scalars().all())


async def get_user_membership(
    db: AsyncSession, user_id: uuid.UUID, group_id: uuid.UUID
) -> Membership:
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user_id, Membership.group_id == group_id
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise ForbiddenError("User is not a member of this group")
    return membership
