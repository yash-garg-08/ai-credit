import uuid

from fastapi import APIRouter
from temporalio.client import Client

from app.config import settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import AppError
from app.groups.service import get_user_membership
from app.providers.registry import get_provider
from app.usage import service as usage_service
from app.usage.schemas import (
    BurnRateResponse,
    TopUserResponse,
    UsageEventResponse,
    UsageRequest,
    UsageResponse,
)
from app.workflows.process_usage import ProcessUsageInput, ProcessUsageResult, ProcessUsageWorkflow

router = APIRouter(prefix="/usage", tags=["usage"])


@router.post("/request", response_model=UsageResponse)
async def request_usage(
    body: UsageRequest, db: DbSession, user: CurrentUser
) -> UsageResponse:
    # Verify membership
    await get_user_membership(db, user.id, body.group_id)

    # --- Abuse prevention hook ---
    # Extension point: rate limiting, anomaly detection
    # e.g., await check_rate_limit(user.id, body.group_id)

    # Call AI provider
    provider = get_provider(body.provider)
    provider_response = await provider.generate_completion(body.model, body.messages)

    # Start Temporal workflow for credit deduction
    temporal_client = await Client.connect(settings.temporal_host)

    workflow_input = ProcessUsageInput(
        request_id=body.request_id,
        user_id=str(user.id),
        group_id=str(body.group_id),
        provider=body.provider,
        model=body.model,
        input_tokens=provider_response.input_tokens,
        output_tokens=provider_response.output_tokens,
    )

    # Workflow ID = request_id ensures idempotency
    result: ProcessUsageResult = await temporal_client.execute_workflow(
        ProcessUsageWorkflow.run,
        workflow_input,
        id=f"usage-{body.request_id}",
        task_queue=settings.temporal_task_queue,
    )

    if not result.success:
        raise AppError(result.error, status_code=402)

    return UsageResponse(
        request_id=body.request_id,
        response=provider_response.content,
        input_tokens=provider_response.input_tokens,
        output_tokens=provider_response.output_tokens,
        credits_charged=result.credits_charged,
    )


@router.get("/history/{group_id}", response_model=list[UsageEventResponse])
async def usage_history(
    group_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    limit: int = 50,
    offset: int = 0,
) -> list[UsageEventResponse]:
    await get_user_membership(db, user.id, group_id)
    events = await usage_service.get_usage_history(db, group_id, limit, offset)
    return [UsageEventResponse.model_validate(e) for e in events]


@router.get("/burn-rate/{group_id}", response_model=BurnRateResponse)
async def burn_rate(
    group_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> BurnRateResponse:
    await get_user_membership(db, user.id, group_id)
    last_24h, last_7d = await usage_service.get_burn_rate(db, group_id)
    return BurnRateResponse(
        group_id=group_id, credits_last_24h=last_24h, credits_last_7d=last_7d
    )


@router.get("/top-users/{group_id}", response_model=list[TopUserResponse])
async def top_users(
    group_id: uuid.UUID, db: DbSession, user: CurrentUser, limit: int = 10
) -> list[TopUserResponse]:
    await get_user_membership(db, user.id, group_id)
    rows = await usage_service.get_top_users(db, group_id, limit)
    return [TopUserResponse(user_id=uid, total_credits=tc) for uid, tc in rows]
