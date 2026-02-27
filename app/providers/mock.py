from typing import Any

from app.providers.base import BaseProvider, ProviderResponse


class MockProvider(BaseProvider):
    """Deterministic mock provider for testing and development."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ProviderResponse:
        # Deterministic token count based on input length
        input_chars = sum(len(m.get("content", "")) for m in messages)
        input_tokens = max(input_chars // 4, 10)
        output_tokens = input_tokens * 2

        return ProviderResponse(
            content=f"Mock response for model={model}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            raw_metadata={"provider": "mock", "model": model},
        )
