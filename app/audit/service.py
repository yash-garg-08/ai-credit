"""Audit log service — append-only, never update."""
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog


async def log_event(
    db: AsyncSession,
    org_id: uuid.UUID,
    event_type: str,
    *,
    actor_user_id: uuid.UUID | None = None,
    actor_agent_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    description: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        org_id=org_id,
        actor_user_id=actor_user_id,
        actor_agent_id=actor_agent_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        metadata_=metadata,
    )
    db.add(entry)
    await db.flush()
    return entry
