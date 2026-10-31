from datetime import datetime, timedelta, timezone

from readurlist.rank.score import RankItem, build_day_list

NOW = datetime(2026, 11, 1, 7, 0, tzinfo=timezone.utc)
SHORT, LONG = 1000, 5000  # words: 4 min and 22 min at 230 a minute


def _item(id: int, subject: str, words: int | None, days_ago: int = 1) -> RankItem:
    created = NOW - timedelta(days=days_ago)
    return RankItem(id=id, subject=subject, topics=[], keywords=[], created_at=created,
                    read_at=None, priority=3, word_count=words)


def _sections(day):
    return (
        [p.item_id for p in day.picks if p.section == "short"],
        [p.item_id for p in day.picks if p.section == "long"],
    )


def test_three_short_and_one_long():
    items = [_item(i, f"s{i}", SHORT, days_ago=i) for i in range(1, 6)]
    items += [_item(10, "papers", LONG, days_ago=1), _item(11, "papers2", LONG, days_ago=2)]
    short, long = _sections(build_day_list(items, now=NOW))
    assert short == [1, 2, 3]
    assert long == [10]


def test_no_long_read_leaves_the_long_section_empty():
    items = [_item(i, f"s{i}", SHORT) for i in range(1, 8)]
    short, long = _sections(build_day_list(items, now=NOW))
    assert len(short) == 3 and long == []


def test_two_per_subject_across_both_sections():
    # 25 short saves on one subject, 15 on others, one long paper on the big subject.
    items = [_item(i, "llms", SHORT, days_ago=1) for i in range(1, 26)]
    items += [_item(100 + i, f"other{i}", SHORT, days_ago=1) for i in range(15)]
    items += [_item(200, "llms", LONG, days_ago=0)]
    day = build_day_list(items, now=NOW)
    short, long = _sections(day)
    subjects = [next(i.subject for i in items if i.id == p.item_id) for p in day.picks]
    assert subjects.count("llms") == 2
    assert long == [200]
    assert len(short) == 3


def test_unknown_length_counts_as_short():
    short, long = _sections(build_day_list([_item(1, "a", None)], now=NOW))
    assert short == [1] and long == []


def test_every_unread_item_gets_a_score_and_cap_blocks_are_recorded():
    items = [_item(i, "llms", SHORT, days_ago=i) for i in range(1, 5)]
    day = build_day_list(items, now=NOW)
    assert set(day.scores) == {1, 2, 3, 4}
    assert day.capped == {3, 4}  # would have made the short section but llms already had two
