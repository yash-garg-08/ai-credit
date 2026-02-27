"""Workspace management service."""
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.workspaces.models import Workspace


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:128] or "ws"


async def create_workspace(
    db: AsyncSession,
    org_id: uuid.UUID,
    name: str,
    description: str | None = None,
) -> Workspace:
    slug = _slugify(name)
    ws = Workspace(org_id=org_id, name=name, slug=slug, description=description)
    db.add(ws)
    await db.flush()
    return ws


async def list_workspaces(db: AsyncSession, org_id: uuid.UUID) -> list[Workspace]:
    result = await db.execute(
        select(Workspace).where(Workspace.org_id == org_id).order_by(Workspace.created_at)
    )
    return list(result.scalars().all())


async def get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Workspace | None:
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    return result.scalar_one_or_none()
