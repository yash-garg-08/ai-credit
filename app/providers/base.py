from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderResponse:
    """Standardized response from any AI provider."""
    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    raw_metadata: dict[str, Any]


class BaseProvider(ABC):
    """Abstract interface for AI providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def generate_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Call the provider and return a standardized response.
        Business logic NEVER sees raw provider details.
        """
        ...

    async def close(self) -> None:
        """Cleanup resources (e.g., httpx client)."""
        pass
