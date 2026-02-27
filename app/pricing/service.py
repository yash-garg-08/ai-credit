"""
Cost engine: tokens → cost_usd → credits

All pricing comes from the database. No hardcoded prices.
"""
from decimal import Decimal, ROUND_CEILING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundError
from app.pricing.models import PricingRule
from app.pricing.schemas import CostCalculation


async def get_pricing_rule(
    db: AsyncSession, provider: str, model: str
) -> PricingRule:
    result = await db.execute(
        select(PricingRule).where(
            PricingRule.provider == provider, PricingRule.model == model
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise NotFoundError("PricingRule", f"{provider}/{model}")
    return rule


def calculate_cost(
    rule: PricingRule, input_tokens: int, output_tokens: int
) -> Decimal:
    """Calculate USD cost from token counts and pricing rule."""
    input_cost = (Decimal(input_tokens) / 1000) * rule.input_cost_per_1k
    output_cost = (Decimal(output_tokens) / 1000) * rule.output_cost_per_1k
    return input_cost + output_cost


def cost_to_credits(cost_usd: Decimal, credits_per_usd: int | None = None) -> int:
    """
    Convert USD cost to credits (integer).
    Always rounds UP to avoid under-charging.
    """
    rate = credits_per_usd if credits_per_usd is not None else settings.credits_per_usd
    scaled = cost_usd * Decimal(rate)
    return int(scaled.to_integral_value(rounding=ROUND_CEILING))


async def compute_usage_cost(
    db: AsyncSession, provider: str, model: str, input_tokens: int, output_tokens: int
) -> CostCalculation:
    """Full pipeline: tokens → pricing lookup → USD cost → credits."""
    rule = await get_pricing_rule(db, provider, model)
    cost_usd = calculate_cost(rule, input_tokens, output_tokens)
    credits = cost_to_credits(cost_usd)
    return CostCalculation(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        credits=credits,
    )
