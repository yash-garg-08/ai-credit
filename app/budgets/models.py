import enum
import uuid

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class BudgetPeriod(str, enum.Enum):
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    TOTAL = "TOTAL"  # Lifetime cap


class Budget(UUIDMixin, TimestampMixin, Base):
    """
    Credit budget caps at any level of the hierarchy.
    If any level is exceeded, the request is blocked.
    """
    __tablename__ = "budgets"

    # Exactly one of these FK columns is set
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=True, index=True
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("workspaces.id"), nullable=True, index=True
    )
    agent_group_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agent_groups.id"), nullable=True, index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agents.id"), nullable=True, index=True
    )

    period: Mapped[BudgetPeriod] = mapped_column(Enum(BudgetPeriod), nullable=False)
    # Maximum credits allowed in the period
    limit_credits: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Auto-disable the entity when budget is exhausted
    auto_disable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
