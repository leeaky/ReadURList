from types import SimpleNamespace

import httpx
from openai import BadRequestError

from second_read.llm.groq_provider import GroqProvider
from second_read.prompts import CONSOLIDATE_SCHEMA


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
