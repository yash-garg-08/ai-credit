"""Seed pricing data. Run with: python -m scripts.seed"""
import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db.session import async_session_factory
from app.pricing.models import PricingRule

PRICING_DATA = [
    # OpenAI models
    ("openai", "gpt-4o", Decimal("0.0025"), Decimal("0.01")),
    ("openai", "gpt-4o-mini", Decimal("0.00015"), Decimal("0.0006")),
    ("openai", "gpt-4-turbo", Decimal("0.01"), Decimal("0.03")),
    ("openai", "gpt-3.5-turbo", Decimal("0.0005"), Decimal("0.0015")),
    # Mock provider (for development/testing)
    ("mock", "mock-model", Decimal("0.001"), Decimal("0.002")),
]


async def main() -> None:
    async with async_session_factory() as db:
        for provider, model, input_cost, output_cost in PRICING_DATA:
            result = await db.execute(
                select(PricingRule).where(
                    PricingRule.provider == provider, PricingRule.model == model
                )
            )
            if result.scalar_one_or_none() is None:
                db.add(
                    PricingRule(
                        provider=provider,
                        model=model,
                        input_cost_per_1k=input_cost,
                        output_cost_per_1k=output_cost,
                    )
                )
                print(f"  Added: {provider}/{model}")
            else:
                print(f"  Exists: {provider}/{model}")

        await db.commit()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
