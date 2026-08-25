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
    finally:
        session.close()
