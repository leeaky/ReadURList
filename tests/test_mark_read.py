from datetime import datetime, timezone

from second_read.db import Item, get_session, init_db, mark_item_read, mark_item_skipped


def test_mark_item_read_and_unread(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    session = get_session()
    try:
        item = Item(
            url="https://example.com/a",
            title="A",
            snapshot="snap",
            subject="s",
            topics=["t"],
            keywords=["k"],
            extracted_text="x" * 80,
            priority=3,
        )
        session.add(item)
        session.commit()
        item_id = item.id
    finally:
        session.close()

    when = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)
    marked = mark_item_read(item_id, read=True, when=when)
    assert marked is not None
    assert marked.read_at is not None

    session = get_session()
    try:
        row = session.get(Item, item_id)
        assert row.read_at is not None
    finally:
        session.close()

    cleared = mark_item_read(item_id, read=False)
    assert cleared is not None
    assert cleared.read_at is None


def test_mark_item_skipped_and_restore(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    session = get_session()
    try:
        item = Item(
            url="https://example.com/skip",
            title="S",
            snapshot="snap",
            subject="s",
            topics=["t"],
            keywords=["k"],
            extracted_text="x" * 80,
            priority=3,
        )
        session.add(item)
        session.commit()
        item_id = item.id
    finally:
        session.close()

    when = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)
    marked = mark_item_skipped(item_id, skipped=True, when=when)
    assert marked is not None
    assert marked.skipped_at is not None
    assert marked.read_at is None

    restored = mark_item_skipped(item_id, skipped=False)
    assert restored is not None
    assert restored.skipped_at is None
