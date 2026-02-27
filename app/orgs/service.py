"""Organization management service."""
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.groups.models import Group, Membership, MemberRole
from app.orgs.models import Organization


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:128] or "org"


async def create_organization(
    db: AsyncSession,
    owner_id: uuid.UUID,
    name: str,
    description: str | None = None,
) -> Organization:
    """Create an org, its billing group, and add the owner as ADMIN."""
    # Build a unique slug
    base_slug = _slugify(name)
    slug = base_slug
    counter = 1
    while True:
        exists = await db.execute(select(Organization).where(Organization.slug == slug))
        if exists.scalar_one_or_none() is None:
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Create a billing group for this org (reuses existing ledger infrastructure)
    billing_group = Group(
        name=f"[Billing] {name}",
        owner_id=owner_id,
    )
    db.add(billing_group)
    await db.flush()

    # Add owner as ADMIN of the billing group
    membership = Membership(
        user_id=owner_id,
        group_id=billing_group.id,
        role=MemberRole.ADMIN,
    )
    db.add(membership)

    # Create the org
    org = Organization(
        name=name,
        slug=slug,
        owner_id=owner_id,
        billing_group_id=billing_group.id,
        description=description,
    )
    db.add(org)
    await db.flush()
    return org


async def get_org(db: AsyncSession, org_id: uuid.UUID) -> Organization | None:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    return result.scalar_one_or_none()


async def list_orgs_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Organization]:
    result = await db.execute(
        select(Organization).where(Organization.owner_id == user_id).order_by(Organization.created_at)
    )
    return list(result.scalars().all())
