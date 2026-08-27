from second_read.db import Item, get_session, init_db
from second_read.tags.vocab import apply_tag_maps, load_vocabulary


def _ready(url: str, subject: str, topics: list[str], **kwargs) -> Item:
    return Item(
        url=url,
        title=url,
        snapshot="s",
        subject=subject,
        topics=topics,
        keywords=["keep-me"],
        extracted_text="x" * 40,
        priority=3,
        ingest_status="ready",
        **kwargs,
    )


def test_load_vocabulary_skips_stubs_and_empty_subject(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    session = get_session()
    try:
        session.add_all(
            [
                _ready("https://a.example/1", "Claude Code", ["agents", "cli"]),
                _ready("https://a.example/2", "claude code", ["CLI"]),
                _ready("https://a.example/3", "", ["ignored-empty-subject"]),
                Item(
                    url="https://stub.example",
                    title="stub",
                    snapshot="not available",
                    subject="not available",
                    topics=["should-not-appear"],
                    keywords=[],
                    extracted_text="",
                    priority=3,
                    ingest_status="pending_body",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    vocab = load_vocabulary()
    assert "not available" not in vocab.subjects
    assert "should-not-appear" not in vocab.topics
    lowered = {s.lower() for s in vocab.subjects}
    assert "claude code" in lowered
    assert "" not in vocab.subjects
    assert "agents" in vocab.topics or "cli" in {t.lower() for t in vocab.topics}


def test_apply_tag_maps_merges_subjects_and_topics_leaves_keywords(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    session = get_session()
    try:
        session.add_all(
            [
                _ready("https://a.example/1", "Claude Code workflow", ["AI education"]),
                _ready("https://a.example/2", "Claude Code training", ["online courses"]),
                Item(
                    url="https://stub.example",
                    title="stub",
                    snapshot="not available",
                    subject="Claude Code workflow",
                    topics=["AI education"],
                    keywords=["stub"],
                    extracted_text="",
                    priority=3,
                    ingest_status="pending_body",
                ),
            ]
        )
        session.commit()
        ids = [row.id for row in session.query(Item).filter(Item.ingest_status == "ready")]
        stub_id = session.query(Item).filter_by(url="https://stub.example").one().id
    finally:
        session.close()

    n = apply_tag_maps(
        subject_maps={
            "Claude Code workflow": "Claude Code",
            "Claude Code training": "Claude Code",
        },
        topic_maps={"AI education": "AI education", "online courses": "AI education"},
    )
    assert n == 2

    session = get_session()
    try:
        rows = {row.id: row for row in session.query(Item).all()}
        assert {rows[i].subject for i in ids} == {"Claude Code"}
        for i in ids:
            assert rows[i].keywords == ["keep-me"]
            assert "AI education" in rows[i].topics
        assert rows[stub_id].subject == "Claude Code workflow"
        assert rows[stub_id].keywords == ["stub"]
    finally:
        session.close()
