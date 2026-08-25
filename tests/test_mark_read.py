from datetime import datetime, timezone

from second_read.db import Item, get_session, init_db, mark_item_read


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
