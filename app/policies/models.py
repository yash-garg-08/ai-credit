import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    JSON,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Policy(UUIDMixin, TimestampMixin, Base):
    """
    Policy rules attached at any level of the hierarchy.
    A policy can be attached to: org, workspace, agent_group, or agent.
    Most restrictive wins when cascading.
    """
    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN org_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN workspace_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN agent_group_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN agent_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_policies_single_target",
        ),
    )

    # Exactly one of these FK columns is set (the level this policy applies to)
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

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Model allowlist — JSON array of model strings, null = all allowed
    allowed_models: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Per-request limits
    max_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Rate limiting (requests per minute)
    rpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
