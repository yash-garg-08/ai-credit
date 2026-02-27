import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Organization(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # billing_group_id links to the groups table — org credits live in the ledger
    billing_group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("groups.id"), nullable=False
    )

    # Billing settings
    credits_per_usd: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Optional description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
