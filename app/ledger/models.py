import enum
import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class TransactionType(str, enum.Enum):
    CREDIT_PURCHASE = "CREDIT_PURCHASE"
    USAGE_DEDUCTION = "USAGE_DEDUCTION"
    ADJUSTMENT = "ADJUSTMENT"
    REFUND = "REFUND"


class LedgerEntry(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ledger"
    __table_args__ = (
        Index("ix_ledger_group_created", "group_id", "created_at"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("groups.id"), nullable=False, index=True
    )
    # Signed integer: positive = credit in, negative = deduction
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
