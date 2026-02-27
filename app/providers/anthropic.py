"""Anthropic Claude provider via httpx."""
from typing import Any

import httpx

from app.providers.base import BaseProvider, ProviderResponse

ANTHROPIC_API_URL = "https://api.anthropic.com/v1"


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=ANTHROPIC_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=120.0,
        )

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def generate_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ProviderResponse:
        # Separate system message from user/assistant turns
        system_content: str | None = None
        filtered: list[dict[str, str]] = []
        for msg in messages:
            if msg.get("role") == "system":
                system_content = msg["content"]
            else:
                filtered.append(msg)

        max_tokens = kwargs.pop("max_tokens", 1024)
        payload: dict[str, Any] = {
            "model": model,
            "messages": filtered,
            "max_tokens": max_tokens,
            **kwargs,
        }
        if system_content:
            payload["system"] = system_content

        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        usage = data.get("usage", {})
        content_blocks = data.get("content", [])
        text = " ".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")

        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        return ProviderResponse(
            content=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            raw_metadata=data,
        )

    async def close(self) -> None:
        await self._client.aclose()
