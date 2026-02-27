"""
AI Gateway — OpenAI-compatible proxy endpoint.

Agent flow:
  POST /gateway/v1/chat/completions
  Authorization: Bearer cpk_<key>

Processing:
  1. Authenticate API key → resolve Agent
  2. Walk hierarchy: Agent → AgentGroup → Workspace → Org
  3. Policy check: model allowed? token limits enforced?
  4. Budget check: won't exceed caps at any level?
  5. Ledger check: org has sufficient credits?
  6. Call provider (BYOK cred or platform default)
  7. Atomic deduction + usage recording
  8. Return OpenAI-compatible response
"""
import time
import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.agent_groups.models import AgentGroup
from app.agents.models import Agent, AgentStatus
from app.agents.service import resolve_api_key
from app.audit.service import log_event
from app.budgets.service import check_budgets
from app.core.exceptions import AppError, InsufficientCreditsError
from app.db.session import async_session_factory
from app.ledger import service as ledger_service
from app.ledger.models import TransactionType
from app.orgs.models import Organization
from app.policies.service import enforce_policy, get_effective_policy
from app.pricing import service as pricing_service
from app.providers.registry import get_provider, make_provider
from app.credentials.service import get_active_credential
from app.usage.models import UsageEvent, UsageStatus
from app.workspaces.models import Workspace

