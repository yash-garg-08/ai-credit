from decimal import Decimal

from sqlalchemy import Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class PricingRule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pricing"
    __table_args__ = (
        Index("ix_pricing_provider_model", "provider", "model", unique=True),
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    # Cost in USD per 1,000 input tokens
    input_cost_per_1k: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    # Cost in USD per 1,000 output tokens
    output_cost_per_1k: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
