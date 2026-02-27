import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class CredentialMode(str, enum.Enum):
    MANAGED = "MANAGED"   # Platform provides its own keys
    BYOK = "BYOK"         # Bring Your Own Key — org supplies provider key


class ProviderCredential(UUIDMixin, TimestampMixin, Base):
    """Encrypted provider API keys. Fernet-encrypted at rest."""
    __tablename__ = "provider_credentials"
    __table_args__ = (
        Index("ix_cred_org_provider", "org_id", "provider"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[CredentialMode] = mapped_column(
        Enum(CredentialMode), nullable=False, default=CredentialMode.BYOK
    )
    # Fernet-encrypted API key (base64url encoded ciphertext)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
