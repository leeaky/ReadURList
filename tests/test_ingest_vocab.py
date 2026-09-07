from readurlist.config import Settings
from readurlist.db import Item, get_session, init_db
from readurlist.ingest import ingest_url


class CaptureLLM:
    def __init__(self):
        self.prompt = ""

    def complete(self, prompt, *, model, system=None, schema=None, temperature=0.3) -> str:
        self.prompt = prompt
        return (
            '{"title": "T", "snapshot": "S.", "subject": "claude code",'
            ' "topics": ["agents"], "keywords": ["k"], "priority": 3}'
        )


def test_ingest_url_sees_existing_subjects(tmp_path, monkeypatch):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    session = get_session()
    try:
        session.add(
            Item(
                url="https://example.com/old",
                title="Old",
                snapshot="s",
                subject="Claude Code",
                topics=["agents"],
                keywords=["k"],
                extracted_text="x" * 40,
                priority=3,
                ingest_status="ready",
            )
        )
        session.commit()
    finally:
        session.close()

    monkeypatch.setattr(
        "readurlist.ingest.extract_article",
        lambda url: ("Hint", "Body text " * 40),
    )
    settings = Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url=db,
    )
    llm = CaptureLLM()
    item, created = ingest_url("https://example.com/new", llm, settings)  # type: ignore[arg-type]
    assert created is True
    assert item.subject == "Claude Code"
    assert "Claude Code" in llm.prompt
