from datetime import datetime, timezone

from second_read.db import DailyPick, Item, get_session, init_db
from second_read.rank.run import persist_ranking


def test_pending_body_stub_not_in_daily_picks(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    now = datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc)
    session = get_session()
    try:
        session.add_all(
            [
                Item(
                    url="https://example.com/ready",
                    title="Ready",
                    snapshot="a real snapshot about trees",
                    subject="climate",
                    topics=["climate"],
                    keywords=["trees"],
                    extracted_text="x" * 80,
                    priority=4,
                    ingest_status="ready",
                    created_at=now,
                ),
                Item(
                    url="https://example.com/stub",
                    title="https://example.com/stub",
                    snapshot="not available",
                    subject="not available",
                    topics=[],
                    keywords=[],
                    extracted_text="",
                    priority=3,
                    ingest_status="pending_body",
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
        stub = session.query(Item).filter_by(url="https://example.com/stub").one()
        ready = session.query(Item).filter_by(url="https://example.com/ready").one()
        assert stub.id not in ids
        assert ready.id in ids or session.query(DailyPick).filter_by(item_id=ready.id).count() == 1
    finally:
        session.close()
