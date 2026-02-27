import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class AgentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


class Agent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_agent_group_id", "agent_group_id"),
    )

    agent_group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agent_groups.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), nullable=False, default=AgentStatus.ACTIVE
    )


class ApiKey(UUIDMixin, TimestampMixin, Base):
    """Platform-issued API keys for agents. Format: cpk_<base64url(32 bytes)>."""
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_key_hash", "key_hash", unique=True),
        Index("ix_api_keys_agent_id", "agent_id"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agents.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # SHA-256 hash of the full key — never store plaintext
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Last 8 chars of key suffix for display (e.g., "...aB3xYz1k")
    key_suffix: Mapped[str] = mapped_column(String(8), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
