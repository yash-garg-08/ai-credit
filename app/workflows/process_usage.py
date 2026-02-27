"""
ProcessUsageWorkflow — the core credit deduction workflow.

Workflow ID = request_id (client-provided UUID).
Temporal guarantees at-most-once execution per workflow ID,
which prevents double deductions.
"""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.config import settings
    from app.workflows.activities import (
        CalculateCostInput,
        CalculateCostOutput,
        CheckBalanceInput,
        FetchPricingInput,
        FetchPricingOutput,
        RecordUsageInput,
        calculate_cost,
        check_balance_and_limits,
        fetch_pricing,
        record_usage_and_deduct,
    )


@dataclass
class ProcessUsageInput:
    request_id: str
    user_id: str
    group_id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int


@dataclass
class ProcessUsageResult:
    success: bool
    credits_charged: int = 0
    usage_event_id: str = ""
    error: str = ""


@workflow.defn
class ProcessUsageWorkflow:
    @workflow.run
    async def run(self, input: ProcessUsageInput) -> ProcessUsageResult:
        # Step 1: Fetch pricing from DB
        pricing: FetchPricingOutput = await workflow.execute_activity(
            fetch_pricing,
            FetchPricingInput(provider=input.provider, model=input.model),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3),
        )

        # Step 2: Calculate cost (tokens → USD → credits)
        cost: CalculateCostOutput = await workflow.execute_activity(
            calculate_cost,
            CalculateCostInput(
                input_cost_per_1k=pricing.input_cost_per_1k,
                output_cost_per_1k=pricing.output_cost_per_1k,
                input_tokens=input.input_tokens,
                output_tokens=input.output_tokens,
                credits_per_usd=settings.credits_per_usd,
            ),
            start_to_close_timeout=timedelta(seconds=5),
        )

        # Step 3: Check balance and limits
        has_balance: bool = await workflow.execute_activity(
            check_balance_and_limits,
            CheckBalanceInput(
                group_id=input.group_id,
                required_credits=cost.credits,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3),
        )

        if not has_balance:
            return ProcessUsageResult(
                success=False,
                error=f"Insufficient credits for {cost.credits} credits",
            )

        # Step 4: Record usage + deduct credits (atomic)
        usage_event_id: str = await workflow.execute_activity(
            record_usage_and_deduct,
            RecordUsageInput(
                user_id=input.user_id,
                group_id=input.group_id,
                provider=input.provider,
                model=input.model,
                input_tokens=input.input_tokens,
                output_tokens=input.output_tokens,
                cost_usd=cost.cost_usd,
                credits_charged=cost.credits,
                idempotency_key=f"usage:{input.request_id}",
            ),
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3),
        )

        return ProcessUsageResult(
            success=True,
            credits_charged=cost.credits,
            usage_event_id=usage_event_id,
        )
