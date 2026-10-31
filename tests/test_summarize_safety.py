import json

import pytest

from readurlist.ingest.summarize import AnswerRejected, summarize_article

GOOD = {
    "title": "T",
    "snapshot": "A short factual summary.",
    "subject": "Gardening",
    "topics": ["soil"],
    "keywords": ["compost"],
    "priority": 3,
}


class FakeLLM:
    def __init__(self, answer: dict | None = None) -> None:
        self.answer = answer or GOOD
        self.prompt = ""

    def complete(self, prompt, *, model, system=None, schema=None, temperature=0.3) -> str:
        self.prompt = prompt
        return json.dumps(self.answer)


def _run(llm, text="Body text " * 20, title_hint="Hint"):
    return summarize_article(
        llm,  # type: ignore[arg-type]
        model="x",
        url="https://example.com/a",
        title_hint=title_hint,
        text=text,
    )


def test_page_text_reaches_the_model_cleaned_and_wrapped_as_data():
    llm = FakeLLM()
    _run(llm, text="Hidden​ words‮ here", title_hint="Title​ hint")
    assert '<untrusted_document source="https://example.com/a">' in llm.prompt
    assert "Hidden words here" in llm.prompt
    assert "​" not in llm.prompt and "‮" not in llm.prompt
    # The page's own title is page text too, so it sits inside the wrapper.
    start = llm.prompt.index("<untrusted_document")
    assert llm.prompt.index("Title hint") > start


def test_a_valid_answer_is_accepted():
    assert _run(FakeLLM()).subject == "Gardening"


@pytest.mark.parametrize(
    "change",
    [
        {"priority": 9},
        {"priority": 0},
        {"snapshot": ""},
        {"snapshot": "x" * 1201},
        {"subject": ""},
        {"subject": "s" * 81},
        {"topics": ["t" * 61]},
        {"topics": "soil"},
        {"keywords": [3]},
    ],
)
def test_an_answer_outside_the_fixed_form_is_rejected(change):
    with pytest.raises(AnswerRejected):
        _run(FakeLLM({**GOOD, **change}))
