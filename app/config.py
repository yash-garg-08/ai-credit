from cryptography.fernet import Fernet
from pydantic import PrivateAttr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "extra": "ignore"}
    _runtime_fernet_key: bytes | None = PrivateAttr(default=None)

    database_url: str = "postgresql+asyncpg://credit_platform:credit_platform_dev@localhost:5432/credit_platform"
    redis_url: str = "redis://localhost:6379/0"
    temporal_host: str = "localhost:7233"
    temporal_task_queue: str = "credit-platform"

    secret_key: str = "change-me-to-a-random-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""

    # Fernet key for encrypting provider credentials at rest.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Must be a 32-byte URL-safe base64-encoded key.
    credential_encryption_key: str = ""

    # 1 USD = 100 credits (credits are integer cents)
    credits_per_usd: int = 100

    db_pool_size: int = 20
    db_max_overflow: int = 10

    def get_fernet_key(self) -> bytes:
        """Return a valid Fernet key, generating a default if not set (dev only)."""
        if self.credential_encryption_key:
            return self.credential_encryption_key.encode()
        # Auto-generate once per process in dev (not suitable for production).
        if self._runtime_fernet_key is None:
            self._runtime_fernet_key = Fernet.generate_key()
        return self._runtime_fernet_key


settings = Settings()
