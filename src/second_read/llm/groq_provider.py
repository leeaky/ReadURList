from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from openai import APIStatusError, OpenAI, RateLimitError

from second_read.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_MAX_LLM_ATTEMPTS = 4
_LLM_BACKOFF_SEC = 1.5
# gpt-oss spends completion tokens on reasoning first; Groq's default 1024
# often leaves empty content and json_object then 400s json_validate_failed.
# On-demand TPM is 8000: prompt + max_completion_tokens must fit that window.
_GROQ_TPM_LIMIT = 8000
_TARGET_COMPLETION_TOKENS = 2048
_MIN_COMPLETION_TOKENS = 256
_TPM_MARGIN = 64

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _estimate_tokens(*parts: str) -> int:
    return max(1, sum(len(part) for part in parts) // 4)


def _completion_budget(prompt_tokens: int) -> int:
    room = _GROQ_TPM_LIMIT - prompt_tokens - _TPM_MARGIN
    return max(_MIN_COMPLETION_TOKENS, min(_TARGET_COMPLETION_TOKENS, room))


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
    """Groq chat via the OpenAI-compatible API."""

    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)

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
            schema_name = schema["name"] if "name" in schema else "result"
            system_text = (
                (system_text + "\n\n" if system_text else "")
                + "Respond with a single valid JSON object only — no markdown fences, no prose."
            )
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema_body,
                },
            }

        if system_text:
            messages.append({"role": "system", "content": system_text})
        messages.append({"role": "user", "content": user_prompt})
        kwargs["messages"] = messages
        prompt_tokens = _estimate_tokens(*(m["content"] for m in messages))
        kwargs["max_completion_tokens"] = _completion_budget(prompt_tokens)
        if "gpt-oss" in model.lower():
            kwargs["reasoning_effort"] = "low"

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
                retryable = isinstance(exc, RateLimitError) or status in {
                    408,
                    429,
                    500,
                    502,
                    503,
                    504,
                }
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
