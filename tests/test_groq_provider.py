from types import SimpleNamespace

from second_read.llm.groq_provider import GroqProvider
from second_read.prompts import CONSOLIDATE_SCHEMA


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
    assert kwargs["max_completion_tokens"] >= 8192
    fmt = kwargs["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["name"] == "tag_consolidation"
    assert fmt["json_schema"]["schema"]["required"] == ["subject_maps", "topic_maps"]
