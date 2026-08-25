from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, Sequence

from openai import APIStatusError, OpenAI, RateLimitError

from second_read.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_MAX_LLM_ATTEMPTS = 4
_LLM_BACKOFF_SEC = 1.5

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _extract_json(text: str) -> str:
    """Pull JSON object/array from a model reply that may include fences or prose."""
    text = text.strip()
    if text.startswith("{") or text.startswith("["):
        return text
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        return fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    raise json.JSONDecodeError("No JSON object found", text, 0)


class GroqProvider(LLMProvider):
    """Groq chat (OpenAI-compatible) + local sentence-transformers embeddings."""

    def __init__(self, api_key: str, *, embed_model: str = "all-MiniLM-L6-v2") -> None:
        self._client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        self._embed_model_name = embed_model
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading local embedding model %s …", self._embed_model_name)
            self._embedder = SentenceTransformer(self._embed_model_name)
        return self._embedder

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
        system_text = system or ""
        user_prompt = prompt

        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
        }

        if schema is not None:
            schema_body = schema["schema"] if "schema" in schema else schema
            system_text = (
                (system_text + "\n\n" if system_text else "")
                + "Respond with a single valid JSON object only — no markdown fences, no prose.\n"
                f"JSON schema:\n{json.dumps(schema_body)}"
            )
            # Groq supports json_object; full json_schema is unreliable across models
            kwargs["response_format"] = {"type": "json_object"}

        if system_text:
            messages.append({"role": "system", "content": system_text})
        messages.append({"role": "user", "content": user_prompt})
        kwargs["messages"] = messages

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_LLM_ATTEMPTS + 1):
            try:
                response = self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                if schema is not None:
                    content = _extract_json(content)
                    json.loads(content)
                return content
            except (RateLimitError, APIStatusError) as exc:
                status = getattr(exc, "status_code", None)
                retryable = isinstance(exc, RateLimitError) or status in {408, 429, 500, 502, 503, 504}
                last_exc = exc
                if not retryable or attempt == _MAX_LLM_ATTEMPTS:
                    raise
                import time

                wait = _LLM_BACKOFF_SEC * (2 ** (attempt - 1))
                logger.warning(
                    "Groq %s (attempt %s/%s); retry in %.1fs",
                    status or exc.__class__.__name__,
                    attempt,
                    _MAX_LLM_ATTEMPTS,
                    wait,
                )
                time.sleep(wait)
        raise last_exc or RuntimeError("Groq complete failed")

    def embed(self, texts: Sequence[str], *, model: str) -> list[list[float]]:
        if not texts:
            return []
        # `model` arg kept for interface compatibility; local model comes from settings
        name = model or self._embed_model_name
        if name != self._embed_model_name:
            self._embed_model_name = name
            self._embedder = None
        embedder = self._get_embedder()
        vectors = embedder.encode(list(texts), normalize_embeddings=True)
        return [v.tolist() for v in vectors]
