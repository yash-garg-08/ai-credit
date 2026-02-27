import uuid

from sqlalchemy import ForeignKey, Index, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class AuditLog(UUIDMixin, TimestampMixin, Base):
    """Immutable audit trail for security-relevant events."""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_org_id", "org_id"),
        Index("ix_audit_created_at", "created_at"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    actor_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agents.id"), nullable=True
    )

    # Event type: api_key.created, api_key.revoked, credential.added,
    #             gateway.request, budget.exceeded, policy.violation
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
