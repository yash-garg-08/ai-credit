"""
Test fixtures using async SQLite for fast, isolated tests.
No PostgreSQL required for unit tests.
"""
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.auth.models import User  # noqa: F401
from app.groups.models import Group, Membership, MemberRole  # noqa: F401
from app.ledger.models import LedgerEntry  # noqa: F401
from app.usage.models import UsageEvent  # noqa: F401
from app.pricing.models import PricingRule  # noqa: F401
# New multi-tenant models — must be imported so Base.metadata knows all tables
from app.orgs.models import Organization  # noqa: F401
from app.workspaces.models import Workspace  # noqa: F401
from app.agent_groups.models import AgentGroup  # noqa: F401
from app.agents.models import Agent, ApiKey  # noqa: F401
from app.credentials.models import ProviderCredential  # noqa: F401
from app.policies.models import Policy  # noqa: F401
from app.budgets.models import Budget  # noqa: F401
from app.audit.models import AuditLog  # noqa: F401


@pytest_asyncio.fixture
async def db():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def sample_group(db: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a user and a group, return (group_id, user_id)."""
    from app.core.security import hash_password

    user = User(email="test@example.com", hashed_password=hash_password("password"))
    db.add(user)
    await db.flush()

    group = Group(name="Test Group", owner_id=user.id)
    db.add(group)
    await db.flush()

    membership = Membership(user_id=user.id, group_id=group.id, role=MemberRole.ADMIN)
    db.add(membership)
    await db.commit()

    return group.id, user.id


@pytest_asyncio.fixture
async def pricing_rule(db: AsyncSession) -> PricingRule:
    """Create a mock pricing rule."""
    rule = PricingRule(
        provider="mock",
        model="mock-model",
        input_cost_per_1k=Decimal("0.001"),
        output_cost_per_1k=Decimal("0.002"),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule
