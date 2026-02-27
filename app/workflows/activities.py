"""
Temporal activities for the usage processing workflow.

Each activity is a discrete, retryable unit of work.
Activities interact with the database and external services.
"""
import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

from temporalio import activity

from app.db.session import async_session_factory
from app.ledger import service as ledger_service
from app.pricing import service as pricing_service
from app.usage import service as usage_service


@dataclass
class FetchPricingInput:
    provider: str
    model: str


@dataclass
class FetchPricingOutput:
    input_cost_per_1k: str  # Decimal as string for serialization
    output_cost_per_1k: str


@dataclass
class CalculateCostInput:
    input_cost_per_1k: str
    output_cost_per_1k: str
    input_tokens: int
    output_tokens: int
    credits_per_usd: int


@dataclass
class CalculateCostOutput:
    cost_usd: str
    credits: int


@dataclass
class CheckBalanceInput:
    group_id: str
    required_credits: int


@dataclass
class RecordUsageInput:
    user_id: str
    group_id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: str
    credits_charged: int
    idempotency_key: str


@activity.defn
async def fetch_pricing(input: FetchPricingInput) -> FetchPricingOutput:
    async with async_session_factory() as db:
        rule = await pricing_service.get_pricing_rule(db, input.provider, input.model)
        return FetchPricingOutput(
            input_cost_per_1k=str(rule.input_cost_per_1k),
            output_cost_per_1k=str(rule.output_cost_per_1k),
        )


@activity.defn
async def calculate_cost(input: CalculateCostInput) -> CalculateCostOutput:
    """Pure computation — no DB access needed."""
    from app.pricing.models import PricingRule as _  # noqa - just for type reference

    input_cost = (Decimal(input.input_tokens) / 1000) * Decimal(input.input_cost_per_1k)
    output_cost = (Decimal(input.output_tokens) / 1000) * Decimal(input.output_cost_per_1k)
    cost_usd = input_cost + output_cost

    scaled = cost_usd * Decimal(input.credits_per_usd)
    credits = int(scaled.to_integral_value(rounding=ROUND_CEILING))

    return CalculateCostOutput(cost_usd=str(cost_usd), credits=credits)


@activity.defn
async def check_balance_and_limits(input: CheckBalanceInput) -> bool:
    """Check if group has sufficient balance. Returns True if OK."""
    group_id = uuid.UUID(input.group_id)
    async with async_session_factory() as db:
        balance = await ledger_service.get_group_balance(db, group_id)
        # Extension point: check per-user limits, group spend caps, etc.
        return balance >= input.required_credits


@activity.defn
async def record_usage_and_deduct(input: RecordUsageInput) -> str:
    """
    Atomic operation: record usage event + deduct credits.
    Both happen in a single DB transaction.
    Returns the usage event ID.
    """
    user_id = uuid.UUID(input.user_id)
    group_id = uuid.UUID(input.group_id)

    async with async_session_factory() as db:
        async with db.begin():
            # Deduct credits (with advisory lock + idempotency check)
            await ledger_service.deduct_credits(
                db,
                group_id=group_id,
                amount=input.credits_charged,
                idempotency_key=input.idempotency_key,
                metadata={
                    "provider": input.provider,
                    "model": input.model,
                    "input_tokens": input.input_tokens,
                    "output_tokens": input.output_tokens,
                },
            )

            # Record usage event
            event = await usage_service.record_usage_event(
                db,
                user_id=user_id,
                group_id=group_id,
                provider=input.provider,
                model=input.model,
                input_tokens=input.input_tokens,
                output_tokens=input.output_tokens,
                cost_usd=Decimal(input.cost_usd),
                credits_charged=input.credits_charged,
            )

        return str(event.id)
