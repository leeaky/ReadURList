from second_read.ingest.summarize import summarize_article


class FakeLLM:
    def __init__(self):
        self.prompt = ""
        self.system = ""

    def complete(self, prompt, *, model, system=None, schema=None, temperature=0.3) -> str:
        self.prompt = prompt
        self.system = system or ""
        return (
            '{"title": "T", "snapshot": "Snap.", "subject": "claude code",'
            ' "topics": ["Agents", "brand-new-topic"], "keywords": ["X"], "priority": 4}'
        )


def test_summarize_canonicalizes_subject_to_existing_spelling():
    llm = FakeLLM()
    result = summarize_article(
        llm,  # type: ignore[arg-type]
        model="x",
        url="https://example.com",
        title_hint="Hint",
        text="Body " * 20,
        existing_subjects=["Claude Code", "Public health"],
        existing_topics=["agents"],
    )
    assert result.subject == "Claude Code"
    assert "agents" in [t.lower() for t in result.topics]
    assert "brand-new-topic" in result.topics
    assert "Existing subjects" in llm.prompt
    assert "Claude Code" in llm.prompt
    assert "reuse an existing subject" in llm.system.lower()
