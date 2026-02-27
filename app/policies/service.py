"""Policy engine — cascading model/token/RPM policies.

Cascade order: Agent → AgentGroup → Workspace → Org.
Most restrictive value wins for each field.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.policies.models import Policy


@dataclass
class EffectivePolicy:
    """The merged, most-restrictive policy for a request."""
    allowed_models: list[str] | None  # None = all allowed
    max_input_tokens: int | None
    max_output_tokens: int | None
    rpm_limit: int | None


def _merge_policies(policies: list[Policy]) -> EffectivePolicy:
    """
    Merge multiple policies into one effective policy.
    For lists (allowed_models): intersection (most restrictive = smallest set).
    For integers: minimum non-None value.
    """
    merged_allowed: list[str] | None = None
    merged_max_input: int | None = None
    merged_max_output: int | None = None
    merged_rpm: int | None = None

    for p in policies:
        if not p.is_active:
            continue

        # Allowed models — take intersection
        if p.allowed_models is not None:
            if merged_allowed is None:
                merged_allowed = list(p.allowed_models)
            else:
                merged_allowed = [m for m in merged_allowed if m in p.allowed_models]

        # Max tokens — take minimum
        if p.max_input_tokens is not None:
            if merged_max_input is None:
                merged_max_input = p.max_input_tokens
            else:
                merged_max_input = min(merged_max_input, p.max_input_tokens)

        if p.max_output_tokens is not None:
            if merged_max_output is None:
                merged_max_output = p.max_output_tokens
            else:
                merged_max_output = min(merged_max_output, p.max_output_tokens)

        # RPM — take minimum
        if p.rpm_limit is not None:
            if merged_rpm is None:
                merged_rpm = p.rpm_limit
            else:
                merged_rpm = min(merged_rpm, p.rpm_limit)

    return EffectivePolicy(
        allowed_models=merged_allowed,
        max_input_tokens=merged_max_input,
        max_output_tokens=merged_max_output,
        rpm_limit=merged_rpm,
    )


async def get_effective_policy(
    db: AsyncSession,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    agent_group_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> EffectivePolicy:
    """Fetch and merge all active policies across the hierarchy."""
    result = await db.execute(
        select(Policy).where(
            Policy.is_active == True,  # noqa: E712
            (
                (Policy.org_id == org_id)
                | (Policy.workspace_id == workspace_id)
                | (Policy.agent_group_id == agent_group_id)
                | (Policy.agent_id == agent_id)
            ),
        )
    )
    policies = list(result.scalars().all())
    return _merge_policies(policies)


async def list_policies_for_target(
    db: AsyncSession,
    *,
    org_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    agent_group_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
) -> list[Policy]:
    q = select(Policy)
    if org_id is not None:
        q = q.where(Policy.org_id == org_id)
    elif workspace_id is not None:
        q = q.where(Policy.workspace_id == workspace_id)
    elif agent_group_id is not None:
        q = q.where(Policy.agent_group_id == agent_group_id)
    elif agent_id is not None:
        q = q.where(Policy.agent_id == agent_id)
    else:
        return []

    q = q.order_by(Policy.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


def enforce_policy(
    policy: EffectivePolicy,
    model: str,
    requested_max_tokens: int | None,
) -> int | None:
    """
    Check model is allowed, enforce token limits.
    Returns effective max_tokens to pass to provider.
    Raises AppError(403) on policy violation.
    """
    if policy.allowed_models is not None and model not in policy.allowed_models:
        raise AppError(
            f"Model '{model}' is not in the allowed list for this agent: {policy.allowed_models}",
            status_code=403,
        )

    effective_max = requested_max_tokens
    if policy.max_output_tokens is not None:
        if effective_max is None:
            effective_max = policy.max_output_tokens
        else:
            effective_max = min(effective_max, policy.max_output_tokens)

    return effective_max
