"""Provider credential management — Fernet-encrypted BYOK keys."""
import uuid

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.credentials.models import CredentialMode, ProviderCredential


def _fernet() -> Fernet:
    return Fernet(settings.get_fernet_key())


def encrypt_key(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


async def add_credential(
    db: AsyncSession,
    org_id: uuid.UUID,
    provider: str,
    plaintext_api_key: str,
    label: str | None = None,
    mode: CredentialMode = CredentialMode.BYOK,
) -> ProviderCredential:
    encrypted = encrypt_key(plaintext_api_key)
    cred = ProviderCredential(
        org_id=org_id,
        provider=provider,
        mode=mode,
        encrypted_api_key=encrypted,
        label=label,
        is_active=True,
    )
    db.add(cred)
    await db.flush()
    return cred


async def get_active_credential(
    db: AsyncSession, org_id: uuid.UUID, provider: str
) -> str | None:
    """Return decrypted API key for the org+provider, or None if not configured."""
    result = await db.execute(
        select(ProviderCredential).where(
            ProviderCredential.org_id == org_id,
            ProviderCredential.provider == provider,
            ProviderCredential.is_active == True,  # noqa: E712
        )
    )
    cred = result.scalar_one_or_none()
    if cred is None:
        return None
    return decrypt_key(cred.encrypted_api_key)
