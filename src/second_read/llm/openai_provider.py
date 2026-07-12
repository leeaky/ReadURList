from __future__ import annotations

import json
from typing import Any, Optional, Sequence

from openai import OpenAI

from second_read.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(api_key=api_key)

    def complete(
        self,
        prompt: str,
        *,
        model: str,
        system: Optional[str] = None,
        schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.3,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if schema is not None:
            schema_body = schema["schema"] if "schema" in schema else schema
            name = schema.get("name", "response") if "name" in schema else "response"
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": name,
                    "strict": True,
                    "schema": schema_body,
                },
            }

        response = self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        if schema is not None:
            json.loads(content)
        return content

    def embed(self, texts: Sequence[str], *, model: str) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=model, input=list(texts))
        return [item.embedding for item in response.data]
