import json
from types import SimpleNamespace

import httpx
from openai import APIStatusError, BadRequestError

from readurlist.llm.groq_provider import GroqProvider
from readurlist.prompts import CONSOLIDATE_SCHEMA, INGEST_SCHEMA, INGEST_SYSTEM


def _billed_tpm(kwargs: dict) -> int:
    """Groq reserves prompt + max_completion_tokens against the 8000 TPM cap.

    Academic PDF text and json_schema tokenize denser than chars/4; this helper
    approximates that so tests fail if we only budget message chars/4.
    """
    contents = sum(len(m["content"]) for m in kwargs["messages"])
    schema = len(json.dumps(kwargs.get("response_format") or {}))
    prompt = max(1, (contents + schema) // 3)
    return prompt + int(kwargs["max_completion_tokens"])


def _empty_json_validate_error() -> BadRequestError:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(
        400,
        request=request,
        json={
            "error": {
                "message": "Failed to validate JSON. Please adjust your prompt.",
                "type": "invalid_request_error",
                "code": "json_validate_failed",
                "failed_generation": "",
            }
        },
    )
    return BadRequestError(
        "Failed to validate JSON",
        response=response,
        body=response.json(),
    )


class _FakeCompletions:
    def __init__(self):
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
        )


def _provider() -> tuple[GroqProvider, _FakeCompletions]:
    provider = GroqProvider(api_key="x")
    completions = _FakeCompletions()
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return provider, completions


def test_complete_uses_json_schema_strict_and_room_for_reasoning():
    provider, completions = _provider()
    provider.complete(
        "merge tags",
        model="openai/gpt-oss-120b",
        system="Return JSON only.",
        schema=CONSOLIDATE_SCHEMA,
        temperature=0.2,
    )
    kwargs = completions.calls[0]
    assert kwargs["max_completion_tokens"] > 1024
    prompt_tokens = sum(len(m["content"]) for m in kwargs["messages"]) // 4
    assert prompt_tokens + kwargs["max_completion_tokens"] <= 8000
    fmt = kwargs["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["name"] == "tag_consolidation"
    assert fmt["json_schema"]["schema"]["required"] == ["subject_maps", "topic_maps"]


def test_complete_caps_completion_tokens_so_request_fits_tpm_limit():
    provider, completions = _provider()
    provider.complete(
        "label " * 4000,
        model="openai/gpt-oss-120b",
        schema=CONSOLIDATE_SCHEMA,
    )
    kwargs = completions.calls[0]
    prompt_tokens = sum(len(m["content"]) for m in kwargs["messages"]) // 4
    assert prompt_tokens + kwargs["max_completion_tokens"] <= 8000
    assert kwargs["max_completion_tokens"] >= 256


def test_complete_gives_gpt_oss_the_remaining_tpm_not_a_2048_cap():
    provider, completions = _provider()
    provider.complete(
        "merge tags",
        model="openai/gpt-oss-120b",
        schema=CONSOLIDATE_SCHEMA,
    )
    kwargs = completions.calls[0]
    prompt_tokens = sum(len(m["content"]) for m in kwargs["messages"]) // 4
    assert kwargs["max_completion_tokens"] > 2048
    assert prompt_tokens + kwargs["max_completion_tokens"] <= 8000


class _FailThenOk:
    def __init__(self):
        self.calls: list[dict] = []
        self.n = 0

    def create(self, **kwargs):
        self.calls.append(kwargs)
        self.n += 1
        if self.n == 1:
            raise _empty_json_validate_error()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
        )


def test_complete_retries_empty_json_validate_failed(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    provider = GroqProvider(api_key="x")
    completions = _FailThenOk()
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    content = provider.complete(
        "merge tags",
        model="openai/gpt-oss-120b",
        schema=CONSOLIDATE_SCHEMA,
    )
    assert content == '{"ok": true}'
    assert len(completions.calls) == 2


def test_complete_fits_tpm_for_clipped_article_plus_ingest_schema():
    """ScienceDirect-sized body (12k chars) + json_schema must not reserve >8000 TPM."""
    provider, completions = _provider()
    vocab = "\n".join(f"- topic-{i} phrase" for i in range(127))
    provider.complete(
        f"Existing topics:\n{vocab}\n\nArticle text:\n" + ("market " * 2000),
        model="openai/gpt-oss-120b",
        system=INGEST_SYSTEM,
        schema=INGEST_SCHEMA,
        temperature=0.2,
    )
    kwargs = completions.calls[0]
    assert _billed_tpm(kwargs) <= 8000
    assert kwargs["max_completion_tokens"] >= 256


def test_complete_truncates_user_prompt_when_it_would_exceed_tpm():
    provider, completions = _provider()
    huge = "word " * 20_000
    provider.complete(
        huge,
        model="openai/gpt-oss-120b",
        schema=INGEST_SCHEMA,
    )
    kwargs = completions.calls[0]
    user = kwargs["messages"][-1]["content"]
    assert len(user) < len(huge)
    assert _billed_tpm(kwargs) <= 8000


def _tpm_too_large_error() -> APIStatusError:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(
        413,
        request=request,
        json={
            "error": {
                "message": (
                    "Request too large for model `openai/gpt-oss-120b` "
                    "on tokens per minute (TPM): Limit 8000, Requested 8164"
                ),
                "type": "tokens",
                "code": "rate_limit_exceeded",
            }
        },
    )
    return APIStatusError(
        "Request too large",
        response=response,
        body=response.json(),
    )


class _TpmThenOk:
    def __init__(self):
        self.calls: list[dict] = []
        self.n = 0

    def create(self, **kwargs):
        recorded = {k: v for k, v in kwargs.items()}
        recorded["messages"] = [
            {"role": m["role"], "content": m["content"]} for m in kwargs["messages"]
        ]
        self.calls.append(recorded)
        self.n += 1
        if self.n == 1:
            raise _tpm_too_large_error()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
        )


def test_complete_shrinks_prompt_and_retries_413_tpm(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    provider = GroqProvider(api_key="x")
    completions = _TpmThenOk()
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    content = provider.complete(
        "Article text:\n" + ("market " * 2000),
        model="openai/gpt-oss-120b",
        system=INGEST_SYSTEM,
        schema=INGEST_SCHEMA,
    )
    assert content == '{"ok": true}'
    assert len(completions.calls) == 2
    first = completions.calls[0]["messages"][-1]["content"]
    second = completions.calls[1]["messages"][-1]["content"]
    assert len(second) < len(first)
    assert _billed_tpm(completions.calls[1]) <= 8000
