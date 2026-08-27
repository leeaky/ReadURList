from second_read.config import Settings
from second_read.db import Item, get_session, init_db
from second_read.tags.consolidate import (
    consolidation_prompt,
    maps_from_payload,
    maybe_consolidate_tags,
)


def test_consolidation_prompt_lists_labels_not_article_bodies():
    prompt = consolidation_prompt(
        subjects=["Claude flavor 0", "Public health"],
        topics=["LLM", "agents"],
    )
    assert "Claude flavor 0" in prompt
    assert "Public health" in prompt
    assert "LLM" in prompt
    assert "title=" not in prompt
    assert "extracted" not in prompt.lower()


def test_maps_from_payload_reads_pair_lists():
    subjects, topics = maps_from_payload(
        {
            "subject_maps": [
                {"from": "Claude Code workflow", "to": "Claude Code"},
                {"from": "Claude Code", "to": "Claude Code"},
            ],
            "topic_maps": [{"from": "online courses", "to": "AI education"}],
        }
    )
    assert subjects["Claude Code workflow"] == "Claude Code"
    assert topics["online courses"] == "AI education"


class RecordingLLM:
    def __init__(self, payload: str):
        self.payload = payload
        self.prompts: list[str] = []

    def complete(self, prompt, *, model, system=None, schema=None, temperature=0.3) -> str:
        self.prompts.append(prompt)
        return self.payload


def _settings(db: str) -> Settings:
    return Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url=db,
    )


def test_maybe_consolidate_skips_when_corpus_is_small(tmp_path):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    session = get_session()
    try:
        for i in range(3):
            session.add(
                Item(
                    url=f"https://e.example/{i}",
                    title=str(i),
                    snapshot="s",
                    subject=f"unique-{i}",
                    topics=["t"],
                    keywords=["k"],
                    extracted_text="x" * 20,
                    priority=3,
                    ingest_status="ready",
                )
            )
        session.commit()
    finally:
        session.close()

    llm = RecordingLLM('{"subject_maps": [], "topic_maps": []}')
    assert maybe_consolidate_tags(llm, _settings(db)) == 0
    assert llm.prompts == []


def test_maybe_consolidate_applies_maps_and_skips_stubs(tmp_path):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    session = get_session()
    try:
        for i in range(8):
            session.add(
                Item(
                    url=f"https://e.example/{i}",
                    title=f"Article {i} about Claude",
                    snapshot="s",
                    subject=f"Claude flavor {i}",
                    topics=[f"topic-{i}"],
                    keywords=[f"kw-{i}"],
                    extracted_text="x" * 20,
                    priority=3,
                    ingest_status="ready",
                )
            )
        session.add(
            Item(
                url="https://stub.example",
                title="stub",
                snapshot="not available",
                subject="Claude flavor 0",
                topics=["topic-0"],
                keywords=[],
                extracted_text="",
                priority=3,
                ingest_status="pending_body",
            )
        )
        session.commit()
    finally:
        session.close()

    payload = (
        '{"subject_maps": ['
        + ",".join(
            f'{{"from": "Claude flavor {i}", "to": "Claude Code"}}' for i in range(8)
        )
        + '], "topic_maps": []}'
    )
    llm = RecordingLLM(payload)
    changed = maybe_consolidate_tags(llm, _settings(db))
    assert changed == 8
    assert llm.prompts
    assert "Claude flavor 0" in llm.prompts[0]
    assert "stub" not in llm.prompts[0].lower() or "https://stub.example" not in llm.prompts[0]

    session = get_session()
    try:
        subjects = [r.subject for r in session.query(Item).filter_by(ingest_status="ready")]
        assert set(subjects) == {"Claude Code"}
        stub = session.query(Item).filter_by(url="https://stub.example").one()
        assert stub.subject == "Claude flavor 0"
        ready = session.query(Item).filter_by(url="https://e.example/0").one()
        assert ready.keywords == ["kw-0"]
    finally:
        session.close()
