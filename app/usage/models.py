import enum
import uuid
from decimal import Decimal

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class UsageStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


class UsageEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        Index("ix_usage_group_user", "group_id", "user_id"),
        Index("ix_usage_group_created", "group_id", "created_at"),
        Index("ix_usage_agent_id", "agent_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("groups.id"), nullable=False
    )
    # New: agent context (nullable for backward compat)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agents.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    output_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    credits_charged: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # New observability fields
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[UsageStatus] = mapped_column(
        Enum(UsageStatus), nullable=False, default=UsageStatus.SUCCESS
    )
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
