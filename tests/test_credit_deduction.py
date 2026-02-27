"""Tests for the cost engine: tokens → USD → credits."""
from decimal import Decimal

import pytest

from app.pricing.models import PricingRule
from app.pricing.service import calculate_cost, compute_usage_cost, cost_to_credits


class _FakeRule:
    """Lightweight stand-in for PricingRule to avoid SQLAlchemy instrumentation."""
    def __init__(self, input_cost: str, output_cost: str):
        self.input_cost_per_1k = Decimal(input_cost)
        self.output_cost_per_1k = Decimal(output_cost)


def _make_rule(input_cost: str = "0.001", output_cost: str = "0.002"):
    return _FakeRule(input_cost, output_cost)


class TestCalculateCost:
    def test_basic_cost(self):
        rule = _make_rule("0.001", "0.002")
        # 1000 input tokens @ $0.001/1k = $0.001
        # 500 output tokens @ $0.002/1k = $0.001
        cost = calculate_cost(rule, input_tokens=1000, output_tokens=500)
        assert cost == Decimal("0.002")

    def test_zero_tokens(self):
        rule = _make_rule()
        cost = calculate_cost(rule, input_tokens=0, output_tokens=0)
        assert cost == Decimal("0")

    def test_large_token_count(self):
        rule = _make_rule("0.01", "0.03")
        # 100k input @ $0.01/1k = $1.00
        # 50k output @ $0.03/1k = $1.50
        cost = calculate_cost(rule, input_tokens=100_000, output_tokens=50_000)
        assert cost == Decimal("2.50")


class TestCostToCredits:
    def test_exact_conversion(self):
        # $1.00 at 100 credits/USD = 100 credits
        assert cost_to_credits(Decimal("1.00")) == 100

    def test_rounds_up(self):
        # $0.001 at 100 credits/USD = 0.1 → rounds up to 1
        assert cost_to_credits(Decimal("0.001")) == 1

    def test_zero_cost(self):
        assert cost_to_credits(Decimal("0")) == 0

    def test_fractional_rounds_up(self):
        # $0.015 at 100 credits/USD = 1.5 → rounds up to 2
        assert cost_to_credits(Decimal("0.015")) == 2


@pytest.mark.asyncio
async def test_compute_usage_cost_pipeline(db, pricing_rule):
    """Integration test: tokens → pricing lookup → cost → credits."""
    result = await compute_usage_cost(
        db, provider="mock", model="mock-model", input_tokens=10_000, output_tokens=5_000
    )
    # 10k input @ $0.001/1k = $0.01
    # 5k output @ $0.002/1k = $0.01
    # Total = $0.02, at 100 credits/USD = 2 credits
    assert result.cost_usd == Decimal("0.020000000")
    assert result.credits == 2
    assert result.provider == "mock"
    assert result.model == "mock-model"
