from fastapi import APIRouter
from sqlalchemy import select

from app.core.dependencies import DbSession
from app.pricing.models import PricingRule
from app.pricing.schemas import PricingRuleResponse

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("", response_model=list[PricingRuleResponse])
async def list_pricing(db: DbSession) -> list[PricingRuleResponse]:
    result = await db.execute(select(PricingRule).order_by(PricingRule.provider, PricingRule.model))
    rules = result.scalars().all()
    return [PricingRuleResponse.model_validate(r) for r in rules]
