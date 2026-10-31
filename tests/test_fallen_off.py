from datetime import datetime, timedelta, timezone

from readurlist.db import DailyPick, FallenOff, Item, get_session, init_db
from readurlist.rank.run import persist_ranking

DAY1 = datetime(2026, 11, 1, 7, 0, tzinfo=timezone.utc)
DAY2 = DAY1 + timedelta(days=1)
SHORT = 1000


def _add(url: str, subject: str, saved: datetime, words: int = SHORT) -> int:
    session = get_session()
    item = Item(url=url, title=url, snapshot="s", subject=subject, topics=[], keywords=[],
                extracted_text="x", priority=3, ingest_status="ready", created_at=saved,
                word_count=words)
    session.add(item)
    session.commit()
    item_id = item.id
    session.close()
    return item_id


def _set(item_id: int, **fields) -> None:
    session = get_session()
    row = session.get(Item, item_id)
    for k, v in fields.items():
        setattr(row, k, v)
    session.commit()
    session.close()


def _fallen(day) -> dict[int, FallenOff]:
    session = get_session()
    try:
        rows = session.query(FallenOff).filter(FallenOff.run_on == day).all()
        for r in rows:
            session.expunge(r)
        return {r.item_id: r for r in rows}
    finally:
        session.close()


def _sections(day) -> dict[int, str]:
    session = get_session()
    try:
        return {r.item_id: r.section for r in session.query(DailyPick).filter(DailyPick.run_on == day)}
    finally:
        session.close()


def test_each_pick_stores_its_section(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    short = _add("https://example.com/s", "a", DAY1)
    long = _add("https://example.com/l", "b", DAY1, words=5000)
    persist_ranking(now=DAY1)
    assert _sections(DAY1.date()) == {short: "short", long: "long"}


def test_fallen_off_causes_and_points(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    read = _add("https://example.com/read", "a", DAY1)
    skipped = _add("https://example.com/skip", "b", DAY1)
    outscored = _add("https://example.com/old", "c", DAY1 - timedelta(days=3))
    persist_ranking(now=DAY1)
    assert set(_sections(DAY1.date())) == {read, skipped, outscored}

    _set(read, read_at=DAY2)
    _set(skipped, skipped_at=DAY2)
    # Three fresh saves on new subjects push the old one out.
    for n in range(3):
        _add(f"https://example.com/new{n}", f"new{n}", DAY2)
    persist_ranking(now=DAY2)

    fallen = _fallen(DAY2.date())
    assert set(fallen) == {read, skipped, outscored}
    assert fallen[read].cause == "read" and fallen[read].points_after is None
    assert fallen[skipped].cause == "skipped" and fallen[skipped].points_after is None
    assert fallen[outscored].cause == "outscored"
    assert fallen[outscored].points_before == 74  # subject 65 + recency 35/4 = 9
    assert fallen[outscored].points_after == 72  # subject 65 + recency 35/5 = 7


def test_fallen_off_because_its_subject_already_has_two(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    old = _add("https://example.com/old", "llms", DAY1 - timedelta(days=1))
    persist_ranking(now=DAY1)
    assert old in _sections(DAY1.date())

    _add("https://example.com/n1", "llms", DAY2)
    _add("https://example.com/n2", "llms", DAY2)
    persist_ranking(now=DAY2)

    assert _fallen(DAY2.date())[old].cause == "subject_full"


def test_rebuilding_today_does_not_duplicate_fallen_off(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    item = _add("https://example.com/a", "a", DAY1)
    persist_ranking(now=DAY1)
    _set(item, read_at=DAY2)
    persist_ranking(now=DAY2)
    persist_ranking(now=DAY2)
    assert list(_fallen(DAY2.date())) == [item]
