from datetime import datetime, timezone

from second_read.db import DailyPick, Item, get_session, init_db
from second_read.rank.run import persist_ranking


def test_persist_ranking_writes_picks_and_respects_read(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    now = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)
    session = get_session()
    try:
        session.add_all(
            [
                Item(
                    url="https://example.com/a",
                    title="A",
                    snapshot="about trees",
                    subject="climate",
                    topics=["climate"],
                    keywords=["trees", "carbon"],
                    extracted_text="x" * 80,
                    priority=4,
                    created_at=now,
                ),
                Item(
                    url="https://example.com/b",
                    title="B",
                    snapshot="about bonds",
                    subject="markets",
                    topics=["finance"],
                    keywords=["bonds", "rates"],
                    extracted_text="x" * 80,
                    priority=4,
                    created_at=now,
                    read_at=now,
                ),
                Item(
                    url="https://example.com/c",
                    title="C",
                    snapshot="about ice",
                    subject="climate",
                    topics=["climate"],
                    keywords=["ice", "antarctica"],
                    extracted_text="x" * 80,
                    priority=3,
                    created_at=now,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    picks = persist_ranking(now=now)
    ids = {p.item_id for p in picks}
    session = get_session()
    try:
        unread_ids = {
            i.id for i in session.query(Item).filter(Item.read_at.is_(None)).all()
        }
        read_ids = {i.id for i in session.query(Item).filter(Item.read_at.isnot(None)).all()}
        assert ids <= unread_ids
        assert ids.isdisjoint(read_ids)
        assert session.query(DailyPick).count() == len(picks)
        assert all(p.reason for p in picks)
        assert all(item.similar_to_item_id is None for item in session.query(Item).all())
    finally:
        session.close()


def test_persist_ranking_omits_skipped_items(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    now = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)
    session = get_session()
    try:
        session.add_all(
            [
                Item(
                    url="https://example.com/queue",
                    title="Queue",
                    snapshot="about ice",
                    subject="climate",
                    topics=["climate"],
                    keywords=["ice"],
                    extracted_text="x" * 80,
                    priority=4,
                    created_at=now,
                ),
                Item(
                    url="https://example.com/skipped",
                    title="Skipped",
                    snapshot="about ice too",
                    subject="climate",
                    topics=["climate"],
                    keywords=["ice"],
                    extracted_text="x" * 80,
                    priority=5,
                    created_at=now,
                    skipped_at=now,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    picks = persist_ranking(now=now)
    session = get_session()
    try:
        skipped = session.query(Item).filter_by(url="https://example.com/skipped").one()
        queued = session.query(Item).filter_by(url="https://example.com/queue").one()
        ids = {p.item_id for p in picks}
        assert skipped.id not in ids
        assert queued.id in ids
    finally:
        session.close()


def test_persist_ranking_does_not_write_similar_to(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    now = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)
    session = get_session()
    try:
        session.add_all(
            [
                Item(
                    url="https://example.com/a",
                    title="A",
                    snapshot="about transformers",
                    subject="llms",
                    topics=["llms"],
                    keywords=["transformer", "attention", "gpt"],
                    extracted_text="x" * 80,
                    priority=4,
                    created_at=now,
                ),
                Item(
                    url="https://example.com/b",
                    title="B",
                    snapshot="about gpt",
                    subject="llms",
                    topics=["llms"],
                    keywords=["transformer", "attention", "gpt"],
                    extracted_text="x" * 80,
                    priority=3,
                    created_at=now,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    persist_ranking(now=now)
    session = get_session()
    try:
        rows = session.query(Item).all()
        assert rows
        assert all(item.similar_to_item_id is None for item in rows)
    finally:
        session.close()
