from second_read.config import Settings
from second_read.db import Item, get_session, init_db
from second_read.ingest.complete import complete_pending_bodies_sync
from second_read.llm.base import LLMProvider


class FakeLLM:
    def complete(
        self,
        prompt,
        *,
        model,
        system=None,
        schema=None,
        temperature=0.3,
    ) -> str:
        return (
            '{"title": "Filled", "snapshot": "Now we have a snapshot.",'
            ' "subject": "testing", "topics": ["tests"], "keywords": ["pytest"],'
            ' "priority": 4}'
        )


def test_complete_pending_fills_ready_item(tmp_path):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    session = get_session()
    try:
        session.add(
            Item(
                url="https://example.com/later",
                title="https://example.com/later",
                snapshot="not available",
                subject="not available",
                topics=[],
                keywords=[],
                extracted_text="Article body " * 40,
                priority=3,
                ingest_status="pending_body",
                note="HTTP 403",
            )
        )
        session.commit()
    finally:
        session.close()

    settings = Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url=db,
    )
    llm: LLMProvider = FakeLLM()  # type: ignore[assignment]
    done = complete_pending_bodies_sync(llm, settings)

    assert len(done) == 1
    assert done[0].ingest_status == "ready"
    assert done[0].snapshot == "Now we have a snapshot."
    assert done[0].subject == "testing"
    assert done[0].title == "Filled"


def test_complete_skips_stub_without_body(tmp_path):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    session = get_session()
    try:
        session.add(
            Item(
                url="https://example.com/empty",
                title="t",
                snapshot="not available",
                subject="not available",
                extracted_text="",
                ingest_status="pending_body",
            )
        )
        session.commit()
    finally:
        session.close()

    settings = Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url=db,
    )
    assert complete_pending_bodies_sync(FakeLLM(), settings) == []  # type: ignore[arg-type]
