import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent_groups.models import AgentGroup
from app.agents.models import Agent, AgentStatus, ApiKey
from app.auth.models import User
from app.budgets.models import Budget, BudgetPeriod
from app.budgets.service import check_budgets
from app.budgets.schemas import BudgetCreate
from app.credentials.models import CredentialMode, ProviderCredential
from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.groups.models import Group
from app.main import app
from app.orgs.models import Organization
from app.policies.models import Policy
from app.policies.schemas import PolicyCreate
from app.usage.models import UsageEvent, UsageStatus
from app.workspaces.models import Workspace


def _override_db(session: AsyncSession):
    async def _get_db():
        yield session

    return _get_db


def _override_user(user: User):
    async def _get_user():
        return user

    return _get_user


@pytest.mark.asyncio
async def test_policy_create_requires_exactly_one_target():
    with pytest.raises(ValidationError):
        PolicyCreate(name="no-target")

    with pytest.raises(ValidationError):
        PolicyCreate(
            name="double-target",
            org_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
        )

    created = PolicyCreate(name="ok", org_id=uuid.uuid4())
    assert created.org_id is not None


@pytest.mark.asyncio
async def test_budget_create_requires_exactly_one_target():
    with pytest.raises(ValidationError):
        BudgetCreate(period=BudgetPeriod.DAILY, limit_credits=100)

    with pytest.raises(ValidationError):
        BudgetCreate(
            period=BudgetPeriod.DAILY,
            limit_credits=100,
            org_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
        )

    created = BudgetCreate(
        period=BudgetPeriod.MONTHLY,
        limit_credits=1000,
        workspace_id=uuid.uuid4(),
    )
    assert created.workspace_id is not None


