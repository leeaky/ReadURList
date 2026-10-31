from datetime import datetime, timedelta, timezone

from readurlist.db import DailyPick, Item, get_session, init_db
from readurlist.rank.run import persist_ranking

DAY1 = datetime(2026, 11, 1, 7, 0, tzinfo=timezone.utc)


def _add(url: str, *, subject: str, saved: datetime, restored: datetime | None = None) -> int:
    session = get_session()
    item = Item(url=url, title=url, snapshot="s", subject=subject, topics=[], keywords=[],
                extracted_text="x", priority=3, ingest_status="ready", created_at=saved,
                restored_at=restored)
    session.add(item)
    session.commit()
    item_id = item.id
    session.close()
    return item_id


def _picks(day) -> dict[int, DailyPick]:
    session = get_session()
    try:
        rows = session.query(DailyPick).filter(DailyPick.run_on == day).all()
        for r in rows:
            session.expunge(r)
        return {r.item_id: r for r in rows}
    finally:
        session.close()


def test_each_pick_stores_its_points_per_part(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    item_id = _add("https://example.com/a", subject="llms", saved=DAY1)
    persist_ranking(now=DAY1)
    pick = _picks(DAY1.date())[item_id]
    assert (pick.subject_points, pick.recency_points, pick.score) == (65, 35, 100)


def test_yesterdays_list_is_kept_when_today_is_built(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    item_id = _add("https://example.com/a", subject="llms", saved=DAY1)
    persist_ranking(now=DAY1)
    day2 = DAY1 + timedelta(days=1)
    persist_ranking(now=day2)
    persist_ranking(now=day2)  # rebuilding today twice still leaves yesterday alone
    assert _picks(DAY1.date())[item_id].score == 100
    assert _picks(day2.date())[item_id].recency_points == 18  # 35 / 2


def test_restore_date_is_read_from_the_database(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    item_id = _add("https://example.com/r", subject="llms",
                   saved=DAY1 - timedelta(days=30), restored=DAY1)
    persist_ranking(now=DAY1)
    assert _picks(DAY1.date())[item_id].recency_points == 35
