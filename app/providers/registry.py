"""Provider registry.

Supports two modes:
  - Singleton providers (for platform-managed keys configured in env)
  - Ephemeral providers (created per-request for BYOK org credentials)
"""
from app.providers.base import BaseProvider
from app.config import settings
from app.providers.mock import MockProvider
from app.providers.openai import OpenAIProvider

# Singleton providers (platform-managed / test)
_providers: dict[str, BaseProvider] = {}


def get_provider(name: str) -> BaseProvider:
    """Get singleton provider by name (uses platform/env credentials)."""
    if name not in _providers:
        if name == "openai":
            _providers[name] = OpenAIProvider()
        elif name == "anthropic":
            from app.providers.anthropic import AnthropicProvider
            if not settings.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY is not set. Configure managed key or add BYOK credential."
                )
            _providers[name] = AnthropicProvider(api_key=settings.anthropic_api_key)
        elif name == "mock":
            _providers[name] = MockProvider()
        else:
            raise ValueError(f"Unknown provider: {name}")
    return _providers[name]


def make_provider(name: str, api_key: str) -> BaseProvider:
    """Create an ephemeral provider with a specific API key (for BYOK)."""
    if name == "openai":
        from app.providers.openai import OpenAIProvider as _OAI
        from app.config import settings
        provider = _OAI.__new__(_OAI)
        import httpx
        provider._client = httpx.AsyncClient(
            base_url=settings.openai_base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )
        return provider
    elif name == "anthropic":
        from app.providers.anthropic import AnthropicProvider
        return AnthropicProvider(api_key=api_key)
    else:
        raise ValueError(f"Unknown provider for BYOK: {name}")


async def close_all() -> None:
    for provider in _providers.values():
        await provider.close()
    _providers.clear()
