from typing import Any

import httpx

from app.config import settings
from app.providers.base import BaseProvider, ProviderResponse


class OpenAIProvider(BaseProvider):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.openai_base_url,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            timeout=60.0,
        )

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ProviderResponse:
        payload: dict[str, Any] = {"model": model, "messages": messages, **kwargs}
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        usage = data.get("usage", {})
        return ProviderResponse(
            content=data["choices"][0]["message"]["content"],
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            raw_metadata=data,
        )

    async def close(self) -> None:
        await self._client.aclose()