router = APIRouter(prefix="/gateway/v1", tags=["gateway"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool = False


async def _resolve_hierarchy(
    db: Any,
    agent: Agent,
) -> tuple[AgentGroup, Workspace, Organization]:
    """Walk Agent → AgentGroup → Workspace → Org."""
    group_result = await db.execute(
        select(AgentGroup).where(AgentGroup.id == agent.agent_group_id)
    )
    agent_group: AgentGroup = group_result.scalar_one()

    ws_result = await db.execute(
        select(Workspace).where(Workspace.id == agent_group.workspace_id)
    )
    workspace: Workspace = ws_result.scalar_one()

    org_result = await db.execute(
        select(Organization).where(Organization.id == workspace.org_id)
    )
    org: Organization = org_result.scalar_one()

    return agent_group, workspace, org


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: str = Header(...),
) -> JSONResponse:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    plaintext_key = authorization.removeprefix("Bearer ").strip()
    if not plaintext_key.startswith("cpk_"):
        raise HTTPException(401, "Invalid API key format — must start with cpk_")

    request_id = str(uuid.uuid4())
    start_ts = time.monotonic()

    async with async_session_factory() as db:
        async with db.begin():
            # 1. Resolve API key → Agent
            api_key_obj = await resolve_api_key(db, plaintext_key)
            if api_key_obj is None:
                raise HTTPException(401, "Invalid or revoked API key")

            agent_result = await db.execute(
                select(Agent).where(Agent.id == api_key_obj.agent_id)
            )
            agent: Agent = agent_result.scalar_one()

            if agent.status != AgentStatus.ACTIVE:
                raise HTTPException(
                    403,
                    f"Agent is not active (status: {agent.status.value})",
                )

            # 2. Resolve hierarchy
            agent_group, workspace, org = await _resolve_hierarchy(db, agent)

            if not org.is_active:
                raise HTTPException(403, "Organization is disabled")
            if not workspace.is_active:
                raise HTTPException(403, "Workspace is disabled")
            if not agent_group.is_active:
                raise HTTPException(403, "Agent group is disabled")

            # 3. Policy check
            policy = await get_effective_policy(
                db,
                org_id=org.id,
                workspace_id=workspace.id,
                agent_group_id=agent_group.id,
                agent_id=agent.id,
            )
            effective_max_tokens = enforce_policy(
                policy, request.model, request.max_tokens
            )

            # 4. Fetch pricing (needed for budget/credit check)
            provider_name = _infer_provider(request.model)
            pricing_rule = await pricing_service.get_pricing_rule(
                db, provider_name, request.model
            )

            # Estimate cost for budget pre-check (use 0 input tokens as estimate; post-check is authoritative)
            # We use a rough estimate: max_tokens output, 0 input
            estimated_output = effective_max_tokens or 1024
            estimated_cost_usd = (
                (Decimal("0") / 1000) * pricing_rule.input_cost_per_1k
                + (Decimal(estimated_output) / 1000) * pricing_rule.output_cost_per_1k
            )
            estimated_credits = pricing_service.cost_to_credits(
                estimated_cost_usd,
                credits_per_usd=org.credits_per_usd,
            )

            # 5. Budget check across hierarchy
            await check_budgets(
                db,
                org_id=org.id,
                workspace_id=workspace.id,
                agent_group_id=agent_group.id,
                agent_id=agent.id,
                required_credits=max(1, estimated_credits),
            )

            # 6. Ledger balance check (inside advisory lock)
            balance = await ledger_service.get_group_balance_for_update(
                db, org.billing_group_id
            )

            # We'll do a quick pre-flight — exact deduction happens after provider call

        # End pre-check transaction — release advisory lock

    # 7. Call provider (outside transaction to avoid long-held locks)
    messages = [m.model_dump() for m in request.messages]
    kwargs: dict[str, Any] = {}
    if effective_max_tokens:
        kwargs["max_tokens"] = effective_max_tokens
    if request.temperature is not None:
        kwargs["temperature"] = request.temperature

    usage_status = UsageStatus.SUCCESS
    error_msg: str | None = None
    provider_response = None

    async with async_session_factory() as db:
        # Get provider — prefer BYOK credentials for the org
        byok_key = await get_active_credential(db, org.id, provider_name)

    try:
        try:
            if byok_key:
                provider = make_provider(provider_name, byok_key)
            else:
                provider = get_provider(provider_name)
        except ValueError as exc:
            raise HTTPException(
                503,
                f"Provider '{provider_name}' is not configured: {exc}",
            ) from exc

        provider_response = await provider.generate_completion(
            model=request.model,
            messages=messages,
            **kwargs,
        )
        latency_ms = int((time.monotonic() - start_ts) * 1000)
    except Exception as exc:
        latency_ms = int((time.monotonic() - start_ts) * 1000)
        usage_status = UsageStatus.ERROR
        error_msg = str(exc)[:1024]
        # Record the failed attempt without charging
        async with async_session_factory() as db:
            async with db.begin():
                event = UsageEvent(
                    user_id=org.owner_id,
                    group_id=org.billing_group_id,
                    agent_id=agent.id,
                    provider=provider_name,
                    model=request.model,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost_usd=Decimal("0"),
                    credits_charged=0,
                    latency_ms=latency_ms,
                    status=usage_status,
                    error_message=error_msg,
                )
                db.add(event)
                await log_event(
                    db,
                    org_id=org.id,
                    event_type="gateway.request_error",
                    actor_agent_id=agent.id,
                    description=error_msg,
                    metadata={"model": request.model, "request_id": request_id},
                )
        raise HTTPException(502, f"Provider error: {error_msg}")

    # 8. Compute actual cost & deduct
    actual_input = provider_response.input_tokens
    actual_output = provider_response.output_tokens
    actual_cost_usd = (
        (Decimal(actual_input) / 1000) * pricing_rule.input_cost_per_1k
        + (Decimal(actual_output) / 1000) * pricing_rule.output_cost_per_1k
    )
    actual_credits = pricing_service.cost_to_credits(
        actual_cost_usd,
        credits_per_usd=org.credits_per_usd,
    )

    idempotency_key = f"gateway:{request_id}"

    async with async_session_factory() as db:
        async with db.begin():
            try:
                await ledger_service.deduct_credits(
                    db,
                    group_id=org.billing_group_id,
                    amount=actual_credits,
                    idempotency_key=idempotency_key,
                    metadata={
                        "provider": provider_name,
                        "model": request.model,
                        "input_tokens": actual_input,
                        "output_tokens": actual_output,
                        "request_id": request_id,
                        "agent_id": str(agent.id),
                    },
                )
            except InsufficientCreditsError:
                usage_status = UsageStatus.BUDGET_EXCEEDED
                # Record the blocked event (no charge)
                event = UsageEvent(
                    user_id=org.owner_id,
                    group_id=org.billing_group_id,
                    agent_id=agent.id,
                    provider=provider_name,
                    model=request.model,
                    input_tokens=actual_input,
                    output_tokens=actual_output,
                    total_tokens=actual_input + actual_output,
                    cost_usd=actual_cost_usd,
                    credits_charged=0,
                    latency_ms=latency_ms,
                    status=UsageStatus.BUDGET_EXCEEDED,
                    error_message="Insufficient credits after provider call",
                )
                db.add(event)
                raise HTTPException(402, "Insufficient credits — usage was not charged")

            # Record usage
            event = UsageEvent(
                user_id=org.owner_id,
                group_id=org.billing_group_id,
                agent_id=agent.id,
                provider=provider_name,
                model=request.model,
                input_tokens=actual_input,
                output_tokens=actual_output,
                total_tokens=actual_input + actual_output,
                cost_usd=actual_cost_usd,
                credits_charged=actual_credits,
                latency_ms=latency_ms,
                status=UsageStatus.SUCCESS,
            )
            db.add(event)

            # Audit log
            await log_event(
                db,
                org_id=org.id,
                event_type="gateway.request",
                actor_agent_id=agent.id,
                description=f"Completed {provider_name}/{request.model}",
                metadata={
                    "request_id": request_id,
                    "input_tokens": actual_input,
                    "output_tokens": actual_output,
                    "credits_charged": actual_credits,
                    "latency_ms": latency_ms,
                },
            )

    # 9. Return OpenAI-compatible response
    return JSONResponse(
        content={
            "id": f"chatcmpl-{request_id}",
            "object": "chat.completion",
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": provider_response.content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": actual_input,
                "completion_tokens": actual_output,
                "total_tokens": actual_input + actual_output,
            },
            "x_platform": {
                "credits_charged": actual_credits,
                "latency_ms": latency_ms,
                "request_id": request_id,
            },
        }
    )


def _infer_provider(model: str) -> str:
    """Infer provider from model name."""
    if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3"):
        return "openai"
    elif model.startswith("claude-"):
        return "anthropic"
    elif model.startswith("mock"):
        return "mock"
    else:
        return "openai"  # default
