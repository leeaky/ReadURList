from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

from openai import APIStatusError, OpenAI, RateLimitError

from second_read.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_MAX_LLM_ATTEMPTS = 4
_LLM_BACKOFF_SEC = 1.5
# gpt-oss spends completion tokens on reasoning first; Groq's default 1024
# often leaves empty content and json_schema then 400s json_validate_failed.
# On-demand TPM is 8000: prompt + max_completion_tokens must fit that window.
# Do not cap completion at 2048 — consolidation reasoning can exhaust that
# and Groq returns failed_generation: ''.
_GROQ_TPM_LIMIT = 8000
_MIN_COMPLETION_TOKENS = 256
_TPM_MARGIN = 256
_CHARS_PER_TOKEN = 3  # denser than chars/4; json_schema + academic PDF undercount

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _estimate_tokens(*parts: str) -> int:
    return max(1, sum(len(part or "") for part in parts) // _CHARS_PER_TOKEN)


def _schema_json(kwargs: dict[str, Any]) -> str:
    fmt = kwargs.get("response_format")
    return json.dumps(fmt) if fmt else ""


def _completion_budget(prompt_tokens: int) -> int:
    room = _GROQ_TPM_LIMIT - prompt_tokens - _TPM_MARGIN
    # Never floor at MIN if that would exceed TPM; truncation reserved MIN already.
    return max(1, room)


def _fit_messages_to_tpm(messages: list[dict[str, str]], schema_json: str) -> None:
    """Truncate the user message so prompt + min completion + margin fit TPM."""
    user_idx = next(
        (i for i, m in enumerate(messages) if m["role"] == "user"),
        None,
    )
    if user_idx is None:
        return
    others = [m["content"] for i, m in enumerate(messages) if i != user_idx]
    reserved = (
        _estimate_tokens(*others, schema_json)
        + _MIN_COMPLETION_TOKENS
        + _TPM_MARGIN
    )
    budget_chars = max(0, (_GROQ_TPM_LIMIT - reserved) * _CHARS_PER_TOKEN)
    text = messages[user_idx]["content"]
    if len(text) <= budget_chars:
        return
    clipped = text[:budget_chars]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    messages[user_idx]["content"] = clipped


def _shrink_user_message(messages: list[dict[str, str]], fraction: float = 0.75) -> None:
    for message in reversed(messages):
        if message["role"] != "user":
            continue
        text = message["content"]
        keep = max(1, int(len(text) * fraction))
        clipped = text[:keep]
        if " " in clipped:
            clipped = clipped.rsplit(" ", 1)[0]
        message["content"] = clipped or text[:keep]
        return


def _apply_tpm_budget(kwargs: dict[str, Any]) -> None:
    messages = kwargs["messages"]
    schema_json = _schema_json(kwargs)
    _fit_messages_to_tpm(messages, schema_json)
    prompt_tokens = _estimate_tokens(
        *(m["content"] for m in messages),
        schema_json,
    )
    kwargs["max_completion_tokens"] = _completion_budget(prompt_tokens)


def _tpm_request_too_large(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status == 413:
        return True
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return False
    err = body.get("error") if isinstance(body.get("error"), dict) else body
    if not isinstance(err, dict):
        return False
    message = str(err.get("message") or "")
    return err.get("type") == "tokens" or "Request too large" in message


def _empty_json_validate(exc: BaseException) -> bool:
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return False
    err = body.get("error") if isinstance(body.get("error"), dict) else body
    if not isinstance(err, dict):
        return False
    return err.get("code") == "json_validate_failed" and not (
        err.get("failed_generation") or ""
    )


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
        _apply_tpm_budget(kwargs)
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
                last_exc = exc
                too_large = _tpm_request_too_large(exc)
                retryable = (
                    too_large
                    or isinstance(exc, RateLimitError)
                    or status in {408, 429, 500, 502, 503, 504}
                    or _empty_json_validate(exc)
                )
                if not retryable or attempt == _MAX_LLM_ATTEMPTS:
                    raise
                if too_large:
                    _shrink_user_message(kwargs["messages"])
                    _apply_tpm_budget(kwargs)
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