@pytest.mark.asyncio
async def test_org_balance_forbidden_for_non_owner(db: AsyncSession):
    owner = User(email="owner@test.com", hashed_password=hash_password("password"))
    outsider = User(email="outsider@test.com", hashed_password=hash_password("password"))
    db.add_all([owner, outsider])
    await db.flush()

    billing_group = Group(name="Billing", owner_id=owner.id)
    db.add(billing_group)
    await db.flush()

    org = Organization(
        name="Owner Org",
        slug="owner-org",
        owner_id=owner.id,
        billing_group_id=billing_group.id,
    )
    db.add(org)
    await db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = _override_user(outsider)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get(f"/orgs/{org.id}/balance")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_workspace_create_forbidden_for_non_owner(db: AsyncSession):
    owner = User(email="owner2@test.com", hashed_password=hash_password("password"))
    outsider = User(email="outsider2@test.com", hashed_password=hash_password("password"))
    db.add_all([owner, outsider])
    await db.flush()

    billing_group = Group(name="Billing 2", owner_id=owner.id)
    db.add(billing_group)
    await db.flush()

    org = Organization(
        name="Owner Org 2",
        slug="owner-org-2",
        owner_id=owner.id,
        billing_group_id=billing_group.id,
    )
    db.add(org)
    await db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = _override_user(outsider)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                f"/orgs/{org.id}/workspaces",
                json={"name": "Forbidden Workspace"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_routes_require_exactly_one_target_query(db: AsyncSession):
    owner = User(email="list-owner@test.com", hashed_password=hash_password("password"))
    db.add(owner)
    await db.flush()

    billing_group = Group(name="List Billing", owner_id=owner.id)
    db.add(billing_group)
    await db.flush()

    org = Organization(
        name="List Org",
        slug="list-org",
        owner_id=owner.id,
        billing_group_id=billing_group.id,
    )
    db.add(org)
    await db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = _override_user(owner)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            policy_none = await client.get("/policies")
            policy_multi = await client.get(
                f"/policies?org_id={org.id}&agent_id={uuid.uuid4()}"
            )
            budget_none = await client.get("/budgets")
            budget_multi = await client.get(
                f"/budgets?org_id={org.id}&agent_id={uuid.uuid4()}"
            )
    finally:
        app.dependency_overrides.clear()

    assert policy_none.status_code == 400
    assert policy_multi.status_code == 400
    assert budget_none.status_code == 400
    assert budget_multi.status_code == 400


@pytest.mark.asyncio
async def test_owner_can_list_policy_budget_credentials_and_keys(db: AsyncSession):
    owner = User(email="owner-list@test.com", hashed_password=hash_password("password"))
    db.add(owner)
    await db.flush()

    billing_group = Group(name="Owner List Billing", owner_id=owner.id)
    db.add(billing_group)
    await db.flush()

    org = Organization(
        name="Owner List Org",
        slug="owner-list-org",
        owner_id=owner.id,
        billing_group_id=billing_group.id,
    )
    db.add(org)
    await db.flush()

    workspace = Workspace(org_id=org.id, name="Owner WS", slug="owner-ws")
    db.add(workspace)
    await db.flush()

    agent_group = AgentGroup(workspace_id=workspace.id, name="Owner AG")
    db.add(agent_group)
    await db.flush()

    agent = Agent(agent_group_id=agent_group.id, name="Owner Agent")
    db.add(agent)
    await db.flush()

    db.add(
        Policy(
            name="Org Policy",
            org_id=org.id,
            allowed_models=["mock-model"],
            max_output_tokens=256,
        )
    )
    db.add(
        Budget(
            period=BudgetPeriod.DAILY,
            limit_credits=250,
            auto_disable=False,
            org_id=org.id,
        )
    )
    db.add(
        ProviderCredential(
            org_id=org.id,
            provider="openai",
            mode=CredentialMode.BYOK,
            encrypted_api_key="encrypted-test-value",
            label="primary",
        )
    )
    db.add(
        ApiKey(
            agent_id=agent.id,
            name="default",
            key_hash="a" * 64,
            key_suffix="1234abcd",
        )
    )
    await db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = _override_user(owner)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            policies_response = await client.get(f"/policies?org_id={org.id}")
            budgets_response = await client.get(f"/budgets?org_id={org.id}")
            credentials_response = await client.get(f"/orgs/{org.id}/credentials")
            keys_response = await client.get(f"/agents/{agent.id}/keys")
    finally:
        app.dependency_overrides.clear()

    assert policies_response.status_code == 200
    assert budgets_response.status_code == 200
    assert credentials_response.status_code == 200
    assert keys_response.status_code == 200

    assert len(policies_response.json()) == 1
    assert len(budgets_response.json()) == 1
    assert len(credentials_response.json()) == 1
    assert len(keys_response.json()) == 1


@pytest.mark.asyncio
async def test_list_routes_forbidden_for_non_owner(db: AsyncSession):
    owner = User(email="owner-scope@test.com", hashed_password=hash_password("password"))
    outsider = User(
        email="outsider-scope@test.com", hashed_password=hash_password("password")
    )
    db.add_all([owner, outsider])
    await db.flush()

    billing_group = Group(name="Scoped Billing", owner_id=owner.id)
    db.add(billing_group)
    await db.flush()

    org = Organization(
        name="Scoped Org",
        slug="scoped-org",
        owner_id=owner.id,
        billing_group_id=billing_group.id,
    )
    db.add(org)
    await db.flush()

    workspace = Workspace(org_id=org.id, name="Scoped WS", slug="scoped-ws")
    db.add(workspace)
    await db.flush()

    agent_group = AgentGroup(workspace_id=workspace.id, name="Scoped AG")
    db.add(agent_group)
    await db.flush()

    agent = Agent(agent_group_id=agent_group.id, name="Scoped Agent")
    db.add(agent)
    await db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = _override_user(outsider)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            policies_response = await client.get(f"/policies?org_id={org.id}")
            budgets_response = await client.get(f"/budgets?org_id={org.id}")
            credentials_response = await client.get(f"/orgs/{org.id}/credentials")
            keys_response = await client.get(f"/agents/{agent.id}/keys")
    finally:
        app.dependency_overrides.clear()

    assert policies_response.status_code == 403
    assert budgets_response.status_code == 403
    assert credentials_response.status_code == 403
    assert keys_response.status_code == 403


@pytest.mark.asyncio
async def test_budget_auto_disable_sets_agent_status(db: AsyncSession, monkeypatch):
    owner = User(email="budget-owner@test.com", hashed_password=hash_password("password"))
    db.add(owner)
    await db.flush()

    billing_group = Group(name="Budget Billing", owner_id=owner.id)
    db.add(billing_group)
    await db.flush()

    org = Organization(
        name="Budget Org",
        slug="budget-org",
        owner_id=owner.id,
        billing_group_id=billing_group.id,
    )
    db.add(org)
    await db.flush()

    workspace = Workspace(org_id=org.id, name="WS", slug="ws")
    db.add(workspace)
    await db.flush()

    agent_group = AgentGroup(workspace_id=workspace.id, name="AG")
    db.add(agent_group)
    await db.flush()

    agent = Agent(agent_group_id=agent_group.id, name="Agent 1")
    db.add(agent)
    await db.flush()

    budget = Budget(
        period=BudgetPeriod.DAILY,
        limit_credits=10,
        auto_disable=True,
        agent_id=agent.id,
    )
    db.add(budget)
    await db.flush()

    usage = UsageEvent(
        user_id=owner.id,
        group_id=billing_group.id,
        agent_id=agent.id,
        provider="mock",
        model="mock-model",
        input_tokens=10,
        output_tokens=10,
        total_tokens=20,
        cost_usd=Decimal("0.01"),
        credits_charged=9,
        status=UsageStatus.SUCCESS,
    )
    db.add(usage)
    await db.commit()

    session_factory = async_sessionmaker(
        db.bind, class_=AsyncSession, expire_on_commit=False
    )
    import app.budgets.service as budget_service

    monkeypatch.setattr(budget_service, "async_session_factory", session_factory)

    with pytest.raises(AppError) as exc:
        await check_budgets(
            db,
            org_id=org.id,
            workspace_id=workspace.id,
            agent_group_id=agent_group.id,
            agent_id=agent.id,
            required_credits=5,
        )

    assert exc.value.status_code == 402

    await db.refresh(agent)
    assert agent.status == AgentStatus.BUDGET_EXHAUSTED
