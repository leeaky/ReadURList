from __future__ import annotations

from second_read.config import Settings
from second_read.db import Item, get_session, init_db
from second_read.ingest import ingest_url
from second_read.llm.base import LLMProvider


class FakeLLM:
    def complete(self, prompt, *, model, system=None, schema=None, temperature=0.3) -> str:
        return (
            '{"title": "Example", "snapshot": "A short snapshot of the piece.",'
            ' "subject": "testing", "topics": ["tests"], "keywords": ["pytest"],'
            ' "priority": 3}'
        )


def test_same_url_does_not_insert_second_item(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    init_db(f"sqlite:///{db}")

    def fake_extract(url: str, timeout: float = 30.0):
        return "Example", "x" * 200

    monkeypatch.setattr("second_read.ingest.extract_article", fake_extract)
    monkeypatch.setattr("second_read.ingest.summarize_article", lambda *a, **k: __import__(
        "second_read.ingest.summarize", fromlist=["IngestResult"]
    ).IngestResult(
        title="Example",
        snapshot="A short snapshot of the piece.",
        subject="testing",
        topics=["tests"],
        keywords=["pytest"],
        priority=3,
    ))

    settings = Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url=f"sqlite:///{db}",
    )
    llm: LLMProvider = FakeLLM()  # type: ignore[assignment]
    url = "https://example.com/article"

    first, created1 = ingest_url(url, llm, settings)
    second, created2 = ingest_url(url, llm, settings)

    assert created1 is True
    assert created2 is False
    assert first.id == second.id

    session = get_session()
    try:
        assert session.query(Item).filter_by(url=url).count() == 1
    finally:
        session.close()
