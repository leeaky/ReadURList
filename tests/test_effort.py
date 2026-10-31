import json

import pytest

from readurlist.config import Settings
from readurlist.db import Item, get_session, init_db
from readurlist.effort import backfill_word_counts, effort, word_count
from readurlist.ingest import ingest_url
from readurlist.ingest.complete import complete_pending_bodies_sync


def test_word_count_counts_whitespace_separated_words():
    assert word_count("one two\nthree\t four  ") == 4
    assert word_count("") == 0


@pytest.mark.parametrize(
    ("words", "label", "minutes"),
    [
        (300, "short", 1),  # 1.3 min
        (1200, "short", 5),  # proof post: 5.2 min
        (3449, "short", 15),  # 14.996 min: still under 15
        (3450, "long", 15),  # exactly 15 min
        (12000, "long", 52),  # 30-page paper
        (0, "short", 1),  # never shows 0 minutes
    ],
)
def test_effort_is_short_under_15_minutes_at_230_words_a_minute(words, label, minutes):
    assert effort(words) == (label, minutes)


class FakeLLM:
    def complete(self, prompt, *, model, system=None, schema=None, temperature=0.3) -> str:
        return json.dumps(
            {"title": "T", "snapshot": "Summary.", "subject": "Gardening",
             "topics": ["soil"], "keywords": ["compost"], "priority": 3}
        )


def _settings(db: str) -> Settings:
    return Settings(telegram_bot_token="x", telegram_user_id=1, groq_api_key="x", database_url=db)


def test_a_read_page_stores_its_word_count(tmp_path, monkeypatch):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    monkeypatch.setattr(
        "readurlist.ingest.extract_article",
        lambda url, timeout=30.0: ("Title", "compost " * 500),
    )
    item, _ = ingest_url("https://example.com/a", FakeLLM(), _settings(db))  # type: ignore[arg-type]
    assert item.word_count == 500


def _add(**fields) -> int:
    session = get_session()
    item = Item(title="T", snapshot="s", subject="x", topics=[], keywords=[], priority=3, **fields)
    session.add(item)
    session.commit()
    item_id = item.id
    session.close()
    return item_id


def _words(item_id: int):
    session = get_session()
    try:
        return session.get(Item, item_id).word_count
    finally:
        session.close()


def test_filled_in_text_stores_its_word_count(tmp_path):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    item_id = _add(url="https://example.com/p", extracted_text="soil " * 40, ingest_status="pending_body")
    complete_pending_bodies_sync(FakeLLM(), _settings(db))  # type: ignore[arg-type]
    assert _words(item_id) == 40


def test_backfill_labels_older_ready_items_once(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    old = _add(url="https://example.com/old", extracted_text="word " * 70, ingest_status="ready")
    stub = _add(url="https://example.com/stub", extracted_text="", ingest_status="pending_body")

    assert backfill_word_counts() == 1
    assert _words(old) == 70
    assert _words(stub) is None
    assert backfill_word_counts() == 0  # already done
