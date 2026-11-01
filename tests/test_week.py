from datetime import date, datetime, timedelta, timezone

from readurlist.db import DailyPick, Item, get_session, init_db
from readurlist.rank.run import format_digest
from readurlist.rank.week import WeekStats, week_line, week_stats

MON = date(2026, 11, 2)  # a Monday
WEEK_START = MON - timedelta(days=7)
T0 = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)  # before the week


def _add(url, *, saved=T0, read=None, skipped=None, status="ready") -> int:
    session = get_session()
    item = Item(url=url, title=url, snapshot="s", subject="a", topics=[], keywords=[],
                extracted_text="x", priority=3, ingest_status=status, created_at=saved,
                read_at=read, skipped_at=skipped, word_count=100)
    session.add(item)
    session.commit()
    item_id = item.id
    session.close()
    return item_id


def _shown(item_id: int, on: date, rank: int = 1) -> None:
    session = get_session()
    session.add(DailyPick(run_on=on, item_id=item_id, rank=rank, score=50, reason="r",
                          section="short"))
    session.commit()
    session.close()


def _at(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 12, 0, tzinfo=timezone.utc)


def test_counts_distinct_picks_read_and_skipped(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    read = _add("https://example.com/r", read=_at(WEEK_START + timedelta(days=2)))
    skipped = _add("https://example.com/s", skipped=_at(WEEK_START + timedelta(days=3)))
    waiting = _add("https://example.com/w")
    before = _add("https://example.com/b")
    _shown(read, WEEK_START)
    _shown(read, WEEK_START + timedelta(days=1))  # shown twice, counted once
    _shown(skipped, WEEK_START + timedelta(days=2))
    _shown(waiting, MON - timedelta(days=1))
    _shown(before, WEEK_START - timedelta(days=1))  # outside the week

    stats = week_stats(WEEK_START, MON - timedelta(days=1))
    assert (stats.shown, stats.read, stats.skipped) == (3, 1, 1)


def test_pile_then_is_worked_out_from_dates(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    _add("https://example.com/old-unread")  # unread then and now
    _add("https://example.com/read-in-week", read=_at(WEEK_START + timedelta(days=1)))  # then only
    _add("https://example.com/read-before", read=_at(WEEK_START - timedelta(days=2)))  # neither
    _add("https://example.com/new", saved=_at(WEEK_START + timedelta(days=4)))  # now only
    _add("https://example.com/stub", status="pending_body")  # not in the pile

    stats = week_stats(WEEK_START, MON - timedelta(days=1))
    assert (stats.pile_then, stats.pile_now) == (2, 2)


def test_line_names_read_rate_and_verdict():
    assert week_line(WeekStats(shown=12, read=5, skipped=3, pile_then=140, pile_now=142)) == (
        "Last week: read 5 of 12 picks (42%, below half: tune the ranking). "
        "Skipped 3. Unread pile 140 → 142."
    )
    assert week_line(WeekStats(shown=10, read=5, skipped=0, pile_then=9, pile_now=7)) == (
        "Last week: read 5 of 10 picks (50%, working). Skipped 0. Unread pile 9 → 7."
    )
    assert "(13%, below half" in week_line(
        WeekStats(shown=8, read=1, skipped=0, pile_then=1, pile_now=1)
    )
    assert week_line(WeekStats(shown=0, read=0, skipped=0, pile_then=3, pile_now=4)) == (
        "Last week: no picks shown. Unread pile 3 → 4."
    )


def test_monday_list_ends_with_last_weeks_line(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    item = _add("https://example.com/a", read=_at(WEEK_START + timedelta(days=1)))
    _shown(item, WEEK_START)
    other = _add("https://example.com/b")
    _shown(other, MON)

    monday = format_digest(MON, "")
    assert monday.splitlines()[-1].startswith("Last week: read 1 of 1 picks (100%, working).")
    tuesday_pick = _add("https://example.com/c")
    _shown(tuesday_pick, MON + timedelta(days=1))
    assert "Last week" not in format_digest(MON + timedelta(days=1), "")
