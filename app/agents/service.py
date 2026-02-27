"""API Key management service.

Platform API keys format: cpk_<base64url(32 random bytes)>
Storage: SHA-256 hash of the full key (never store plaintext).
"""
import hashlib
import os
import secrets
import uuid
from base64 import urlsafe_b64encode

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import Agent, AgentStatus, ApiKey
from app.core.exceptions import AppError


def _generate_platform_key() -> str:
    """Generate a new cpk_ prefixed platform API key."""
    raw = secrets.token_bytes(32)
    return "cpk_" + urlsafe_b64encode(raw).rstrip(b"=").decode()


def _hash_key(key: str) -> str:
    """Return SHA-256 hex digest of the key."""
    return hashlib.sha256(key.encode()).hexdigest()


async def create_api_key(
    db: AsyncSession,
    agent_id: uuid.UUID,
    name: str,
) -> tuple[ApiKey, str]:
    """
    Create a new API key for an agent.
    Returns (ApiKey ORM object, plaintext_key).
    Caller must return the plaintext key to the user — it is never stored.
    """
    plaintext = _generate_platform_key()
    key_hash = _hash_key(plaintext)
    key_suffix = plaintext[-8:]

    api_key = ApiKey(
        agent_id=agent_id,
        name=name,
        key_hash=key_hash,
        key_suffix=key_suffix,
        is_active=True,
    )
    db.add(api_key)
    await db.flush()
    return api_key, plaintext


async def resolve_api_key(db: AsyncSession, plaintext_key: str) -> ApiKey | None:
    """Look up an API key by its plaintext value. Returns None if not found/revoked."""
    key_hash = _hash_key(plaintext_key)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def revoke_api_key(
    db: AsyncSession,
    api_key_id: uuid.UUID,
    reason: str | None = None,
    agent_id: uuid.UUID | None = None,
) -> ApiKey:
    result = await db.execute(select(ApiKey).where(ApiKey.id == api_key_id))
    key = result.scalar_one_or_none()
    if key is None:
        raise AppError("API key not found", status_code=404)
    if agent_id is not None and key.agent_id != agent_id:
        raise AppError("API key not found", status_code=404)
    key.is_active = False
    key.revoked_reason = reason
    await db.flush()
    return key


async def get_agent(db: AsyncSession, agent_id: uuid.UUID) -> Agent | None:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def list_agents_for_group(db: AsyncSession, agent_group_id: uuid.UUID) -> list[Agent]:
    result = await db.execute(
        select(Agent).where(Agent.agent_group_id == agent_group_id).order_by(Agent.created_at)
    )
    return list(result.scalars().all())


async def create_agent(
    db: AsyncSession,
    agent_group_id: uuid.UUID,
    name: str,
    description: str | None = None,
) -> Agent:
    agent = Agent(agent_group_id=agent_group_id, name=name, description=description)
    db.add(agent)
    await db.flush()
    return agent


async def disable_agent(db: AsyncSession, agent_id: uuid.UUID, reason: str = "budget_exhausted") -> None:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent:
        agent.status = AgentStatus.BUDGET_EXHAUSTED if reason == "budget_exhausted" else AgentStatus.DISABLED
        await db.flush()
